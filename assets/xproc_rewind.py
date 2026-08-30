#!/usr/bin/env python3
r"""xproc_rewind.py - verified recipe for rewinding a *finished* CLI process's edits.

Why this exists: `rewind_files.py` proves rewind inside one SDK session. The real
need is "that delegation already exited and made a mess - undo it". This script
runs as two separate processes and shows it works, because checkpoints live on
disk at ~/.qoder-cn/file-history/<session-id>/<hash>@v<N>, not in memory and NOT
in the SessionStore (checkpoint blobs are outside that contract).

Verified on this machine (CLI 1.1.34 / SDK 1.0.13):
  phase A: Write lands, process exits, session_id captured from the stream.
  phase B: new process, QoderSDKClient(resume=<sid>) -> rewind_files(mid, dry_run=True)
           returns canRewind:True with the right path -> apply -> file back to OLD.

Assertions are deliberately written so a *model* misbehaving cannot fail them:
phase A only requires the target to have CHANGED, not to equal an exact string -
cheap models genuinely truncate literal payloads (observed: asked for
"NEW-CONTENT", wrote "NEW-CO"), and that is not a rewind failure.

Usage:
  python xproc_rewind.py --phase A --repo "C:\\proj" --target "C:\\proj\\note.txt" --state "C:\\st.json"
  python xproc_rewind.py --phase B --repo "C:\\proj" --target "C:\\proj\\note.txt" --state "C:\\st.json"
Do not pass --no-session-persistence / options.session_store: no persisted session means
no anchor to resume into, and session_store is mutually exclusive with checkpointing.
"""
import argparse, asyncio, json, os, sys, uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdk_bridge as SB
from qodercn_agent_sdk import QoderAgentOptions, QoderSDKClient
from qodercn_agent_sdk.auth import qodercli_auth
from qodercn_agent_sdk.types import PermissionResultAllow

R = argparse.ArgumentParser(description=__doc__.splitlines()[0])
R.add_argument("--phase", required=True, choices=["A", "B"])
R.add_argument("--repo", required=True)
R.add_argument("--target", required=True)
R.add_argument("--state", required=True)
R.add_argument("--old", default="OLD-CONTENT")
R.add_argument("--new", default="NEWCONTENT-DONTCARE")
R.add_argument("--model", default=None,
               help="omit to use the CLI's own settings model.name")
a = R.parse_args()

calls = []


async def allow(name, tool_input, ctx):
    calls.append(name)
    return PermissionResultAllow(behavior="allow")


def opts(extra=None):
    base = dict(auth=qodercli_auth(), cwd=a.repo, cli_path=SB.resolve_cli(None),
                env=SB.scrubbed_env(), permission_mode="acceptEdits",
                enable_file_checkpointing=True, can_use_tool=allow, max_turns=12)
    if a.model:
        base["model"] = a.model
    base.update(extra or {})
    return QoderAgentOptions(**base)


def read():
    return open(a.target, encoding="utf-8").read().strip() if os.path.exists(a.target) else None


def emit(rows):
    ok = True
    for n, p, d in rows:
        print(("PASS " if p else "FAIL ") + n + " :: " + str(d)[:200])
        ok = ok and p
    print("RESULT " + ("CROSS_PROC_REWIND_VERIFIED" if ok else "CROSS_PROC_REWIND_FAILED"))
    sys.exit(0 if ok else 1)


async def phase_a():
    open(a.target, "w", encoding="utf-8").write(a.old + "\n")
    mid = str(uuid.uuid4())
    sid = None
    rows = []
    async with QoderSDKClient(opts()) as c:
        await c.query("必须真正调用 Write 工具一次：用内容 " + a.new + " 覆盖绝对路径 " +
                      a.target + " 。禁止用文字代替工具调用；完成后只回复 done",
                      message_uuid=mid)
        async for m in c.receive_response():
            s = getattr(m, "session_id", None)
            if isinstance(s, str) and s:
                sid = s
            if type(m).__name__ == "ResultMessage":
                break
        cur = read()
        rows.append(("A_file_changed", cur is not None and cur != a.old, cur))
        rows.append(("A_session_captured", bool(sid), sid))
    json.dump({"mid": mid, "sid": sid}, open(a.state, "w", encoding="utf-8"))
    hist = os.path.join(os.path.expanduser("~"), ".qoder-cn", "file-history", sid or "")
    rows.append(("A_checkpoint_on_disk", os.path.isdir(hist), hist))
    emit(rows)


async def phase_b():
    st = json.load(open(a.state, encoding="utf-8"))
    mid, sid = st["mid"], st["sid"]
    rows = [("B_precondition_changed", read() != a.old, read())]
    try:
        async with QoderSDKClient(opts({"resume": sid})) as c:
            dry = await c.rewind_files(mid, dry_run=True)
            rows.append(("B_can_rewind", bool(dry.get("canRewind")), dry))
            rows.append(("B_preview_lists_target",
                         any(os.path.basename(a.target) in str(f)
                             for f in (dry.get("filesChanged") or [])), dry.get("filesChanged")))
            await c.rewind_files(mid)
            rows.append(("B_reverted_to_old", read() == a.old, read()))
    except Exception as e:
        rows.append(("B_no_exception", False, repr(e)[:400]))
    emit(rows)


asyncio.run(asyncio.wait_for(phase_a() if a.phase == "A" else phase_b(), timeout=420))
