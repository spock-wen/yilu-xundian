#!/bin/bash
# Build the OHOS-free Zip staticlib and the iOS Simulator app.
# Host must be macOS aarch64 with Xcode and cangjie-sdk-mac-aarch64-ios.
# Flags follow:
# https://cj-docs.gitcode.com/zh/1.1.3/dev-guide/source_zh_cn/compile_and_build/cross_compilation.html
# cjpm --target:
# https://docs.cangjie-lang.cn/cjnative/user_manual/tools/source_zh_cn/tools/cjpm_manual_cjnative_community.html

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$ROOT/../.." && pwd)"
SHARED="$REPO/engine/shared"
APP="$ROOT/app"

if [ "$(uname -s)" != "Darwin" ]; then
  echo "SMOKE BLOCKED: build_simulator.sh must run on macOS with Xcode."
  echo "This host is $(uname -s) $(uname -m)."
  echo "A later xcodebuild on a Mac is still not a smoke pass."
  exit 1
fi

if [ -z "${CANGJIE_HOME:-}" ]; then
  echo "CANGJIE_HOME is unset."
  echo "Extract cangjie-sdk-mac-aarch64-ios-1.1.3.tar.gz and point CANGJIE_HOME at the directory that contains envsetup.sh."
  echo "Download: https://cangjie-lang.cn/download/1.1.3"
  exit 1
fi

case "$CANGJIE_HOME" in
  *" "*)
    echo "CANGJIE_HOME must not contain spaces (xcconfig cannot quote it): $CANGJIE_HOME"
    exit 1
    ;;
esac

if [ -f "$CANGJIE_HOME/envsetup.sh" ]; then
  set +u
  # shellcheck disable=SC1091
  . "$CANGJIE_HOME/envsetup.sh"
  set -u
fi

command -v cjpm >/dev/null 2>&1 || {
  echo "cjpm is not on PATH. Source \$CANGJIE_HOME/envsetup.sh from the iOS SDK."
  exit 1
}
command -v cjc >/dev/null 2>&1 || {
  echo "cjc is not on PATH. Source \$CANGJIE_HOME/envsetup.sh from the iOS SDK."
  exit 1
}
command -v xcodebuild >/dev/null 2>&1 || {
  echo "xcodebuild is not on PATH. Install Xcode.app and its iOS platform."
  exit 1
}
command -v xcrun >/dev/null 2>&1 || {
  echo "xcrun is not on PATH."
  exit 1
}
if [ ! -x /usr/bin/libtool ]; then
  echo "Missing /usr/bin/libtool (Xcode)."
  exit 1
fi

# Simulator bullet on the cross-compile page has no SDK-version suffix.
# Device example on that page is: --target=aarch64-apple-ios17.5
# Override with YILU_IOS_TARGET if cjc rejects the default triple.
TARGET="${YILU_IOS_TARGET:-aarch64-apple-ios-simulator}"

# Pick an arm64 iPhone simulator. generic/platform=iOS Simulator also
# builds the x86_64 slice; the Cangjie simulator libs are arm64-only, so
# that slice fails with Undefined symbols for _yilu_* (Mac 2026-09-26).
pick_iphone_udid() {
  if [ -n "${YILU_SIM_UDID:-}" ]; then
    printf '%s\n' "$YILU_SIM_UDID"
    return
  fi
  list="$(xcrun simctl list devices available)"
  booted=""
  any=""
  while IFS= read -r line; do
    case "$line" in
      *iPhone*) ;;
      *) continue ;;
    esac
    udid="$(printf '%s\n' "$line" | sed -n 's/.*(\([0-9A-Fa-f]\{8\}-[0-9A-Fa-f]\{4\}-[0-9A-Fa-f]\{4\}-[0-9A-Fa-f]\{4\}-[0-9A-Fa-f]\{12\}\)).*/\1/p')"
    if [ -z "$udid" ]; then
      continue
    fi
    if [ -z "$any" ]; then
      any="$udid"
    fi
    case "$line" in
      *"(Booted)"*)
        booted="$udid"
        break
        ;;
    esac
  done <<EOF
$list
EOF
  if [ -n "$booted" ]; then
    printf '%s\n' "$booted"
  elif [ -n "$any" ]; then
    printf '%s\n' "$any"
  else
    echo "No available iPhone simulator."
    echo "Install an arm64 iOS Simulator runtime, or set YILU_SIM_UDID."
    exit 1
  fi
}

case "$TARGET" in
  *simulator*)
    LIB_SUBDIR="ios_simulator_aarch64_cjnative"
    SDK="iphonesimulator"
    SIM_UDID="$(pick_iphone_udid)"
    DEST="platform=iOS Simulator,id=${SIM_UDID}"
    ;;
  *)
    LIB_SUBDIR="ios_aarch64_cjnative"
    SDK="iphoneos"
    SIM_UDID=""
    DEST="generic/platform=iOS"
    ;;
esac

CJ_LIBDIR="${YILU_CJ_LIBDIR:-$CANGJIE_HOME/lib/$LIB_SUBDIR}"

echo "---- cjc -v ----"
cjc -v
echo "---- target ----"
echo "YILU_IOS_TARGET=$TARGET"
echo "CJ_LIBDIR=$CJ_LIBDIR"
echo "xcodebuild destination: $DEST"
echo "SDK $SDK version: $(xcrun --sdk "$SDK" --show-sdk-version)"
echo "If cjc rejects the triple, re-run with YILU_IOS_TARGET set to the Target line from cjc -v,"
echo "or to the device form in the cross-compile page (aarch64-apple-ios<sdk version>)."

if [ ! -d "$CJ_LIBDIR" ]; then
  echo "Missing Cangjie iOS lib dir: $CJ_LIBDIR"
  echo "Expected by the cross-compile page:"
  echo "  \$CANGJIE_HOME/lib/ios_simulator_aarch64_cjnative   (simulator)"
  echo "  \$CANGJIE_HOME/lib/ios_aarch64_cjnative             (device)"
  exit 1
fi

if [ ! -f "$CJ_LIBDIR/section.o" ] || [ ! -f "$CJ_LIBDIR/cjstart.o" ]; then
  echo "Missing section.o or cjstart.o in $CJ_LIBDIR"
  exit 1
fi

cd "$SHARED"
cjpm build --target "$TARGET" -V

list="$(find target -name 'libyilu_zip*.a' | sort)"
if [ -z "$list" ]; then
  echo "cjpm build did not write libyilu_zip*.a under $SHARED/target"
  exit 1
fi
echo "$list"

mkdir -p "$APP/YiluXundian/Cangjie"
MERGED="$APP/YiluXundian/Cangjie/libyilu_zip.a"
set --
while IFS= read -r archive; do
  if [ -n "$archive" ]; then
    set -- "$@" "$archive"
  fi
done <<EOF
$list
EOF
/usr/bin/libtool -static -o "$MERGED" "$@"

LOCAL="$APP/Config/Cangjie.local.xcconfig"
{
  printf 'CANGJIE_HOME = %s\n' "$CANGJIE_HOME"
  printf 'CJ_LIBDIR = %s\n' "$CJ_LIBDIR"
  printf 'OTHER_LDFLAGS = $(inherited) %s/section.o %s/cjstart.o -lc++ -Wl,-no_compact_unwind -Wl,-u,_CJ_MRT_CjRuntimeInit -force_load $(SRCROOT)/YiluXundian/Cangjie/libyilu_zip.a' \
    "$CJ_LIBDIR" "$CJ_LIBDIR"
  for archive in "$CJ_LIBDIR"/*.a; do
    if [ -f "$archive" ]; then
      printf ' %s' "$archive"
    fi
  done
  printf '\n'
  printf 'LIBRARY_SEARCH_PATHS = $(inherited) %s $(SRCROOT)/YiluXundian/Cangjie\n' "$CJ_LIBDIR"
} > "$LOCAL"

echo "Wrote $MERGED"
echo "Wrote $LOCAL"

cd "$APP"
set -- \
  -project YiluXundian.xcodeproj \
  -scheme YiluXundian \
  -configuration Debug \
  -sdk "$SDK" \
  -destination "$DEST" \
  -derivedDataPath "$APP/build" \
  CODE_SIGNING_ALLOWED=NO
if [ "$SDK" = "iphonesimulator" ]; then
  # Do not let a generic/x86_64 slice look like a successful simulator build.
  set -- "$@" ARCHS=arm64 EXCLUDED_ARCHS=x86_64 ONLY_ACTIVE_ARCH=YES
fi
xcodebuild "$@" build

echo "xcodebuild finished a binary only. SMOKE is not green."
echo "This script does not install or launch, and it does not play 涿郡·范阳."
if [ "$SDK" = "iphonesimulator" ]; then
  echo "Simulator destination: $DEST (arm64 only; x86_64 excluded)."
  app_path=""
  while IFS= read -r candidate; do
    if [ -n "$candidate" ]; then
      app_path="$candidate"
      break
    fi
  done <<EOF
$(find "$APP/build/Build/Products" -type d -name 'YiluXundian.app' 2>/dev/null || true)
EOF
  if [ -n "$app_path" ]; then
    echo "App: $app_path"
    echo "Mac re-check, still not a pass until the board is on screen:"
    echo "  xcrun simctl boot $SIM_UDID"
    echo "  xcrun simctl install $SIM_UDID \"$app_path\""
    echo "  xcrun simctl launch --console $SIM_UDID com.yilu.xundian.ios"
    echo "Expected first screen: 涿郡·范阳 · id 1."
  fi
fi
