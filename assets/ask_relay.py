#!/usr/bin/env python3
r"""ask_relay.py - human-in-the-loop permission relay for Qoder CLI CN over the SDK.

把 can_use_tool 挂到一对文件上，实现"脚本持有会话、只在真要人拍板时冒一行"：
  问题 -> outbox（每行一条 JSON，含 id/tool/input）
  答复 -> inbox  （一行 "N: allow" / "N: allow_always" / "N: deny 理由"）

为什么走文件而不是 stdin：宿主 agent 的 shell 每次调用都是新进程，无法跨调用维持
stdin；文件信箱让"发起"与"作答"落在两次独立调用里，且后台进程不会占住宿主管道。

用法（宿主侧两轮）：
  nohup python ask_relay.py --cwd "C:\proj" --prompt "..." --outbox q.jsonl \
        --inbox a.txt --ask-timeout 180 --on-timeout deny > relay.log 2>&1 < /dev/null &
  # 稍后读 q.jsonl 取得待决问题 -> 问人 -> 把 "1: allow" 追加进 a.txt
  # 结束看 --out 的 summary

退出码 0 表示会话正常结束（不代表每个工具调用都被放行）。
"""
import argparse, asyncio, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdk_bridge as SB
from qodercn_agent_sdk import QoderSDKClient, QoderAgentOptions
from qodercn_agent_sdk.auth import access_token_from_env, qodercli_auth
from qodercn_agent_sdk.types import PermissionResultAllow, PermissionResultDeny


def parse_args():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--cwd", required=True)
    p.add_argument("--prompt", required=True)
    p.add_argument("--outbox", required=True)
    p.add_argument("--inbox", required=True)
    p.add_argument("--out")
    p.add_argument("--model", default="GLM-5.3-Flash")
    p.add_argument("--permission-mode", default="default",
                   choices=["default", "acceptEdits", "plan", "bypassPermissions", "yolo", "dontAsk", "auto"])
    p.add_argument("--max-turns", type=int, default=25)
    p.add_argument("--ask-timeout", type=int, default=180, help="等待人工答复的秒数")
    p.add_argument("--on-timeout", default="deny", choices=["deny", "allow"])
    p.add_argument("--cli")
    p.add_argument("--pat", action="store_true")
    p.add_argument("--session-timeout", type=int, default=900)
    return p.parse_args()


class Relay:
    def __init__(self, args):
        self.args = args
        self.seq = 0
        self.auto_allow = False
        self.log = open(args.outbox, "a", encoding="utf-8")
        self.asked = []

    def _answers(self):
        """读 inbox，容忍宿主边写边被读到半行的情况。"""
        out = {}
        try:
            with open(self.args.inbox, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or ":" not in line:
                        continue
                    k, v = line.split(":", 1)
                    try:
                        out[int(k.strip())] = v.strip()
                    except ValueError:
                        pass
        except FileNotFoundError:
            pass
        return out

    async def __call__(self, name, tool_input, ctx):
        if self.auto_allow:
            self.asked.append({"tool": name, "decision": "auto_allow_previously"})
            return PermissionResultAllow(behavior="allow")
        self.seq += 1
        n = self.seq
        self.log.write(json.dumps({"id": n, "tool": name, "input": tool_input}, ensure_ascii=False) + "\n")
        self.log.flush()
        deadline = time.time() + self.args.ask_timeout
        while time.time() < deadline:
            ans = self._answers().get(n)
            if ans:
                low = ans.lower()
                if low.startswith("allow_always"):
                    self.auto_allow = True
                    self.asked.append({"id": n, "tool": name, "decision": "allow_always"})
                    return PermissionResultAllow(behavior="allow")
                if low.startswith("allow"):
                    self.asked.append({"id": n, "tool": name, "decision": "allow"})
                    return PermissionResultAllow(behavior="allow")
                if low.startswith("deny"):
                    reason = ans[4:].strip() or "denied by operator"
                    self.asked.append({"id": n, "tool": name, "decision": "deny", "reason": reason})
                    return PermissionResultDeny(behavior="deny", message=reason)
            await asyncio.sleep(1)
        self.asked.append({"id": n, "tool": name, "decision": "timeout"})
        if self.args.on_timeout == "allow":
            return PermissionResultAllow(behavior="allow")
        return PermissionResultDeny(behavior="deny", message="no decision within timeout")


async def run(args, relay):
    opts = QoderAgentOptions(auth=access_token_from_env() if args.pat else qodercli_auth(),
                             cwd=args.cwd, cli_path=SB.resolve_cli(args.cli), model=args.model,
                             env=SB.scrubbed_env(), permission_mode=args.permission_mode,
                             can_use_tool=relay, max_turns=args.max_turns)
    kinds, res = {}, None
    async with QoderSDKClient(opts) as c:
        await c.query(args.prompt)
        async for m in c.receive_response():
            kinds[type(m).__name__] = kinds.get(type(m).__name__, 0) + 1
            if type(m).__name__ == "ResultMessage":
                res = m
    return {"ok": bool(res) and not res.is_error, "turns": getattr(res, "num_turns", None),
            "credits": round(getattr(res, "total_credits", 0) or 0, 4),
            "sessionId": getattr(res, "session_id", None),
            "text": (getattr(res, "result", "") or "")[:1500], "messages": kinds,
            "decisions": relay.asked}


def main():
    args = parse_args()
    relay = Relay(args)
    try:
        summary = asyncio.run(asyncio.wait_for(run(args, relay), timeout=args.session_timeout))
    except Exception as e:
        summary = {"ok": False, "error": type(e).__name__, "detail": str(e)[:400],
                   "decisions": relay.asked}
    # 根治读数器歧义：自己定绝对路径并把它打印出来，调用方只读这一个值。
    # （此前一次"deny 未取到证据"就是调用侧自己拼路径拼错造成的。）
    if args.out:
        out = os.path.abspath(args.out)
        summary["summaryPath"] = out
    line = json.dumps(summary, ensure_ascii=False)
    if args.out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(line)
    print(line)


if __name__ == "__main__":
    main()
