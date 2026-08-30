#!/usr/bin/env python3
"""Reference recipe: drive Qoder CLI CN through the official Agent SDK.

Verified working with qodercn-agent-sdk 1.0.13 against the standalone
qoderclicn 1.1.34 (via --cli / QODERCLI_PATH), auth=qodercli_auth() reusing the
browser login in ~/.qoder-cn/.auth.

Two non-obvious requirements this file encodes; both were proven the hard way:

1. YOU MUST SCRUB THE INHERITED ENVIRONMENT. The SDK adds its own
   QODER_AGENT_SDK_ENTRYPOINT / QODER_SDK_AUTH_PAYLOAD_FILE but passes the rest
   of the host environment straight through. Inherited QODERCN_CONFIG_DIR /
   QODERCN_SERVER_ENDPOINT make the child look for qodercli credentials in the
   wrong place and the handshake dies as `Control request timeout: initialize`.
   QoderAgentOptions.env accepts None values meaning "delete this variable".

2. Pin cli_path to a runtime you control. The wheel bundles a CLI that is
   several releases behind (1.1.23 in 1.0.13), which predates fixes for the
   acceptEdits auto-passes-MCP bug (1.1.28), the improved invalid-PAT error
   (1.1.27), and --max-turns actually taking effect (1.1.30).

Keeps permission decisions out of the agent's context: this script prints one
JSON line per gated tool call to --log and decides by policy, surfacing only a
compact summary on stdout.

Usage:
  python sdk_bridge.py --cwd "C:\\path\\to\\project" --prompt "..." \
      [--model GLM-5.3-Flash] [--permission-mode default] [--max-turns 25] \
      [--cli "C:\\...\\qoderclicn.exe"] [--log f.jsonl] [--out f.json] [--deny-all]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from qodercn_agent_sdk import QoderAgentOptions, query
from qodercn_agent_sdk.auth import access_token_from_env, qodercli_auth
from qodercn_agent_sdk.types import PermissionResultAllow, PermissionResultDeny

# Keep this denylist in sync with assets/qcn.sh - same host-plumbing families,
# expressed here as {name: None} so the SDK removes them from the child.
POLLUTION_FAMILIES = (
    "QODERWORK_", "DWS_", "QODER_AGENT_SDK_", "QODER_SDK_", "QODER_WORK_",
    "QODER_WORKER_", "QODERCLI_", "QODER_SECURITY_",
)
POLLUTION_EXACT = {
    # Feature flags by exact name: docs define QODERCN_FEATURE_CROSS_SESSION etc.
    # that must survive. Extend only if the host starts injecting new ones.
    "QODER_FEATURE_TASKS", "QODER_FEATURE_WORKFLOWS_DISABLE", "QODERCN_FEATURE_TASKS",
    "QODER_ENABLE_AGENT_SESSIONS", "QODERCN_ENABLE_AGENT_SESSIONS",
    "QODER_CONFIG_DIR", "QODER_SITE", "QODER_SCENE",
    "QODER_WINDOWS_SHELL_KIND", "QODER_REPEATED_TOOL_CALL_THRESHOLD",
    "QODERCN_REPEATED_TOOL_CALL_THRESHOLD", "QODERCN_SERVER_ENDPOINT",
    "QODERCN_CLI", "QODERCN_CONFIG_DIR",
}


# User intent despite prefix overlap: QODERCLI_PATH selects the CLI runtime.
POLLUTION_KEEP = frozenset({"QODERCLI_PATH"})


def is_pollution(key: str) -> bool:
    if key in POLLUTION_KEEP:
        return False
    return key.startswith(POLLUTION_FAMILIES) or key in POLLUTION_EXACT


def config_dir() -> Path:
    return Path.home() / ".qoder-cn"


def scrubbed_env() -> dict[str, str | None]:
    env: dict[str, str | None] = {k: None for k in os.environ if is_pollution(k)}
    env["QODERCN_CONFIG_DIR"] = str(config_dir())
    env["QODER_SITE"] = "cn"
    return env


def resolve_cli(explicit: str | None) -> str:
    """Mirror the SDK lookup order but refuse the stale bundled runtime."""
    for cand in (explicit, os.environ.get("QODERCLI_PATH")):
        if cand and Path(cand).is_file():
            return cand
    for cand in (
        config_dir() / "bin" / "qoderclicn" / "qoderclicn.exe",
        config_dir() / "bin" / "qoderclicn" / "qoderclicn",
    ):
        if cand.is_file():
            return str(cand)
    raise SystemExit(
        "sdk_bridge: no standalone qoderclicn found; pass --cli or set "
        "QODERCLI_PATH (avoiding the SDK's bundled runtime is deliberate)"
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--cwd", required=True)
    p.add_argument("--prompt", required=True)
    p.add_argument("--model", default="GLM-5.3-Flash")
    # NOTE: SDK modes are camelCase (acceptEdits, bypassPermissions, dontAsk,
    # yolo) unlike the CLI flags (accept_edits, ...). They are not interchangeable.
    p.add_argument("--permission-mode", default="default",
                   choices=["default", "acceptEdits", "plan", "bypassPermissions",
                            "yolo", "dontAsk", "auto"])
    p.add_argument("--max-turns", type=int, default=25)
    p.add_argument("--cli")
    p.add_argument("--log")
    p.add_argument("--out")
    p.add_argument("--deny-all", action="store_true")
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--pat", action="store_true",
                   help="use QODERCN_PERSONAL_ACCESS_TOKEN instead of qodercli login")
    return p.parse_args()


def make_logger(path: str | None):
    if not path:
        return lambda rec: None
    fh = open(path, "a", encoding="utf-8")

    def log(rec: dict) -> None:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.flush()

    return log


def make_policy(cwd: str, deny_all: bool, log):
    root = Path(cwd).resolve()

    async def can_use_tool(name, tool_input, ctx):
        log({"event": "gate", "tool": name, "input_keys": sorted(tool_input)})
        if deny_all:
            return PermissionResultDeny(behavior="deny", message="denied by --deny-all")
        if name in {"Write", "Edit", "MultiEdit"}:
            target = tool_input.get("file_path") or tool_input.get("path") or ""
            try:
                inside = target and Path(target).resolve().is_relative_to(root)
            except (OSError, ValueError):
                inside = False
            if not inside:
                log({"event": "deny_outside", "tool": name, "target": target})
                return PermissionResultDeny(
                    behavior="deny",
                    message=f"{name} outside {root} is not permitted",
                    interrupt=False,
                )
        return PermissionResultAllow(behavior="allow")

    return can_use_tool


async def run(args: argparse.Namespace) -> int:
    log = make_logger(args.log)
    kinds: list[str] = []
    result = None
    opts = QoderAgentOptions(
        auth=access_token_from_env() if args.pat else qodercli_auth(),
        cwd=args.cwd,
        cli_path=resolve_cli(args.cli),
        model=args.model,
        env=scrubbed_env(),
        permission_mode=args.permission_mode,
        can_use_tool=make_policy(args.cwd, args.deny_all, log),
        max_turns=args.max_turns,
    )
    async for msg in query(prompt=args.prompt, options=opts):
        kinds.append(type(msg).__name__)
        if type(msg).__name__ == "ResultMessage":
            result = msg
    summary = {
        "ok": bool(result) and not getattr(result, "is_error", True),
        "turns": getattr(result, "num_turns", None),
        "credits": round(getattr(result, "total_credits", 0) or 0, 4),
        "sessionId": getattr(result, "session_id", None),
        "text": (getattr(result, "result", "") or "")[:2000] if result else "",
        "messageTypes": kinds,
    }
    if args.out:
        Path(args.out).write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["ok"] else 1


def main() -> None:
    args = parse_args()
    try:
        sys.exit(asyncio.run(asyncio.wait_for(run(args), timeout=args.timeout)))
    except asyncio.TimeoutError:
        print(json.dumps({"ok": False, "error": "timeout"}), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
