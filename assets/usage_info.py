#!/usr/bin/env python3
r"""usage_info.py - read the sibling account's quota WITHOUT spending credits.

Why this exists: docs describe /usage as an interactive-only panel. True for the slash
command, false for the data - the SDK has a control request `get_usage_info` that costs
zero credits and touches no model. It is the cheapest possible diagnostic and the one
that separates "this model's pool is drained" from "the CLI is broken".

The trap this script exists to defuse: QoderSDKClient.get_usage_info() normalizes the
server payload down to userQuota / addOnQuota / orgResourcePackage and **silently drops
`dedicatedResourcePackages`** - which is where the daily Qwen-exclusive grant lives. So
the SDK happily reports isQuotaExceeded=true with remaining=0 while several hundred
usable credits sit in a package it never shows you. The CLI *does* log the raw payload,
so this script re-reads the run log it just produced and prints the full picture.

Usage:  python usage_info.py [--json] [--no-log-mine]
"""
import argparse, asyncio, glob, json, os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdk_bridge as SB
from qodercn_agent_sdk import QoderAgentOptions, QoderSDKClient
from qodercn_agent_sdk.auth import qodercli_auth

R = argparse.ArgumentParser(description=__doc__.splitlines()[0])
R.add_argument("--json", action="store_true", help="dump raw + normalized together")
R.add_argument("--no-log-mine", action="store_true",
               help="skip re-reading the CLI log for dedicatedResourcePackages")
R.add_argument("--cwd", default=os.getcwd())
a = R.parse_args()


def config_dir():
    return os.path.join(os.path.expanduser("~"), ".qoder-cn")


def mine_packages(since_ts):
    """Pull the raw quota payload the CLI logged during this run."""
    best = None
    for f in glob.glob(os.path.join(config_dir(), "logs", "runs", "*", "qodercli.log")):
        try:
            if os.path.getmtime(f) < since_ts - 5:
                continue
            t = open(f, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        i = t.find("dedicatedResourcePackages")
        if i < 0:
            continue
        if best is None or os.path.getmtime(f) > best[0]:
            best = (os.path.getmtime(f), t[i:])
    if not best:
        return []
    seg = best[1][:4000]
    pkgs = []
    for m in re.finditer(r'\{"id":"([^"]+)","name":"([^"]+)"', seg):
        blk = seg[m.start():m.start() + 1200]
        g = lambda k: (re.search(r'"%s":([0-9.]+)' % k, blk) or [None, None])[1]
        e = re.search(r'"expiresAt":([0-9]+)', blk)
        av = re.search(r'"available":(true|false)', blk)
        zh = re.search(r'"zh-CN":"([^"]+)"', blk)
        pkgs.append({
            "name": m.group(2), "total": g("total"), "used": g("used"),
            "remaining": g("remaining"),
            "expiresAt": (time.strftime("%Y-%m-%d %H:%M",
                        time.localtime(int(e.group(1)) / 1000)) if e else None),
            "available": (av.group(1) == "true" if av else None),
            "label_zh": (zh.group(1) if zh else None),
        })
    return pkgs


def bucket(u, name):
    b = u.get(name) or {}
    if not b:
        print("%-18s <absent>" % name)
        return
    print("%-18s used=%s total=%s remaining=%s pct=%s unit=%s" % (
        name, b.get("used"), b.get("total"), b.get("remaining"),
        b.get("percentage"), b.get("unit")))


async def main():
    since = time.time()
    opts = QoderAgentOptions(auth=qodercli_auth(), cwd=a.cwd, cli_path=SB.resolve_cli(None),
                             env=SB.scrubbed_env(), max_turns=1)
    async with QoderSDKClient(opts) as c:
        u = await c.get_usage_info()
    if u is None:
        print("RESULT NO_USAGE_INFO (CLI returned nothing - check auth / cli_path)")
        return 2
    pkgs = [] if a.no_log_mine else mine_packages(since)
    if a.json:
        print(json.dumps({"sdk_normalized": u, "dedicatedResourcePackages": pkgs},
                         ensure_ascii=False, indent=2, default=str))
        return 0
    print("userId=%s userType=%s isHighestTier=%s" % (u.get("userId"), u.get("userType"),
                                                      u.get("isHighestTier")))
    print("totalUsagePercentage=%s isQuotaExceeded=%s isPlanQuotaProrated=%s" % (
        u.get("totalUsagePercentage"), u.get("isQuotaExceeded"), u.get("isPlanQuotaProrated")))
    print("plan expiresAt=%s" % u.get("expiresAt"))
    for k in ("userQuota", "addOnQuota", "orgResourcePackage"):
        bucket(u, k)
    if pkgs:
        print("-- dedicatedResourcePackages (dropped by the SDK normalizer) --")
        for p in pkgs:
            print("  %-18s total=%s used=%s remaining=%s available=%s expires=%s" % (
                p["name"], p["total"], p["used"], p["remaining"], p["available"], p["expiresAt"]))
            if p["label_zh"]:
                print("    label: %s" % p["label_zh"][:90])
    else:
        print("-- dedicatedResourcePackages: none found in the run log "
              "(account may have no grant, or log rotation) --")
    s = u.get("session") or {}
    print("session total_credits=%s per-model=%s" % (s.get("total_credits"), s.get("model_usage")))
    live = sum(float(p["remaining"] or 0) for p in pkgs if p.get("available"))
    plan = float((u.get("userQuota") or {}).get("remaining") or 0)
    print("VERDICT plan_remaining=%s dedicated_remaining=%s -> %s" % (
        plan, live,
        "usable now (Qwen pack)" if plan == 0 and live > 0 else
        "usable" if (plan > 0 or live > 0) else "nothing left"))
    print("RESULT OK")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(asyncio.wait_for(main(), timeout=120)))
