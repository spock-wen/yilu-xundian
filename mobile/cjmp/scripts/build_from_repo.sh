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
#   STEP C2  EntryEntryAbilityActivity system-back guard (Android)
#   STEP C3  EntryEntryAbilityActivity setenv YILU_FILES_DIR (Android, progress save dir)
#   STEP D   IPHONEOS_DEPLOYMENT_TARGET 12.0 -> 15.0 (iOS pbxproj)
#   STEP D2  iOS host UIScene lifecycle patch (TN3187): scene manifest +
#            SceneDelegate, window/root-VC moved out of AppDelegate
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
# STEP C2: Patch EntryEntryAbilityActivity — Android system back must not exit
#
# Keels 0.2.2 on Android never routes the system back to the Cangjie page
# (log: ProcessBackPressed -> AceContainerSG::OnBackPressed returns false), so
# StageActivity falls through to Activity.onBackPressed() and the app finishes
# on the FIRST back press from any screen. The page-level onBackPress in
# mobile/cjmp/lib/index.cj is therefore dead code on Android.
#
# Fix: override onBackPressed to first forward to the runtime (windowView.
# backPressed via reflection; if a future runtime routes it to the page the
# Cangjie handler comes alive by itself), and when unconsumed move the task to
# the background instead of finishing (acceptance: pressing back N times must
# not exit the app; game process and board state survive).
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
        // Keels 0.2.2: ACE never routes page onBackPress on Android; default
        // super() finishes the app on the first back press. Forward to the
        // runtime first; if unconsumed, keep the app alive in background.
        try {
            java.lang.reflect.Field f =
                ohos.stage.ability.adapter.StageActivity.class.getDeclaredField("windowView");
            f.setAccessible(true);
            Object wv = f.get(this);
            if (wv != null && (Boolean) wv.getClass().getMethod("backPressed").invoke(wv)) {
                return;
            }
        } catch (Throwable t) {
            android.util.Log.e("xundian", "backPressed forward failed", t);
        }
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
echo "  Patched: onBackPressed guard -> forward-or-background."
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
# ---------------------------------------------------------------------------
if [ "$BUILD_IOS" -eq 1 ]; then
  echo "STEP D2: Patching iOS host for UIScene lifecycle"
  if ! "$PY" "$SCRIPT_DIR/patch_ios_scene.py" patch "$PROJ/ios" --name xundian; then
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
  # and the executable must contain the SceneDelegate class.
  if ! "$PY" "$SCRIPT_DIR/patch_ios_scene.py" check-app "$IOS_APP" --name xundian; then
    echo "ERROR: iOS app bundle scene-manifest check failed" >&2
    exit 1
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
