#!/bin/bash
# phase2d_mac_verify.sh — Mac one-shot "build once + mechanism-level screenshots".
#
# Usage:  phase2d_mac_verify.sh <tag> [repo_dir]
#   tag        run tag; screenshots land under ~/orca/cjmp/m2/out/<tag>*
#   repo_dir   repo root (default: resolved from this script's location)
#
# Dependencies (macOS only — do NOT run on box):
#   • source ~/orca/cjmp/env.sh   (Keels OpenSDK 0.2.2: CJMP_SDK_HOME + keels on PATH)
#   • harness dir ~/orca/cjmp/m2/harness_p  (m2p_run.sh / m2_play.py / solutions.json / perf_report.py)
#   • repo file mobile/cjmp/scripts/phase2d_solutions_mech.json (X1-generated input-sequence
#     solutions for slide/ferry levels; path field is an INPUT sequence, not a full path)
#   • python3, zsh
# macOS bash 3.2 compatible. set -u only (per-step RCs are collected, not fatal).
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
SOL_SRC="$REPO/mobile/cjmp/scripts/phase2d_solutions_mech.json"
SOL_DST="$HARNESS/solutions.json"
REP_IDS="30,40,52,67,70,80,90,95"   # representative mechanism levels

log "repo=$REPO"
log "harness=$HARNESS"
if [ ! -f "$SOL_SRC" ]; then echo "ERROR: missing $SOL_SRC" >&2; exit 1; fi
if [ ! -f "$HARNESS/m2p_run.sh" ]; then echo "ERROR: missing $HARNESS/m2p_run.sh" >&2; exit 1; fi
if [ ! -f "$SOL_DST" ] && [ ! -f "$SOL_DST.bak" ]; then
  echo "ERROR: missing $SOL_DST (nothing to back up)" >&2; exit 1
fi

# --- Swap solutions.json (m2_play STOPs on levels without a solution) --------
# Back up once (keep an existing .bak: it may hold the pristine file from a
# previous interrupted run), restore on EXIT either way.
restore_sols() {
  if [ -f "$SOL_DST.bak" ]; then
    mv -f "$SOL_DST.bak" "$SOL_DST"
    log "solutions.json restored from .bak"
  fi
}
trap restore_sols EXIT
if [ ! -f "$SOL_DST.bak" ]; then
  cp "$SOL_DST" "$SOL_DST.bak" && log "solutions.json -> solutions.json.bak"
fi
cp "$SOL_SRC" "$SOL_DST" && log "solutions.json <- phase2d_solutions_mech.json"

# --- One build + one play pass over 30..95 ----------------------------------
# m2p_run.sh: <tag> <repo> <platforms> <first_id> <last_id> <shot_ids> [start_override] [perf] [skip_build]
# start_override ($7) seds "@State var cleared: Int64 = 0" -> 30 (a rebuild per
# different value, so we fix it at 30 and let m2_play walk every level 30..95,
# screenshotting only the 8 representative ids in shot_ids).
RUN_RC=0
log "RUN: m2p_run.sh ${TAG}_L30  repo=$REPO platforms=ios,android 30 95 $REP_IDS 30 0"
zsh "$HARNESS/m2p_run.sh" "${TAG}_L30" "$REPO" ios,android 30 95 "$REP_IDS" 30 0 || RUN_RC=$?
log "RUN_RC=$RUN_RC"

# --- Summary ----------------------------------------------------------------
log "=== summary ==="
log "RUN_RC=$RUN_RC"
SHOT_DIRS="$(ls -d "$HOME"/orca/cjmp/m2/out/"${TAG}"* 2>/dev/null | tr '\n' ' ')"
if [ -n "$SHOT_DIRS" ]; then
  log "screenshots:"
  for d in $SHOT_DIRS; do log "  $d"; done
else
  log "screenshots: (none found under ~/orca/cjmp/m2/out/${TAG}*)"
fi

# --- Reject-flash capture: deferred (see checklist) -------------------------
# Automated reject-flash (red edge flash) capture was tried and skipped: the
# flash is transient and best captured by hand on-device. Manual checklist:
cat <<'CHECKLIST'

=== manual reject-flash / mechanism checklist (best by hand) ===
 1) One-way gate: drag AGAINST the arrow -> vermilion (朱红) edge flash.
 2) L52 / L67: after stepping on 甲, the step-count chip (if any) +2 once;
    the ferry line is dashed, never a solid diagonal.
 3) L40: one slide input fills multiple cells in a single move.
 4) Undo once -> the whole input (slide OR ferry) reverts in one step.
 5) L70 / L95: passing a gate WITHOUT the token -> rejected + edge flash;
    with the token -> gate becomes a thin line + 「开」.
 6) L90: top bar shows the 「负重」 chip.
 7) L95: after stepping on the trigger cell, broken edges render as walls.
CHECKLIST

exit "$RUN_RC"
