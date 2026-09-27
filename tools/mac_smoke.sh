#!/usr/bin/env bash
# Mac HarmonyOS emulator smoke for 驿路巡点. One shot, no prompts, no sudo.
#
# Usage:
#   bash tools/mac_smoke.sh <git-ref> <hdc-serial>
#
# Isolated worktree (does not checkout or build in the repo you invoked):
#   ~/orca/yilu-xundian-smoke-<ref>     slash in ref becomes "-"
# Screenshots (hdc snapshot_display, fullscreen JPEG):
#   ~/orca/yilu-xundian-smoke-out/<ref>/<utc>/
#
# Build is hvigorw assembleHap for product=default, buildMode=debug
# (build-profile.json5). hdc is always `hdc -t <serial>`.
#
# Optional: YILU_SMOKE_ROOT overrides ~/orca (tests only).

set -euo pipefail

export GIT_TERMINAL_PROMPT=0
export GCM_INTERACTIVE=never

BUNDLE="com.yilu.xundian"
ABILITY="EntryAbility"
# build-profile.json5: products[0].name=default, buildModeSet includes debug.
HVIGOR_ARGS=(assembleHap --mode module -p product=default -p buildMode=debug --no-daemon)

RESULT="FAIL"
STEPS=()
OUT=""
REPO=""
HEAD_BEFORE=""
STATUS_BEFORE=""

usage() {
  echo "用法: bash tools/mac_smoke.sh <git-ref> <hdc-serial>" >&2
  echo "例: bash tools/mac_smoke.sh 06adc4e 127.0.0.1:5555" >&2
  echo "worktree: ~/orca/yilu-xundian-smoke-<ref>  截图: ~/orca/yilu-xundian-smoke-out/<ref>/<时间>/" >&2
}

fail() {
  echo "FAIL: $*" >&2
  RESULT="FAIL"
  exit 1
}

note() {
  echo "$*"
  STEPS+=("$*")
}

sanitize_ref() {
  local r="$1"
  r=${r//\//-}
  r=${r//:/-}
  if [[ -z "$r" || ! "$r" =~ ^[A-Za-z0-9._-]+$ ]]; then
    fail "git ref 不能作为目录名: ${1}"
  fi
  printf '%s' "$r"
}

smoke_root() {
  printf '%s' "${YILU_SMOKE_ROOT:-$HOME/orca}"
}

# Layout finder. Real uitest dumps nest text under attributes
# (_ship/verify-proof/20260916T092315Z/home-start.layout.json).
# Prints: IN x y | OUT x y | MISS
probe_layout() {
  local layout="$1"
  local needle="$2"
  python3 - "$layout" "$needle" <<'PY'
import json, sys
path, needle = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as f:
    data = json.load(f)

def attrs_of(node):
    a = node.get("attributes")
    if isinstance(a, dict):
        return a
    return node

def bounds_of(node):
    a = attrs_of(node)
    b = a.get("bounds") or a.get("bound") or ""
    if isinstance(b, str) and "][" in b:
        left, right = b.split("][")
        x1, y1 = [int(float(v)) for v in left.strip("[]").split(",")]
        x2, y2 = [int(float(v)) for v in right.strip("[]").split(",")]
        return x1, y1, x2, y2
    return None

screen_h = 0

def walk_h(node):
    global screen_h
    if isinstance(node, dict):
        b = bounds_of(node)
        if b:
            screen_h = max(screen_h, b[3])
        for ch in node.get("children") or []:
            walk_h(ch)
    elif isinstance(node, list):
        for it in node:
            walk_h(it)

walk_h(data)
if screen_h <= 0:
    screen_h = 2856

hits = []

def walk(node, bundle):
    if isinstance(node, list):
        for it in node:
            walk(it, bundle)
        return
    if not isinstance(node, dict):
        return
    a = attrs_of(node)
    bdl = a.get("bundleName") or bundle
    text = str(a.get("text") or a.get("originalText") or "")
    if needle in text and (not bdl or bdl == "com.yilu.xundian"):
        b = bounds_of(node)
        if b:
            hits.append(b)
    for ch in node.get("children") or []:
        walk(ch, bdl)

walk(data, "")
if not hits:
    print("MISS")
    sys.exit(1)
# Prefer a hit whose center sits in the visible band; else the topmost.
def center(b):
    return (b[0] + b[2]) // 2, (b[1] + b[3]) // 2

def in_band(b):
    _, cy = center(b)
    return int(screen_h * 0.05) <= cy <= int(screen_h * 0.97)

chosen = next((b for b in hits if in_band(b)), None)
flag = "IN" if chosen else "OUT"
if chosen is None:
    chosen = min(hits, key=lambda b: b[1])
x, y = center(chosen)
print(f"{flag} {x} {y}")
sys.exit(0)
PY
}

if [[ "${1:-}" == "--probe-layout" ]]; then
  [[ $# -eq 3 ]] || fail "--probe-layout 需要 <layout.json> <文案>"
  probe_layout "$2" "$3"
  exit 0
fi

IN_TRAP=0
summary() {
  [[ "$IN_TRAP" == 1 ]] && return
  IN_TRAP=1
  if [[ "${SKIP_SUMMARY:-0}" == 1 ]]; then
    return
  fi
  if [[ -n "$REPO" && -n "$HEAD_BEFORE" ]]; then
    local head_after status_after
    head_after=$(git -C "$REPO" rev-parse HEAD)
    status_after=$(git -C "$REPO" status --porcelain)
    if [[ "$head_after" != "$HEAD_BEFORE" || "$status_after" != "$STATUS_BEFORE" ]]; then
      echo "FAIL: 主检出被改动了 (HEAD 或工作区)" >&2
      RESULT="FAIL"
    fi
  fi
  echo ""
  echo "======== mac smoke ========"
  if [[ -n "$OUT" ]]; then
    echo "输出目录: $OUT"
  fi
  echo "RESULT: $RESULT"
  if [[ -n "$OUT" && -d "$OUT" ]]; then
    {
      echo "RESULT: $RESULT"
      printf '%s\n' "${STEPS[@]}"
    } >"$OUT/SUMMARY.txt" || true
  fi
  if [[ "$RESULT" != "PASS" ]]; then
    exit 1
  fi
}
trap summary EXIT

if [[ $# -ne 2 ]]; then
  usage
  SKIP_SUMMARY=1
  exit 2
fi

REF="$1"
SERIAL="$2"
[[ -n "$REF" && -n "$SERIAL" ]] || fail "git ref 和 hdc 序列号都不能空"
[[ "$SERIAL" != *" "* ]] || fail "hdc 序列号不能含空格"

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)
HEAD_BEFORE=$(git -C "$REPO" rev-parse HEAD)
STATUS_BEFORE=$(git -C "$REPO" status --porcelain)

SAFE=$(sanitize_ref "$REF")
ROOT_DIR=$(smoke_root)
WT="${ROOT_DIR}/yilu-xundian-smoke-${SAFE}"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT="${ROOT_DIR}/yilu-xundian-smoke-out/${SAFE}/${STAMP}"
mkdir -p "$OUT"

note "ref=$REF"
note "serial=$SERIAL"
note "主检出=$REPO (不在这里 checkout / 编译)"
note "worktree=$WT"
note "截图目录=$OUT"

# Tool discovery. DevEco.app on Mac is the usual install; PATH wins if set.
DEVECO_CONTENTS="${DEVECO_HOME:-/Applications/DevEco-Studio.app/Contents}"
if [[ -d "$DEVECO_CONTENTS/tools/node/bin" ]]; then
  export PATH="${DEVECO_CONTENTS}/tools/node/bin:${DEVECO_CONTENTS}/tools/ohpm/bin:${DEVECO_CONTENTS}/tools/hvigor/bin:${DEVECO_CONTENTS}/sdk/default/openharmony/toolchains:${PATH}"
fi

pick_bin() {
  local name="$1"
  shift
  if command -v "$name" >/dev/null 2>&1; then
    command -v "$name"
    return 0
  fi
  local c
  for c in "$@"; do
    if [[ -f "$c" ]]; then
      printf '%s' "$c"
      return 0
    fi
  done
  return 1
}

HDC=$(pick_bin hdc \
  "${DEVECO_CONTENTS}/sdk/default/openharmony/toolchains/hdc" \
  "${DEVECO_CONTENTS}/sdk/default/hms/toolchains/hdc") || fail "找不到 hdc。把 DevEco toolchains 放到 PATH，或安装 DevEco Studio。"
HVIGORW=$(pick_bin hvigorw \
  "${DEVECO_CONTENTS}/tools/hvigor/bin/hvigorw") || fail "找不到 hvigorw。安装 DevEco Studio，或把 hvigor/bin 放到 PATH。"
OHPM=""
if OHPM=$(pick_bin ohpm "${DEVECO_CONTENTS}/tools/ohpm/bin/ohpm"); then
  :
else
  OHPM=""
fi
command -v python3 >/dev/null 2>&1 || fail "找不到 python3（用来读 uitest 布局）"
command -v git >/dev/null 2>&1 || fail "找不到 git"

hdc_t() {
  "$HDC" -t "$SERIAL" "$@"
}

resolve_commit() {
  local c=""
  if c=$(git -C "$REPO" rev-parse --verify --end-of-options "${REF}^{commit}" 2>/dev/null); then
    printf '%s' "$c"
    return 0
  fi
  if c=$(git -C "$REPO" rev-parse --verify --end-of-options "origin/${REF}^{commit}" 2>/dev/null); then
    printf '%s' "$c"
    return 0
  fi
  return 1
}

note "git fetch origin（失败则只用本地已有对象；不改主检出工作区）"
if ! git -C "$REPO" fetch --prune origin; then
  echo "WARN: git fetch 失败，继续用本地对象" >&2
fi
COMMIT=$(resolve_commit) || fail "解析不了 git ref: $REF"
note "commit=$COMMIT"

git -C "$REPO" worktree prune
if [[ -e "$WT/.git" ]]; then
  note "更新已有 worktree"
  git -C "$WT" checkout --detach --force "$COMMIT"
  git -C "$WT" reset --hard "$COMMIT"
elif [[ -e "$WT" ]]; then
  fail "路径已存在但不是 git worktree: $WT"
else
  mkdir -p "$ROOT_DIR"
  note "git worktree add --detach"
  git -C "$REPO" worktree add --detach "$WT" "$COMMIT"
fi

# SDK path: copy the main checkout's gitignored local.properties (read-only),
# else point at the DevEco SDK. Written only inside the worktree.
if [[ ! -f "$WT/local.properties" ]]; then
  if [[ -f "$REPO/local.properties" ]]; then
    cp "$REPO/local.properties" "$WT/local.properties"
    note "已把主检出的 local.properties 复制进 worktree（未改主检出）"
  else
    SDK_DIR=""
    if [[ -n "${DEVECO_SDK_HOME:-}" && -d "$DEVECO_SDK_HOME" ]]; then
      SDK_DIR="$DEVECO_SDK_HOME"
    elif [[ -d "${DEVECO_CONTENTS}/sdk" ]]; then
      SDK_DIR="${DEVECO_CONTENTS}/sdk"
    fi
    [[ -n "$SDK_DIR" ]] || fail "worktree 没有 local.properties，也找不到 DevEco SDK。在主检出配好 local.properties，或设置 DEVECO_SDK_HOME。"
    {
      printf 'sdk.dir=%s\n' "$SDK_DIR"
      if [[ -d "${DEVECO_CONTENTS}/tools/node" ]]; then
        printf 'nodejs.dir=%s\n' "${DEVECO_CONTENTS}/tools/node"
      fi
    } >"$WT/local.properties"
    note "已在 worktree 写入 local.properties sdk.dir=$SDK_DIR"
  fi
fi
if [[ -f "$WT/local.properties" ]]; then
  SDK_LINE=$(grep -E '^sdk\.dir=' "$WT/local.properties" | head -1 || true)
  if [[ -n "$SDK_LINE" ]]; then
    export OHOS_BASE_SDK_HOME="${SDK_LINE#sdk.dir=}"
  fi
fi

note "编译: ${HVIGORW} ${HVIGOR_ARGS[*]}"
{
  echo "# $(date -u +%Y-%m-%dT%H:%M:%SZ) commit=$COMMIT"
  if [[ -n "$OHPM" ]]; then
    echo "# ohpm install --all"
    (cd "$WT" && "$OHPM" install --all)
  else
    echo "# ohpm 不在 PATH，跳过 install（依赖由 DevEco 插件提供）"
  fi
  echo "# hvigorw ${HVIGOR_ARGS[*]}"
  if [[ -x "$HVIGORW" ]]; then
    (cd "$WT" && "$HVIGORW" "${HVIGOR_ARGS[@]}")
  else
    (cd "$WT" && bash "$HVIGORW" "${HVIGOR_ARGS[@]}")
  fi
} >"$OUT/build.log" 2>&1 || {
  echo "---- build.log 末尾 ----" >&2
  tail -n 40 "$OUT/build.log" >&2 || true
  fail "HAP 编译失败，日志 $OUT/build.log"
}
note "编译结束，日志 $OUT/build.log"

HAP=""
while IFS= read -r f; do
  case "$f" in
    *unsigned*) ;;
    *) HAP="$f"; break ;;
  esac
done < <(find "$WT/entry/build" -type f -name '*.hap' | sort)
if [[ -z "$HAP" ]]; then
  HAP=$(find "$WT/entry/build" -type f -name '*.hap' | head -1 || true)
fi
[[ -n "$HAP" && -f "$HAP" ]] || fail "编译结束但没有找到 .hap"
note "hap=$HAP"

TARGETS=$("$HDC" list targets 2>&1 || true)
echo "$TARGETS" | grep -F -q -- "$SERIAL" || fail "hdc list targets 里没有 $SERIAL。当前: ${TARGETS}"
note "目标在 hdc list targets 中"

if ! hdc_t install -r "$HAP"; then
  hdc_t uninstall "$BUNDLE" || true
  hdc_t install -r "$HAP" || fail "hdc install 失败"
fi
note "已安装 $BUNDLE"

dump_layout() {
  local dest="$1"
  local remote="/data/local/tmp/yilu_mac_smoke_${SAFE}_layout.json"
  hdc_t shell uitest dumpLayout -p "$remote" >/dev/null || return 1
  hdc_t file recv "$remote" "$dest" >/dev/null || return 1
  [[ -s "$dest" ]] || return 1
}

shot() {
  local label="$1"
  local remote="/data/local/tmp/yilu_mac_smoke_${SAFE}_${label}.jpeg"
  local dest="${OUT}/${label}.jpeg"
  hdc_t shell snapshot_display -f "$remote"
  hdc_t file recv "$remote" "$dest"
  [[ -s "$dest" ]] || fail "截图缺失: $label"
  local sz
  sz=$(wc -c <"$dest" | tr -d ' ')
  # Fullscreen JPEG is far larger than an empty or error file.
  [[ "$sz" -ge 10000 ]] || fail "截图过小 (${sz} 字节)，不像全屏 snapshot_display: $dest"
  local magic
  magic=$(od -An -t x1 -N 2 "$dest" | tr -d ' \n')
  [[ "$magic" == "ffd8" ]] || fail "截图不是 JPEG (magic=$magic): $dest"
  note "截图 ${label}.jpeg ${sz} 字节"
}

wait_probe() {
  local needle="$1"
  local layout="$2"
  local i line
  for i in 1 2 3 4 5 6 7 8; do
    dump_layout "$layout" || true
    if [[ -s "$layout" ]]; then
      line=$(probe_layout "$layout" "$needle" || true)
      if [[ "$line" == IN* || "$line" == OUT* ]]; then
        printf '%s' "$line"
        return 0
      fi
    fi
    sleep 0.5
  done
  return 1
}

tap_text() {
  local needle="$1"
  local layout="${OUT}/layout-tap-${needle}.json"
  local line
  line=$(wait_probe "$needle" "$layout") || fail "界面上找不到「${needle}」"
  [[ "$line" == IN* ]] || fail "「${needle}」不在可见区域: $line"
  local x y
  x=$(echo "$line" | awk '{print $2}')
  y=$(echo "$line" | awk '{print $3}')
  note "点击「${needle}」 ($x,$y)"
  hdc_t shell uitest uiInput click "$x" "$y"
  sleep 0.8
}

launch_app() {
  hdc_t shell aa force-stop "$BUNDLE" || true
  sleep 0.4
  hdc_t shell aa start -a "$ABILITY" -b "$BUNDLE" || fail "aa start 失败"
  sleep 1.2
}

require_text() {
  local needle="$1"
  local layout="$2"
  local line
  line=$(wait_probe "$needle" "$layout") || fail "未看到「${needle}」"
  [[ "$line" == IN* ]] || fail "「${needle}」不在可见区域: ${line}"
  note "见到「${needle}」 ($line)"
}

scroll_until_visible() {
  local needle="$1"
  local layout="${OUT}/layout-scroll.json"
  local i line x y cy
  for i in $(seq 1 40); do
    dump_layout "$layout"
    line=$(probe_layout "$layout" "$needle" || true)
    if [[ "$line" == IN* ]]; then
      printf '%s' "$line"
      return 0
    fi
    # Swipe along the middle of the dumped root. Row below the fold: finger moves up.
    read -r sx1 sy1 sx2 sy2 < <(python3 - "$layout" "$line" <<'PY'
import json, sys
path, line = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as f:
    data = json.load(f)
h = 0
w = 0
def bounds(node):
    a = node.get("attributes") if isinstance(node.get("attributes"), dict) else node
    b = a.get("bounds") or ""
    if isinstance(b, str) and "][" in b:
        left, right = b.split("][")
        x1, y1 = [int(float(v)) for v in left.strip("[]").split(",")]
        x2, y2 = [int(float(v)) for v in right.strip("[]").split(",")]
        return x1, y1, x2, y2
    return None
def walk(node):
    global h, w
    if isinstance(node, dict):
        b = bounds(node)
        if b:
            w = max(w, b[2])
            h = max(h, b[3])
        for ch in node.get("children") or []:
            walk(ch)
    elif isinstance(node, list):
        for it in node:
            walk(it)
walk(data)
if w <= 0:
    w = 1080
if h <= 0:
    h = 2400
x = w // 2
parts = line.split()
cy = int(parts[2]) if len(parts) >= 3 and parts[0] == "OUT" else h
if cy > int(h * 0.85):
    print(x, int(h * 0.75), x, int(h * 0.30))
else:
    print(x, int(h * 0.30), x, int(h * 0.75))
PY
)
    hdc_t shell uitest uiInput swipe "$sx1" "$sy1" "$sx2" "$sy2" 2000 \
      || hdc_t shell uitest uiInput swipe "$sx1" "$sy1" "$sx2" "$sy2"
    sleep 0.45
  done
  return 1
}

# Defined points. Fresh process each time: cleared is in-memory and starts at 0.
# 修缮中 is painted even before those levels unlock (maintenance branch is first).
note "节点 01-home"
launch_app
require_text "开始传书" "${OUT}/layout-01-home.json"
shot "01-home"

note "节点 02-board（开始传书 → 涿郡·涿）"
tap_text "开始传书"
require_text "撤销" "${OUT}/layout-02-board.json"
shot "02-board"

note "节点 03-chapters"
launch_app
tap_text "章节"
require_text "选章入驿" "${OUT}/layout-03-chapters.json"
shot "03-chapters"

note "节点 04-yicheng"
launch_app
tap_text "驿程"
require_text "涿郡·涿" "${OUT}/layout-04-yicheng.json"
shot "04-yicheng"

note "节点 05-maintenance（驿程滚到可见的「修缮中」）"
scroll_line=$(scroll_until_visible "修缮中") || fail "驿程里滚不到可见的「修缮中」"
note "修缮中可见 ($scroll_line)"
require_text "樊城" "${OUT}/layout-05-maintenance-name.json"
shot "05-maintenance"

RESULT="PASS"
exit 0
