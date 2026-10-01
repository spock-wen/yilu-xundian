#!/bin/bash
# phase2d_mac_perf.sh — Mac perf pass: build once + walk ALL levels 0..99 with perf=1.
#
# Usage:  phase2d_mac_perf.sh <tag> [repo_dir]
#   tag        run tag (perf artifacts under ~/orca/cjmp/m2/)
#   repo_dir   repo root (default: resolved from this script's location)
#
# Dependencies (macOS only — do NOT run on box):
#   • source ~/orca/cjmp/env.sh   (Keels OpenSDK 0.2.2: CJMP_SDK_HOME + keels on PATH)
#   • harness dir ~/orca/cjmp/m2/harness_p  (m2p_run.sh / m2_play.py / solutions.json / perf_report.py)
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

HARNESS="$HOME/orca/cjmp/m2/harness_p"
log "repo=$REPO"
log "harness=$HARNESS"
if [ ! -f "$HARNESS/m2p_run.sh" ]; then echo "ERROR: missing $HARNESS/m2p_run.sh" >&2; exit 1; fi

# m2p_run.sh: <tag> <repo> <platforms> <first_id> <last_id> <shot_ids> [start_override] [perf] [skip_build]
# first=0 last=99 (all levels), shot_ids empty (no screenshots), start_override
# empty (use repo default) but the positional slot must exist -> "" placeholder,
# perf=1, skip_build=0 (build once).
RUN_RC=0
log "RUN: m2p_run.sh ${TAG}_perf  repo=$REPO platforms=ios,android 0 99 \"\" \"\" 1 0"
zsh "$HARNESS/m2p_run.sh" "${TAG}_perf" "$REPO" ios,android 0 99 "" "" 1 0 || RUN_RC=$?
log "RUN_RC=$RUN_RC"

# perf_report.py output (incl. any touch handler_us stats) is kept verbatim —
# run it best-effort for a fresh printout; failures are not fatal.
if [ -f "$HARNESS/perf_report.py" ]; then
  log "perf_report.py:"
  python3 "$HARNESS/perf_report.py" 2>&1 || log "perf_report.py exited $? (ignored)"
fi

cat <<'BASline'

=== baseline comparison ===
Compare these numbers against the existing latency baselines in
  Mac:   ~/orca/cjmp/m2/lat
  (box copy of the same data: /workspace/cjmp-smoke/m2/lat)
BASline

exit "$RUN_RC"
