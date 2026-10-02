#!/bin/bash
# phase2d_mac_perf.sh — Mac perf pass: build once + walk ALL levels 0..99 with perf=1.
#
# Usage:  phase2d_mac_perf.sh <tag> [repo_dir]
#   tag        run tag (perf artifacts under ~/orca/cjmp/m2/)
#   repo_dir   repo root (default: resolved from this script's location)
#
# Dependencies (macOS only — do NOT run on box):
#   • source ~/orca/cjmp/env.sh   (Keels OpenSDK 0.2.2: CJMP_SDK_HOME + keels on PATH)
#   • harness dir, default ~/orca/cjmp/mech/harness_p (override: M2_HARNESS).
#     Operator-provided, NOT part of the repo. Must contain: m2p_run.sh,
#     m2_play.py, perf_report.py, test_dfs.py, rejects.json, levels.json,
#     solutions.json. This script unconditionally overwrites harness
#     solutions.json + levels.json from repo copies (walking 0..99 with all
#     mechanics off needs the full solutions + levels); rejects.json belongs
#     to the harness dir and is never touched.
#   • repo files mobile/cjmp/scripts/phase2d_solutions_mech.json and
#     mobile/shared/levels/levels.json
#   • python3, zsh
# macOS bash 3.2 compatible. set -u only (RC collected, not fatal).
set -u

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*"; }

TAG="${1:-}"
if [ -z "$TAG" ]; then
  echo "Usage: $0 <tag> [repo_dir]" >&2
  exit 2
fi

# Repo root — same resolution as build_from_repo.sh
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -d "$SCRIPT_DIR/../../entry" ]; then
  REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"
else
  REPO="$(cd "$SCRIPT_DIR/../../.." && pwd)"
fi
if [ "$#" -ge 2 ] && [ -n "$2" ]; then REPO="$2"; fi

HARNESS="${M2_HARNESS:-$HOME/orca/cjmp/mech/harness_p}"
SOL_SRC="$REPO/mobile/cjmp/scripts/phase2d_solutions_mech.json"
LVL_SRC="$REPO/mobile/shared/levels/levels.json"
PLATFORMS="${M2_PLATFORMS:-ios,android}"

# --- Device guard: never touch other machines' emulator/simulator -------------
AS="${M2_AS:-emulator-5562}"
UDID="${M2_UDID:-57BC648D-148E-4E14-9EF5-9E0C6C7D284E}"
log "M2_AS=$AS  M2_UDID=$UDID"
case "$AS" in
  emulator-5560|emulator-5554|127.0.0.1:5555)
    echo "ERROR: refusing protected Android device $AS" >&2; exit 9 ;;
esac
case "$UDID" in
  8C2F530F*|97D4B29F*)
    echo "ERROR: refusing protected iOS simulator $UDID" >&2; exit 9 ;;
esac

# --- Disk guard: build + perf logs need headroom -----------------------------
AVAIL_KB="$(df -k "$HOME" 2>/dev/null | awk 'NR==2 {print $4}')"
if [ -n "${AVAIL_KB:-}" ] && [ "$AVAIL_KB" -lt 6291456 ]; then
  echo "ERROR: only ${AVAIL_KB}kB free under $HOME (need >= 6GB)" >&2; exit 1
fi

log "repo=$REPO"
log "harness=$HARNESS"
if [ ! -f "$SOL_SRC" ]; then echo "ERROR: missing $SOL_SRC" >&2; exit 1; fi
if [ ! -f "$LVL_SRC" ]; then echo "ERROR: missing $LVL_SRC" >&2; exit 1; fi
if [ ! -f "$HARNESS/m2p_run.sh" ]; then echo "ERROR: missing $HARNESS/m2p_run.sh" >&2; exit 1; fi

# --- Sync repo-owned data into the harness dir (no backup/restore dance) -----
cp "$SOL_SRC" "$HARNESS/solutions.json" && log "solutions.json <- phase2d_solutions_mech.json"
cp "$LVL_SRC" "$HARNESS/levels.json" && log "levels.json <- mobile/shared/levels/levels.json"

# m2p_run.sh: <tag> <repo> <platforms> <first_id> <last_id> <shot_ids> [start_override] [perf] [skip_build]
# first=0 last=99 (all levels), shot_ids empty (no screenshots), start_override
# empty (use repo default) but the positional slot must exist -> "" placeholder,
# perf=1, skip_build=0 (build once). NOTE: M2_TAP_ONLY / M2_MECH_IDS are
# deliberately NOT set here so the numbers stay comparable with the baseline.
RUN_RC=0
log "RUN: m2p_run.sh ${TAG}_perf  repo=$REPO platforms=$PLATFORMS 0 99 \"\" \"\" 1 0"
zsh "$HARNESS/m2p_run.sh" "${TAG}_perf" "$REPO" "$PLATFORMS" 0 99 "" "" 1 0 || RUN_RC=$?
log "RUN_RC=$RUN_RC"

# --- Where the results live (perf_report.py is invoked per-platform by
# m2p_run.sh itself; it needs <out_dir> <platform>, so we do not call it here) --
OUT_DIR="$HOME/orca/cjmp/m2/out/${TAG}_perf"
log "results dir: $OUT_DIR"
log "  $OUT_DIR/run.log"
log "  $OUT_DIR/ios-stdout.txt"
log "  $OUT_DIR/android-logcat.txt"

cat <<'BASline'

=== baseline comparison ===
Compare these numbers against the existing latency baselines in
  /workspace/cjmp-smoke/m2/lat/lat_final.md   (box; no m2/lat copy on Mac)
BASline

exit "$RUN_RC"
