#!/usr/bin/env python3
r"""rewind_files.py - verified minimal recipe for headless file rewind.

Why this exists: `rollback` is the CLI's *version* rollback, not undo. Real file
rewind in headless mode goes through the SDK, and the anchor message UUID must be
supplied by the caller (the SDK auto-generates one for plain-string prompts and
never surfaces it, which yields `no snapshot found for message ...`).

Hard-won gotchas encoded here, each proven on this machine:
1. Without `can_use_tool` every confirmation-requiring tool call FAILS SILENTLY,
   regardless of permission_mode - so the write never happens and there is nothing
   to rewind. This bridge always passes a callback.
2. `session_store` and `enable_file_checkpointing` are mutually exclusive.
3. Read the change preview from `dry_run=True`; the post-apply call returns
   `insertions/deletions` as 0 because the diff has already been applied.

Usage:
  python rewind_files.py --cwd "C:\proj" --target "<abs path to overwrite>" \
      --old "OLD" --new "NEW" [--model Qwen3.8-Flash] [--check-only]
Runs: write NEW (checkpointed) -> assert written -> dry_run preview -> rewind ->
assert content is back to OLD. Prints a PASS/FAIL line per assertion.
"""
import argparse, asyncio, os, sys, uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdk_bridge as SB
from qodercn_agent_sdk import QoderAgentOptions, QoderSDKClient
from qodercn_agent_sdk.auth import qodercli_auth
from qodercn_agent_sdk.types import PermissionResultAllow


def parse():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--cwd", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--old", default="OLD-CONTENT")
    p.add_argument("--new", default="NEW-CONTENT")
    # 省略 --model 即沿用 CLI 自己的 settings.json；GLM-5.3-Flash 已实测走空池(error_code=118)
    p.add_argument("--model", default=None)
    p.add_argument("--check-only", action="store_true", help="only run the dry_run preview")
    p.add_argument("--timeout", type=int, default=300)
    return p.parse_args()


async def run(a):
    results = []
    with open(a.target, "w", encoding="utf-8") as f:
        f.write(a.old + "\n")
    mid = str(uuid.uuid4())
    seen = []

    async def allow(name, tool_input, ctx):
        seen.append(name)
        return PermissionResultAllow(behavior="allow")

    opts = QoderAgentOptions(auth=qodercli_auth(), cwd=a.cwd, cli_path=SB.resolve_cli(None),
                             model=a.model, env=SB.scrubbed_env(),
                             permission_mode="acceptEdits", enable_file_checkpointing=True,
                             can_use_tool=allow, max_turns=12)
    text = ("必须真正调用 Write 工具一次：用内容 " + a.new + " 覆盖绝对路径 " + a.target +
            " 。禁止用文字代替工具调用；完成后只回复 done")
    async with QoderSDKClient(opts) as c:
        await c.query(text, message_uuid=mid)
        async for m in c.receive_response():
            if type(m).__name__ == "ResultMessage":
                break
        cur = open(a.target, encoding="utf-8").read().strip() if os.path.exists(a.target) else None
        results.append(("write_landed", cur == a.new, cur))
        dry = await c.rewind_files(mid, dry_run=True)
        results.append(("preview_has_changes", bool(dry.get("filesChanged")), dry))
        if a.check_only:
            return results
        real = await c.rewind_files(mid)
        after = open(a.target, encoding="utf-8").read().strip() if os.path.exists(a.target) else None
        results.append(("reverted_to_old", after == a.old, after))
        results.append(("real_files_changed", bool(real.get("filesChanged")), real))
        results.append(("preview_matches_applied_paths",
                        sorted(dry.get("filesChanged") or []) == sorted(real.get("filesChanged") or []),
                        (dry.get("filesChanged"), real.get("filesChanged"))))
    return results


def main():
    a = parse()
    r = asyncio.run(asyncio.wait_for(run(a), timeout=a.timeout))
    ok = True
    for name, passed, detail in r:
        print(("PASS " if passed else "FAIL ") + name + " :: " + str(detail)[:160])
        ok = ok and passed
    print("RESULT " + ("REWIND_VERIFIED" if ok else "REWIND_FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
