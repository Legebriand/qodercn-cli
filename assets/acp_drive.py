#!/usr/bin/env python3
"""acp_drive.py -- minimal ACP (Agent Client Protocol) client driver.

Spawns a `--acp` agent process (line-delimited JSON-RPC 2.0 over stdio),
runs initialize -> session/new -> session/prompt, auto-answers
session/request_permission requests, logs every raw message to --log,
writes the final result to --out. Exit code 0 means the prompt completed.

Design rules that matter on Windows + git-bash:
  * ONE reader thread consumes the child's stdout forever; the main thread
    never blocks on a pipe read, so no handshake deadlock.
  * A second drain thread consumes the child's stderr. The child inherits
    NOTHING from our stdout/stderr: stdin/stdout/stderr are all explicit
    pipes (stderr is redirected to the log, never to the host console).
  * Writes to the child's stdin are serialized by a lock.

Usage:
  acp_drive.py --cwd <dir> --prompt <text> [--permission auto|allow|deny]
               [--timeout N] [--log FILE] [--out FILE] [--bin PATH]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time

PROTOCOL_VERSION = 1

# Exit codes
EXIT_OK = 0
EXIT_AGENT_ERROR = 1
EXIT_TIMEOUT = 2
EXIT_DRIVER_ERROR = 3

# ---------------------------------------------------------------------------
# Path handling: this script is normally invoked from git-bash with POSIX
# paths (/tmp/..., /c/Users/...), but we and the child .exe are native
# Windows. Convert before using.
# ---------------------------------------------------------------------------

def to_native(p):
    if not p:
        return p
    m = re.fullmatch(r"/([A-Za-z])(/.*)?", p)
    if m:
        return m.group(1) + ":" + (m.group(2) or "").replace("/", "\\")
    if p == "/tmp":
        return _tmpdir()
    if p.startswith("/tmp/"):
        return os.path.join(_tmpdir(), p[len("/tmp/"):].replace("/", os.sep))
    return p

def _tmpdir():
    return os.environ.get("TMP") or os.environ.get("TEMP") or tempfile.gettempdir()

# ---------------------------------------------------------------------------
# Environment scrubbing. The host (QwenWork) injects QODER*/QODERCN*/DWS*
# variables; if inherited, the CLI aborts with `sdk_invalid_args` or borrows
# the host's config/account. Denylist mirrors the host's qcn.sh bridge.
# ---------------------------------------------------------------------------

SCRUB_EXACT = {
    "QODER_CONFIG_DIR", "QODER_SITE", "QODER_SCENE", "QODER_WINDOWS_SHELL_KIND",
    "QODER_ENABLE_AGENT_SESSIONS", "QODERCN_ENABLE_AGENT_SESSIONS",
    "QODERCN_SERVER_ENDPOINT", "QODERCN_CLI", "QODERCN_CONFIG_DIR",
    # Feature flags by exact name; docs define QODERCN_FEATURE_CROSS_SESSION.
    "QODER_FEATURE_TASKS", "QODER_FEATURE_WORKFLOWS_DISABLE", "QODERCN_FEATURE_TASKS",
}
SCRUB_PREFIXES = (
    "QODERWORK_", "DWS_", "QODER_AGENT_SDK_", "QODER_SDK_",
    "QODER_WORK_", "QODER_WORKER_", "QODERCLI_",
    "QODER_SECURITY_",
)

def is_pollution(name):
    # QODERCLI_PATH selects the CLI runtime - user intent, despite QODERCLI_.
    if name == "QODERCLI_PATH":
        return False
    if name in SCRUB_EXACT:
        return True
    for pref in SCRUB_PREFIXES:
        if name.startswith(pref):
            return True
    # QODER_*_THRESHOLD and QODERCN_*_THRESHOLD
    if name.endswith("_THRESHOLD") and (name.startswith("QODER_") or name.startswith("QODERCN_")):
        return True
    return False

def build_env(home):
    env = {k: v for k, v in os.environ.items() if not is_pollution(k)}
    config_dir = os.environ.get("QCN_HOME") or os.path.join(home, ".qoder-cn")
    env["QODERCN_CONFIG_DIR"] = to_native(config_dir)
    env["QODER_SITE"] = "cn"
    env["QODER_WINDOWS_SHELL_KIND"] = "git-bash"
    return env

def find_bin(explicit):
    if explicit:
        return to_native(explicit)
    home = os.environ.get("HOME") or os.path.expanduser("~")
    cands = [
        os.path.join(home, ".qoder-cn", "bin", "qoderclicn", "qoderclicn.exe"),
        os.path.join(home, ".qoder-cn", "bin", "qoderclicn", "qoderclicn"),
        os.path.join(to_native(home), ".qoder-cn", "bin", "qoderclicn", "qoderclicn.exe"),
    ]
    for c in cands:
        if os.path.isfile(c):
            return c
    raise FileNotFoundError("qoderclicn binary not found; pass --bin. Tried: %s" % ", ".join(cands))

# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

class Driver:
    def __init__(self, args):
        self.args = args
        self.log_path = to_native(args.log)
        self.out_path = to_native(args.out)
        self.cwd = to_native(args.cwd)
        self.log_lock = threading.Lock()
        self.write_lock = threading.Lock()
        self.pending = {}          # id -> {"event": Event, "result": ..., "error": ...}
        self.pending_lock = threading.Lock()
        self.next_id = 0
        self.session_id = None
        self.child_exited = threading.Event()
        self.proc = None
        self.agent_text = []       # collected agent message chunks
        self.tool_events = []      # short summary of tool calls for --out

    # -- logging ----------------------------------------------------------
    def log(self, tag, obj):
        line = "%s [%s] %s" % (time.strftime("%H:%M:%S"), tag, obj)
        with self.log_lock:
            self.logf.write(line + "\n")
            self.logf.flush()

    # -- transport --------------------------------------------------------
    def send(self, msg):
        data = (json.dumps(msg, ensure_ascii=False) + "\n").encode("utf-8")
        self.log("send", json.dumps(msg, ensure_ascii=False))
        with self.write_lock:
            self.proc.stdin.write(data)
            self.proc.stdin.flush()

    def request(self, method, params, timeout):
        with self.pending_lock:
            self.next_id += 1
            rid = self.next_id
            slot = {"event": threading.Event()}
            self.pending[rid] = slot
        self.send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        got = slot["event"].wait(timeout)
        if not got:
            with self.pending_lock:
                self.pending.pop(rid, None)
            raise TimeoutError("no response to %s within %ss" % (method, timeout))
        if "error" in slot:
            raise RuntimeError("%s error: %s" % (method, json.dumps(slot["error"], ensure_ascii=False)))
        return slot["result"]

    def notify(self, method, params):
        self.send({"jsonrpc": "2.0", "method": method, "params": params})

    def respond(self, rid, result=None, error=None):
        msg = {"jsonrpc": "2.0", "id": rid}
        if error is not None:
            msg["error"] = error
        else:
            msg["result"] = result
        self.send(msg)

    # -- reader threads ---------------------------------------------------
    def stdout_reader(self):
        f = self.proc.stdout
        while True:
            line = f.readline()
            if not line:
                break
            self.dispatch(line)
        self.child_exited.set()
        # unblock anyone still waiting on responses
        with self.pending_lock:
            slots = list(self.pending.values())
        for slot in slots:
            slot.setdefault("error", {"code": -32000, "message": "agent process exited"})
            slot["event"].set()

    def stderr_drain(self):
        f = self.proc.stderr
        while True:
            line = f.readline()
            if not line:
                break
            try:
                text = line.decode("utf-8", "replace").rstrip("\r\n")
            except Exception:
                text = repr(line)
            if text.strip():
                self.log("stderr", text)

    # -- dispatch ---------------------------------------------------------
    def dispatch(self, raw):
        try:
            line = raw.decode("utf-8", "replace").strip()
        except Exception:
            line = repr(raw)
        if not line:
            return
        self.log("recv", line)
        try:
            msg = json.loads(line)
        except ValueError:
            return  # non-JSON banner/trace line; already logged
        if not isinstance(msg, dict):
            return
        has_id = "id" in msg
        method = msg.get("method")
        if has_id and method is not None:
            self.handle_agent_request(msg)         # agent -> client request
        elif has_id:
            with self.pending_lock:
                slot = self.pending.pop(msg["id"], None)
            if slot is not None:
                if "error" in msg:
                    slot["error"] = msg["error"]
                else:
                    slot["result"] = msg.get("result")
                slot["event"].set()
        elif method is not None:
            self.handle_notification(msg)          # agent -> client notification

    # -- agent -> client requests ------------------------------------------
    def handle_agent_request(self, msg):
        rid = msg["id"]
        method = msg["method"]
        params = msg.get("params") or {}
        try:
            if method == "session/request_permission":
                result = self.answer_permission(params)
            elif method == "authenticate":
                result = {}
            elif method == "terminal/request_permission":
                result = self.answer_permission(params)
            else:
                # fs/read_text_file, fs/write_text_file, terminal/* ...
                # We advertise no fs/terminal capabilities; refuse politely
                # rather than hang the agent.
                self.respond(rid, error={"code": -32601,
                                         "message": "client does not implement %s" % method})
                return
            self.respond(rid, result=result)
        except Exception as e:
            self.respond(rid, error={"code": -32603, "message": "driver error: %s" % e})

    def pick_option(self, options, want_allow):
        """Score permission options; return the best optionId for want_allow."""
        best, best_score = None, -1
        for opt in options:
            if not isinstance(opt, dict):
                continue
            blob = " ".join(str(opt.get(k, "")) for k in ("kind", "optionId", "name")).lower()
            is_allow = ("allow" in blob) or ("proceed" in blob) or ("approve" in blob) or ("accept" in blob)
            is_reject = ("reject" in blob) or ("deny" in blob) or ("cancel" in blob) or ("refuse" in blob)
            if want_allow and not is_allow:
                continue
            if (not want_allow) and not is_reject:
                continue
            score = 0
            if want_allow:
                if "always" in blob:
                    score = 2      # allow_always: no further interruptions
                else:
                    score = 1
            else:
                # prefer plain reject_once; avoid anything that sounds final/ban
                score = 2 if "once" in blob else 1
            if score > best_score:
                best, best_score = opt.get("optionId"), score
        return best

    def answer_permission(self, params):
        tool = params.get("toolCall") or {}
        kind = str(tool.get("kind", "other")).lower()
        title = tool.get("title", "")
        policy = self.args.permission
        if policy == "allow":
            allow = True
        elif policy == "deny":
            allow = False
        else:  # auto: allow file reads/writes, refuse shell execution
            allow = kind != "execute"
        options = params.get("options") or []
        option_id = self.pick_option(options, allow)
        if option_id is None:  # fallback: try the opposite intent, then anything
            option_id = self.pick_option(options, not allow)
        if option_id is None and options:
            option_id = options[0].get("optionId")
        self.log("policy", "kind=%s title=%r policy=%s -> allow=%s optionId=%s"
                 % (kind, title, policy, allow, option_id))
        if option_id is None:
            return {"outcome": {"outcome": "cancelled"}}
        return {"outcome": {"outcome": "selected", "optionId": option_id}}

    # -- notifications -----------------------------------------------------
    def handle_notification(self, msg):
        method = msg.get("method")
        params = msg.get("params") or {}
        if method != "session/update":
            return
        update = params.get("update") or {}
        ukind = update.get("sessionUpdate") or params.get("sessionUpdate")
        if ukind in ("agent_message_chunk", "agent_thought_chunk"):
            content = update.get("content") or params.get("content") or {}
            if isinstance(content, dict) and content.get("type") == "text":
                if ukind == "agent_message_chunk":
                    self.agent_text.append(content.get("text", ""))
        elif ukind in ("tool_call", "tool_call_update"):
            tid = update.get("toolCallId") or params.get("toolCallId")
            status = update.get("status")
            title = update.get("title")
            if title or status:
                self.tool_events.append("%s %s %s" % (ukind, title or "", status or ""))

    # -- main flow ----------------------------------------------------------
    def run(self):
        binpath = find_bin(self.args.bin)
        env = build_env(os.environ.get("HOME") or os.path.expanduser("~"))
        os.makedirs(os.path.dirname(os.path.abspath(self.log_path)), exist_ok=True)
        self.logf = open(self.log_path, "w", encoding="utf-8")
        self.log("driver", "bin=%s cwd=%s permission=%s timeout=%s"
                 % (binpath, self.cwd, self.args.permission, self.args.timeout))

        # Explicit fds everywhere: child never inherits our stdout/stderr.
        self.proc = subprocess.Popen(
            [binpath, "--acp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.cwd,
            env=env,
        )
        threading.Thread(target=self.stdout_reader, daemon=True, name="acp-reader").start()
        threading.Thread(target=self.stderr_drain, daemon=True, name="acp-stderr").start()

        hand_timeout = min(60, self.args.timeout)
        init = self.request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "clientCapabilities": {},   # no fs/terminal: agent does its own IO
        }, hand_timeout)
        self.log("driver", "initialize -> " + json.dumps(init, ensure_ascii=False))
        negotiated = init.get("protocolVersion")
        if negotiated is not None and negotiated != PROTOCOL_VERSION:
            self.log("driver", "negotiated protocolVersion=%s" % negotiated)

        new_sess = self.request("session/new", {
            "cwd": self.cwd,
            "mcpServers": [],
        }, hand_timeout)
        self.session_id = new_sess.get("sessionId")
        if not self.session_id:
            raise RuntimeError("session/new returned no sessionId: %s" % new_sess)
        self.log("driver", "sessionId=%s" % self.session_id)

        # NOTE: public ACP schema names this field `content`; this agent
        # (v1.1.34) rejects that with -32602 and requires `prompt` instead.
        result = self.request("session/prompt", {
            "sessionId": self.session_id,
            "prompt": [{"type": "text", "text": self.args.prompt}],
        }, self.args.timeout)

        return result

    def shutdown(self):
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=5)
            return
        except Exception:
            pass
        try:  # graceful cancel, then escalate
            self.notify("session/cancel", {"sessionId": self.session_id})
            self.proc.wait(timeout=8)
            return
        except Exception:
            pass
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


def main():
    ap = argparse.ArgumentParser(description="Drive a --acp agent session.")
    ap.add_argument("--cwd", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--permission", choices=["auto", "allow", "deny"], default="auto",
                    help="auto=allow reads/writes, deny shell; allow=everything; deny=everything")
    ap.add_argument("--timeout", type=int, default=600, help="seconds for the prompt turn")
    ap.add_argument("--log", default="acp_drive.log")
    ap.add_argument("--out", default="acp_result.json")
    ap.add_argument("--bin", default=None, help="path to the CLI executable")
    args = ap.parse_args()

    drv = Driver(args)
    out = {"ok": False}
    try:
        result = drv.run()
        out = {
            "ok": True,
            "sessionId": drv.session_id,
            "stopReason": (result or {}).get("stopReason"),
            "result": result,
            "agentText": "".join(drv.agent_text),
            "toolEvents": drv.tool_events,
        }
        stop = out["stopReason"]
        if stop == "refusal":
            out["ok"] = False
        code = EXIT_OK if out["ok"] else EXIT_AGENT_ERROR
    except TimeoutError as e:
        out = {"ok": False, "error": "timeout", "detail": str(e),
               "agentText": "".join(drv.agent_text)}
        code = EXIT_TIMEOUT
    except Exception as e:
        out = {"ok": False, "error": type(e).__name__, "detail": str(e),
               "agentText": "".join(drv.agent_text)}
        code = EXIT_AGENT_ERROR if isinstance(e, RuntimeError) else EXIT_DRIVER_ERROR
    finally:
        if drv.proc is not None:
            drv.shutdown()
        try:
            with open(drv.out_path, "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        try:
            drv.log("driver", "exit code=%s" % code)
            drv.logf.close()
        except Exception:
            pass
    print(json.dumps({"ok": out.get("ok", False), "stopReason": out.get("stopReason"),
                      "out": drv.out_path, "log": drv.log_path}, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
