#!/usr/bin/env bash
# Bridge to the standalone Qoder CLI CN in headless mode.
#
# QwenWork runs on the same @qoder-ai/qoder-agent-sdk engine and injects its own
# QODER*/QODERCN*/DWS* variables into every shell. Left in place they make the
# sibling CLI (a) abort with `sdk_invalid_args`, because it thinks it is a
# worker speaking stream-json, and (b) read QwenWork's config dir, so it
# borrows the wrong account. Scrub them and the CLI falls back to its own
# install at ~/.qoder-cn with its own login and its own credits.
#
# Scrubbing is a DENYLIST, not a prefix regex. Qoder CLI CN documents a set of
# legitimate user-facing variables that share those prefixes - above all
# QODERCN_PERSONAL_ACCESS_TOKEN, which overrides saved /login credentials. A
# blanket ^(QODER|QODERCN|DWS) wipe silently destroys a user's PAT auth plus
# their model / permission-mode / sandbox defaults.
set -uo pipefail

die() { echo "qodercn-bridge: $*" >&2; exit 127; }

# The whole point of this script is to neutralize hostile/inherited env, so do
# not let QCN_HOME be pointed anywhere outside $HOME - an attacker-controlled
# value would make us exec a planted qoderclicn.exe.
if [ -n "${QCN_HOME:-}" ]; then
  case "$QCN_HOME" in
    "$HOME"/*) : ;;
    *) die "refusing QCN_HOME outside \$HOME (expected under $HOME/.qoder-cn)" ;;
  esac
else
  QCN_HOME="$HOME/.qoder-cn"
fi

IS_WINDOWS=0
case "$(uname -s 2>/dev/null)" in
  MINGW*|MSYS*|CYGWIN*) IS_WINDOWS=1 ;;
esac

to_win() {
  if [ "$IS_WINDOWS" -ne 1 ]; then printf '%s' "$1"; return 0; fi
  command -v cygpath >/dev/null 2>&1 || die "cygpath not found; needed to pass Windows paths to the native exe"
  local out
  out="$(cygpath -w "$1" 2>/dev/null)" || die "cygpath failed for $1"
  # A PATH-hijacked fake cygpath could redirect QODERCN_CONFIG_DIR anywhere.
  case "$out" in
    [A-Za-z]:\\*) printf '%s' "$out" ;;
    *) die "cygpath returned a non-Windows path for $1: $out" ;;
  esac
}

BIN=""
for c in "$QCN_HOME/bin/qoderclicn/qoderclicn.exe" "$QCN_HOME/bin/qoderclicn/qoderclicn"; do
  [ -f "$c" ] && { BIN="$c"; break; }
done
[ -n "$BIN" ] || die "Qoder CLI CN not found under $QCN_HOME/bin/qoderclicn/ - install it from https://qoder.cn"

# `.auth` is what a completed browser login leaves behind. A PAT-only user has
# no .auth, so treat its absence as fatal only when no token was supplied.
if [ ! -e "$QCN_HOME/.auth" ] && [ -z "${QODERCN_PERSONAL_ACCESS_TOKEN:-}" ]; then
  die "no login state at $QCN_HOME/.auth and QODERCN_PERSONAL_ACCESS_TOKEN is unset - run 'qodercn' then /login, or export a PAT from https://qoder.cn/account/integrations"
fi

# QwenWork-injected host plumbing only. Anything not listed here is passed
# through untouched, so documented CLI variables keep working.
is_pollution() {
  # QODERCLI_PATH is the documented override for choosing the CLI runtime, so
  # it is user intent even though it matches the QODERCLI_* host-plumbing prefix.
  case "$1" in QODERCLI_PATH) return 1 ;; esac
  case "$1" in
    QODERWORK_*|DWS_*) return 0 ;;
    QODER_AGENT_SDK_*|QODER_SDK_*|QODER_WORK_*|QODER_WORKER_*|QODERCLI_*) return 0 ;;
    QODER_SECURITY_*) return 0 ;;
    # Feature flags go by exact name, NOT by QODER_FEATURE_*/QODERCN_FEATURE_*
    # families: the docs define CLI feature flags we must not eat, e.g.
    # QODERCN_FEATURE_CROSS_SESSION (cross-session messaging). QwenWork currently
    # injects only the three below; add new ones here if it starts injecting more.
    QODER_FEATURE_TASKS|QODER_FEATURE_WORKFLOWS_DISABLE|QODERCN_FEATURE_TASKS) return 0 ;;
    QODER_ENABLE_AGENT_SESSIONS|QODERCN_ENABLE_AGENT_SESSIONS) return 0 ;;
    QODER_CONFIG_DIR|QODER_SITE|QODER_SCENE|QODER_WINDOWS_SHELL_KIND) return 0 ;;
    QODER_REPEATED_TOOL_CALL_THRESHOLD|QODERCN_REPEATED_TOOL_CALL_THRESHOLD) return 0 ;;
    QODERCN_SERVER_ENDPOINT|QODERCN_CLI) return 0 ;;
    QODERCN_CONFIG_DIR) return 0 ;;  # re-set below unless the caller passed --config-dir
  esac
  return 1
}

SCRUB=()
while IFS= read -r v; do
  [ -n "$v" ] || continue
  if is_pollution "$v"; then SCRUB+=("-u" "$v"); fi
done < <(env | sed -n -E 's/^([^=]*)=.*/\1/p' | sort -u)

# A caller-supplied --config-dir wins; do not fight it with the env var.
set_config_dir=1
for a in "$@"; do
  case "$a" in --config-dir|--config-dir=*) set_config_dir=0 ;; esac
done

EXEC=(env)
[ ${#SCRUB[@]} -gt 0 ] && EXEC+=("${SCRUB[@]+"${SCRUB[@]}"}")
EXEC+=(QODER_SITE=cn QODER_WINDOWS_SHELL_KIND=git-bash)
[ "$set_config_dir" -eq 1 ] && EXEC+=(QODERCN_CONFIG_DIR="$(to_win "$QCN_HOME")")

exec "${EXEC[@]}" "$BIN" "$@"
