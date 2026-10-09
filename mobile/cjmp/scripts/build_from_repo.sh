#!/bin/bash
# build_from_repo.sh — ONE documented command to build CJMP (Keels 0.2.2) for iOS and/or Android.
#
# Usage:
#   mobile/cjmp/scripts/build_from_repo.sh [--out DIR] [--android] [--ios] [--pending-sans-ok] [--auto-venv]
#
# Options:
#   --out DIR          Output directory for the Keels project (default: <repo>/mobile/cjmp/.host)
#   --android          Build Android APK only
#   --ios              Build iOS simulator bundle only
#   (neither flag)     Build both platforms
#   --pending-sans-ok  Tolerate missing YiluSans-* files (exit 3 from check_fonts.py is non-fatal;
#                      build is NOT release-valid)
#   --auto-venv        Automatically create a venv at mobile/cjmp/.venv and install fontTools
#
# Prerequisites:
#   • Source the CJMP OpenSDK 0.2.2 environment script before running this script.
#     The env script sets CJMP_SDK_HOME and adds `keels` to PATH.
#     Example:  source ~/orca/cjmp/env.sh   (path varies; document your local path)
#   • python3 on PATH
#   • Xcode (for --ios)
#   • Android SDK + NDK 26.3.11579264 (for --android)
#
# Package identity:
#   Android applicationId / namespace : com.yilu.xundian
#   iOS bundle identifier             : com.yilu.xundian
#   (final IDs to be confirmed before App Store / Google Play release)
#
# Template patches applied automatically:
#   STEP C   xundian.cpp FindClass com/example -> com/yilu (Android)
#   STEP C2  EntryEntryAbilityActivity system-back guard (Android; forwards to
#            the page onBackPress, else moveTaskToBack; logs `adb logcat -s xundian`)
#   STEP C3  EntryEntryAbilityActivity setenv YILU_FILES_DIR (Android, progress save dir)
#   STEP C4  EntryEntryAbilityActivity system bar colors (Android, paper palette;
#            default OFF — zero visual effect on the API35 cutout-inset emulator,
#            run only with an explicit YILU_ANDROID_BARS=on)
#   STEP D   IPHONEOS_DEPLOYMENT_TARGET 12.0 -> 15.0 (iOS pbxproj)
#   STEP D2  iOS host UIScene lifecycle patch (TN3187): scene manifest +
#            SceneDelegate, window/root-VC moved out of AppDelegate,
#            and iOS bars mode (YILU_IOS_BARS)
#   STEP G   post-build check-app verification of the built .app (iOS)
#
# macOS bash 3.2 compatible (no associative arrays, no mapfile).
set -euo pipefail

# ---------------------------------------------------------------------------
# Helper: resolve the repo root from this script's location
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/../../entry" ]; then
  REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"
else
  REPO="$(cd "$SCRIPT_DIR/../../.." && pwd)"
fi

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
OUT_DIR=""
BUILD_ANDROID=0
BUILD_IOS=0
PENDING_SANS_OK=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --out)
      OUT_DIR="$2"
      shift 2
      ;;
    --android)
      BUILD_ANDROID=1
      shift
      ;;
    --ios)
      BUILD_IOS=1
      shift
      ;;
    --pending-sans-ok)
      PENDING_SANS_OK=1
      shift
      ;;
    --auto-venv)
      AUTO_VENV=1
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: $0 [--out DIR] [--android] [--ios] [--pending-sans-ok] [--auto-venv]" >&2
      exit 1
      ;;
  esac
done

# Default: both platforms
if [ "$BUILD_ANDROID" -eq 0 ] && [ "$BUILD_IOS" -eq 0 ]; then
  BUILD_ANDROID=1
  BUILD_IOS=1
fi

# Default output dir
if [ -z "$OUT_DIR" ]; then
  OUT_DIR="$REPO/mobile/cjmp/.host"
fi
mkdir -p "$OUT_DIR"
PROJ="$OUT_DIR/xundian"

PENDING_BANNER=0

# ---------------------------------------------------------------------------
# 校验系统栏相关环境变量（iOS 白带处理模式 / Android 系统栏配色开关）
#   YILU_IOS_BARS     hide（默认，隐藏导航栏，染纸色 #F3E8D6、强制浅色；配合仓颉 safe-top/bottom）
#                    | paper（保留导航栏但整体染纸色 #F3E8D6、去细线）| off（不处理）
#   YILU_ANDROID_BARS off（默认，跳过——Mac 实测 API35 挖孔 inset 下零效果）
#                    | on（系统栏设为 paper 并用浅色图标）
# ---------------------------------------------------------------------------
case "${YILU_IOS_BARS:-hide}" in
  hide|paper|off) ;;
  *)
    echo "ERROR: YILU_IOS_BARS must be one of hide|paper|off (got: ${YILU_IOS_BARS})" >&2
    exit 1
    ;;
esac

case "${YILU_ANDROID_BARS:-off}" in
  on|off) ;;
  *)
    echo "ERROR: YILU_ANDROID_BARS must be one of on|off (got: ${YILU_ANDROID_BARS})" >&2
    exit 1
    ;;
esac

# ---------------------------------------------------------------------------
# STEP A: Check prerequisites
# ---------------------------------------------------------------------------
echo "STEP A: Checking prerequisites"

if ! command -v keels >/dev/null 2>&1; then
  echo "ERROR: 'keels' not found on PATH." >&2
  echo "  Source the CJMP OpenSDK 0.2.2 environment script first." >&2
  echo "  Example: source ~/orca/cjmp/env.sh  (path varies by machine)" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: 'python3' not found on PATH." >&2
  exit 1
fi

PY="${YILU_PY:-python3}"
if "$PY" -c 'import fontTools' >/dev/null 2>&1; then
  echo "fontTools OK ($("$PY" -c 'import fontTools;print(fontTools.version)'))"
else
  if [ "${AUTO_VENV:-0}" -eq 1 ]; then
    if [ ! -d "$REPO/mobile/cjmp/.venv" ]; then
      python3 -m venv "$REPO/mobile/cjmp/.venv"
    fi
    "$REPO/mobile/cjmp/.venv/bin/python" -m pip install --quiet fonttools
    PY="$REPO/mobile/cjmp/.venv/bin/python"
    if ! "$PY" -c 'import fontTools' >/dev/null 2>&1; then
      echo "ERROR: Python module 'fontTools' not found for $PY after auto-venv installation." >&2
      exit 1
    fi
    echo "fontTools OK ($("$PY" -c 'import fontTools;print(fontTools.version)'))"
  else
    echo "ERROR: Python module 'fontTools' not found for $PY." >&2
    echo "  Install:  python3 -m pip install fonttools" >&2
    echo "  or rerun with --auto-venv (creates mobile/cjmp/.venv and installs fonttools there)" >&2
    echo "  or point YILU_PY at an interpreter that has it (e.g. YILU_PY=~/ftvenv/bin/python)." >&2
    exit 1
  fi
fi

keels --version

# ---------------------------------------------------------------------------
# STEP B: Create Keels project
# ---------------------------------------------------------------------------
echo "STEP B: Creating Keels project at $PROJ"
rm -rf "$PROJ"
keels create -n xundian --org com.yilu "$PROJ"
echo "  Project created."

# ---------------------------------------------------------------------------
# STEP C: Patch xundian.cpp — fix hardcoded FindClass org
# ---------------------------------------------------------------------------
echo "STEP C: Patching xundian.cpp (Keels template FindClass bug)"

CPP="$PROJ/android/app/src/main/cpp/xundian.cpp"
if [ ! -f "$CPP" ]; then
  echo "ERROR: $CPP not found — unexpected project layout" >&2
  exit 1
fi

OLD_CLASS="com/example/xundian/xundian"
NEW_CLASS="com/yilu/xundian/xundian"

if ! grep -q "$OLD_CLASS" "$CPP"; then
  echo "  WARNING: old class string not found — already patched or template changed"
else
  sed -i '' "s|${OLD_CLASS}|${NEW_CLASS}|g" "$CPP"
  echo "  Patched: $OLD_CLASS -> $NEW_CLASS"
fi

# Verify
if grep -q "$OLD_CLASS" "$CPP"; then
  echo "ERROR: old class string still present after patch: $OLD_CLASS" >&2
  exit 1
fi
if ! grep -q "$NEW_CLASS" "$CPP"; then
  echo "ERROR: new class string not found after patch: $NEW_CLASS" >&2
  exit 1
fi
echo "  Patch verified."

# ---------------------------------------------------------------------------
# STEP C2: Patch EntryEntryAbilityActivity — Android 系统 Back 守卫
#
# 真实链路（Keels 0.2.2 Android：页面级 onBackPress 是**被路由的**，不是死代码）：
#   StageActivity.onBackPressed() = if (!windowView.backPressed()) super.onBackPressed()
#     （javap 反编译 keels_android_adapter.jar 证实）
#   WindowView.backPressed() -> nativeBackPressed -> ACE PipelineContext::OnBackPressed
#   -> CJFrontend -> CJPageRouterNG::PopWithExitCheck -> PagePattern::OnBackPressed
#   -> NativeView::FireOnBackPress -> 仓颉 @Entry 的 onBackPress()
#     （即 mobile/cjmp/lib/index.cj:389 的 override，见文件内 screen 分发）
#   源码（相对 Keels 仓根，仓库内可检索，不依赖任何盒子本地路径）：
#     ace_engine/frameworks/bridge/cj_frontend/frontend/cj_page_router_ng.cpp
#       的 PopWithExitCheck / SetOnBackPressed
#     ace_engine/frameworks/bridge/cj_frontend/cppview/native_view.cpp
#       的 FireOnBackPress / RemoteView::OnBackPress
#
# 实测日志（2026-10-04 abf56b0 轮，Android API35 logcat）：
#   WindowView backPressed called
#   -> router consumed backpressed event
#   -> AceContainerSG return true
# 同轮 backkey 用例：棋盘/通关页 Back→首页，首页 Back→回桌面且 pid 不变。
#
# 已废弃的错误结论（勿再引用）：10-02 的 0310ebf 轮没有原始 logcat 存档，只有
# BACK_TEST.txt 文字，其中报告过一次「ProcessBackPressed:
# AceContainerSG::OnBackPressed return false → 一次即退」，当时据此写下
# 「Keels 0.2.2 never routes … dead code」。该结论与上面的源码链路、实测日志
# 均矛盾：页面级 onBackPress 在 Android 上是活的。但那一次 return false 的
# 具体原因未查明（当轮未存原始 logcat，无法复核），此处不再猜测其成因；
# 守卫保证即使再出现页面未消费，也只会转后台（进程与棋局保留）而不会
# finish。测试可用 adb logcat -s xundian 的 `back: page consumed=` 行直接判读。
#
# 守卫的作用：先把系统 Back 转发给运行时（windowView.backPressed()），页面
# 消费了就 return；未消费时（按 index.cj onBackPress，仅首页 screen==0 返回
# false）走 moveTaskToBack(true) 而不是 finish —— 等同 Android 12+ 对根任务
# Activity 的系统默认 Back 行为，且在 API 26-30 上避免被 super.onBackPressed()
# finish 掉进程。应用 targetSdk 34 且未开 enableOnBackInvokedCallback，
# onBackPressed 在所有系统版本都会被调用。
#
# 可诊断日志（注入的方法会打 android.util.Log.i，tag = "xundian"）：
#   adb logcat -s xundian
#     back: page consumed=true            页面已消费（棋盘/通关页 → 首页）
#     back: page consumed=false           首页未消费
#     back: unconsumed -> moveTaskToBack  转入后台，进程与棋局保留
# 异常串 "backPressed forward failed" 同时是本 STEP 的幂等标记（grep -q 依赖
# 它），勿改。
# ---------------------------------------------------------------------------
echo "STEP C2: Patching EntryEntryAbilityActivity (Android system back guard)"

ACT="$PROJ/android/app/src/main/java/com/yilu/xundian/EntryEntryAbilityActivity.java"
if [ ! -f "$ACT" ]; then
  echo "ERROR: $ACT not found — unexpected project layout" >&2
  exit 1
fi

if grep -q "backPressed forward failed" "$ACT"; then
  echo "  WARNING: back guard already present — skipping"
else
  if ! "$PY" - "$ACT" <<'PYEOF'
import sys

path = sys.argv[1]
src = open(path, encoding="utf-8").read()
method = '''
    @Override
    public void onBackPressed() {
        // Keels 0.2.2 会把系统 Back 路由到仓颉页面（StageActivity.onBackPressed
        // -> windowView.backPressed() -> ACE PipelineContext ->
        // CJPageRouterNG::PopWithExitCheck -> @Entry 的 onBackPress）。
        // 页面消费则到此为止；未消费（仅首页 screen==0）时转入后台而不是
        // finish，进程与棋局保留。
        boolean consumed = false;
        try {
            java.lang.reflect.Field f =
                ohos.stage.ability.adapter.StageActivity.class.getDeclaredField("windowView");
            f.setAccessible(true);
            Object wv = f.get(this);
            if (wv != null) {
                consumed = (Boolean) wv.getClass().getMethod("backPressed").invoke(wv);
            }
        } catch (Throwable t) {
            android.util.Log.e("xundian", "backPressed forward failed", t);
        }
        android.util.Log.i("xundian", "back: page consumed=" + consumed);
        if (consumed) {
            return;
        }
        android.util.Log.i("xundian", "back: unconsumed -> moveTaskToBack");
        moveTaskToBack(true);
    }
'''
needle = "        setInstanceName(\"com.yilu.xundian:entry:EntryAbility:\");\n        super.onCreate(savedInstanceState);\n    }\n"
if src.count(needle) != 1:
    sys.exit(1)
src = src.replace(needle, needle + method, 1)
open(path, "w", encoding="utf-8").write(src)
PYEOF
then
  echo "ERROR: back guard patch anchor not found in $ACT" >&2
  exit 1
fi
if ! grep -q "backPressed forward failed" "$ACT"; then
  echo "ERROR: back guard not present after patch" >&2
  exit 1
fi
echo "  Patched: onBackPressed guard -> forward-or-background (log tag: xundian)."
fi

# ---------------------------------------------------------------------------
# STEP C3: Patch EntryEntryAbilityActivity — export YILU_FILES_DIR (progress)
#
# Keels 0.2.2 has no Cangjie API to get the Android filesDir, so progress
# save/load has no writable directory on Android. The host-side patch sets
# YILU_FILES_DIR to the activity's filesDir before the runtime starts; the
# Cangjie side (mobile/cjmp/lib/progress_io.cj makeProgressBackend) reads it
# via std.env.getVariable and falls back to NullProgressBackend when absent.
# ---------------------------------------------------------------------------
echo "STEP C3: Patching EntryEntryAbilityActivity (YILU_FILES_DIR for progress save)"
if ! "$PY" "$SCRIPT_DIR/patch_android_filesdir.py" patch "$ACT"; then
  echo "ERROR: patch_android_filesdir.py patch failed (Keels template changed?)" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# STEP C4: Patch EntryEntryAbilityActivity — Android 系统栏配色（paper 色板）
#
# Keels 0.2.2 生成的 Android 宿主未设置系统栏颜色，状态栏(约 48.8dp)与
# 导航栏(约 24dp)默认为黑色，与纸色(#F3E8D6)棋盘不协调。patch_android_bars.py
# 在 onPostCreate 中把两个系统栏颜色设为 paper 并改用浅色前景图标。
#
# Mac 实测（API35 模拟器，A411 挖孔）：dumpsys 证实补丁 flags 生效
# （LIGHT_STATUS_BAR/NAVIGATION_BAR），但黑块 128px 在应用窗口之外
# （mDisplayCutout insets top=128 > statusBars 63px，窗口被放在挖孔之下），
# setStatusBarColor 画不到那里——零视觉变化。故默认跳过（skipping (default
# off)），仅当显式 YILU_ANDROID_BARS=on 时执行（真机/无挖孔设备可复测）；
# 真正消除黑块需 edge-to-edge + cutout 方案（方案 B，另议）。
# ---------------------------------------------------------------------------
echo "STEP C4: Patching EntryEntryAbilityActivity (system bar colors)"
if [ "${YILU_ANDROID_BARS:-off}" = "on" ]; then
  if ! "$PY" "$SCRIPT_DIR/patch_android_bars.py" patch "$ACT"; then
    echo "ERROR: patch_android_bars.py patch failed (Keels template changed?)" >&2
    exit 1
  fi
else
  echo "  YILU_ANDROID_BARS=${YILU_ANDROID_BARS:-off} — skipping (default off)"
fi

# ---------------------------------------------------------------------------
# STEP D: Patch project.pbxproj — set IPHONEOS_DEPLOYMENT_TARGET = 15.0
# ---------------------------------------------------------------------------
echo "STEP D: Patching IPHONEOS_DEPLOYMENT_TARGET in project.pbxproj"

PBXPROJ="$PROJ/ios/xundian.xcodeproj/project.pbxproj"
if [ ! -f "$PBXPROJ" ]; then
  echo "ERROR: $PBXPROJ not found — unexpected project layout" >&2
  exit 1
fi

# Replace any value: IPHONEOS_DEPLOYMENT_TARGET = <anything>;
sed -i '' 's/IPHONEOS_DEPLOYMENT_TARGET = [^;]*;/IPHONEOS_DEPLOYMENT_TARGET = 15.0;/g' "$PBXPROJ"

# Verify at least 1 occurrence exists with the correct value
count_correct=$(grep -c "IPHONEOS_DEPLOYMENT_TARGET = 15.0;" "$PBXPROJ" || true)

if [ "$count_correct" -lt 1 ]; then
  echo "ERROR: IPHONEOS_DEPLOYMENT_TARGET = 15.0 not found after patch" >&2
  exit 1
fi

# Check no other values remain (grep's exit code is fine to ignore here — presence is what matters)
bad_count=0
if grep "IPHONEOS_DEPLOYMENT_TARGET = " "$PBXPROJ" | grep -qv "IPHONEOS_DEPLOYMENT_TARGET = 15.0;"; then
  bad_count=$(grep "IPHONEOS_DEPLOYMENT_TARGET = " "$PBXPROJ" | grep -cv "IPHONEOS_DEPLOYMENT_TARGET = 15.0;" || true)
fi
if [ "$bad_count" -gt 0 ]; then
  echo "ERROR: non-15.0 IPHONEOS_DEPLOYMENT_TARGET still present ($bad_count lines)" >&2
  exit 1
fi

echo "  Patched $count_correct occurrence(s) to 15.0."

# ---------------------------------------------------------------------------
# STEP D2: Patch iOS host for UIScene lifecycle (TN3187)
#
# Apps built with the iOS 27 SDK must use the UIScene lifecycle; the Keels
# template creates its window in AppDelegate and ships no
# UIApplicationSceneManifest, so the app would crash at launch on iOS 27.
# patch_ios_scene.py adds the manifest, a SceneDelegate, moves window/root-VC
# creation into the scene delegate (StageApplication init stays in
# AppDelegate) and registers the new files in the xcodeproj.
#
# --bars comes from YILU_IOS_BARS (default hide: nav bar hidden with
# YiluNavigationController, status bar darkContent, paper #F3E8D6 backgrounds,
# safeAreaInsets exported via YILU_SAFE_TOP/BOTTOM; paper = nav bar kept but
# repainted opaque paper with no shadow hairline; off = the template white band).
# ---------------------------------------------------------------------------
if [ "$BUILD_IOS" -eq 1 ]; then
  echo "STEP D2: Patching iOS host for UIScene lifecycle"
  if ! "$PY" "$SCRIPT_DIR/patch_ios_scene.py" patch "$PROJ/ios" --name xundian --bars "${YILU_IOS_BARS:-hide}"; then
    echo "ERROR: patch_ios_scene.py patch failed (Keels template changed?)" >&2
    exit 1
  fi
fi

# ---------------------------------------------------------------------------
# STEP E: Sync source, engine, levels and assets
# ---------------------------------------------------------------------------
echo "STEP E: Syncing source and assets"
"$SCRIPT_DIR/sync_to_keels.sh" "$PROJ"

# ---------------------------------------------------------------------------
# STEP F: Run checks
# ---------------------------------------------------------------------------
echo "STEP F: Running check_level.py"
"$PY" "$REPO/mobile/scripts/check_level.py"

echo "STEP F: Running check_fonts.py"
if [ "$PENDING_SANS_OK" -eq 1 ]; then
  echo "--pending-sans-ok ignored: sans fonts are delivered"
fi
"$PY" "$SCRIPT_DIR/check_fonts.py"

echo "STEP F: Running check_glyphs.py"
tmp=$(mktemp -d)
mkdir -p "$tmp/mobile/cjmp"
cp -R "$REPO/mobile/cjmp/lib" "$tmp/mobile/cjmp/"
cp -R "$REPO/mobile/shared" "$tmp/mobile/"
set +e
out=$("$PY" "$SCRIPT_DIR/check_glyphs.py" "$tmp/mobile" --fonts-dir "$REPO/mobile/cjmp/fonts" --chars "$REPO/mobile/cjmp/fonts/yilu_sans_chars.txt" --strict-family 2>&1)
rc=$?
set -e
echo "check_glyphs scan root: repo mobile/cjmp/lib + mobile/shared (staged, excludes .host)"
echo "$out"
echo "check_glyphs exit=$rc"
rm -rf "$tmp"
if [ "$rc" -ne 0 ]; then
  exit 1
fi


# ---------------------------------------------------------------------------
# STEP G: Build
# ---------------------------------------------------------------------------
ANDROID_APK=""
IOS_APP=""

if [ "$BUILD_ANDROID" -eq 1 ]; then
  echo "STEP G: Building Android APK"
  (cd "$PROJ" && keels build apk)
  ANDROID_APK="$PROJ/android/app/build/outputs/apk/debug/app-debug.apk"
  if [ ! -f "$ANDROID_APK" ]; then
    echo "ERROR: expected APK not found at $ANDROID_APK" >&2
    exit 1
  fi
  echo "  APK: $ANDROID_APK"
  shasum -a 256 "$ANDROID_APK"

  # Print bundle ID
  if command -v apkanalyzer >/dev/null 2>&1; then
    echo "  Android bundle ID: $(apkanalyzer manifest application-id "$ANDROID_APK")"
  elif command -v aapt >/dev/null 2>&1; then
    echo "  Android bundle ID: $(aapt dump badging "$ANDROID_APK" | grep "package: name=" | sed "s/.*name='//;s/'.*//") "
  else
    GRADLE="$PROJ/android/app/build.gradle"
    if [ -f "$GRADLE" ]; then
      echo "  Android bundle ID (from build.gradle): $(grep applicationId "$GRADLE" | head -1 | sed 's/.*applicationId[[:space:]]*//;s/[[:space:]]//g;s/"//g')"
    fi
  fi
fi

if [ "$BUILD_IOS" -eq 1 ]; then
  echo "STEP G: Building iOS simulator"
  (cd "$PROJ" && keels build ios-sim)
  IOS_APP="$PROJ/ios/output/DerivedData/Build/Products/Debug-iphonesimulator/xundian.app"
  if [ ! -d "$IOS_APP" ]; then
    echo "ERROR: expected iOS app bundle not found at $IOS_APP" >&2
    exit 1
  fi
  # Post-build check: the .app Info.plist must carry the UIScene manifest
  # and the executable must contain the SceneDelegate class (and YiluNavigationController when hide).
  if [ "${YILU_IOS_BARS:-hide}" = "hide" ]; then
    if ! "$PY" "$SCRIPT_DIR/patch_ios_scene.py" check-app "$IOS_APP" --name xundian --expect-hide; then
      echo "ERROR: iOS app bundle scene-manifest check failed" >&2
      exit 1
    fi
  else
    if ! "$PY" "$SCRIPT_DIR/patch_ios_scene.py" check-app "$IOS_APP" --name xundian; then
      echo "ERROR: iOS app bundle scene-manifest check failed" >&2
      exit 1
    fi
  fi
  echo "  iOS app: $IOS_APP"
  # Print size summary (no shasum on directories — use zip hash)
  shasum -a 256 "$IOS_APP/xundian" 2>/dev/null || true

  # Print bundle ID
  PLIST="$IOS_APP/Info.plist"
  if [ -f "$PLIST" ]; then
    BID=$(/usr/libexec/PlistBuddy -c 'Print CFBundleIdentifier' "$PLIST" 2>/dev/null || echo "unknown")
    echo "  iOS bundle ID: $BID"
  fi
fi

# ---------------------------------------------------------------------------
# STEP H: Final summary
# ---------------------------------------------------------------------------
echo "BUILD_FROM_REPO OK"
