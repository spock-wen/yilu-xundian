#!/bin/bash
# Cross-compile the shared Zip engine for Android and assemble a debug APK.
# Does not install or launch the APK. Smoke is BLOCKED until NDK + Cangjie
# Android SDK + Android SDK exist on a build machine.
#
# Flags:
# https://cj-docs.gitcode.com/zh/1.1.3/dev-guide/source_zh_cn/compile_and_build/cross_compilation.html
#   --target=aarch64-linux-android          (API 26 by default)
#   --target=aarch64-linux-android31        (example of a higher API)
#   --sysroot <NDK>/toolchains/llvm/prebuilt/<host>/sysroot
#   -L <dir containing libclang_rt.builtins-aarch64-android.a>
#   runtime example: $CANGJIE_HOME/runtime/lib/linux_android31_aarch64_cjnative/*.so
# cjpm output-type "dynamic":
# https://docs.cangjie-lang.cn/cjnative/user_manual/tools/source_zh_cn/tools/cjpm_manual_cjnative_community.html
# cjc --output-type=dylib is .so on Linux:
# https://docs.cangjie-lang.cn/docs/1.0.3/user_manual/source_zh_cn/Appendix/compile_options.html

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
SHARED="$REPO/mobile/shared"
STAGE="$SHARED/.android-build"
JNILIBS="$ROOT/app/src/main/jniLibs/arm64-v8a"
ASSETS="$ROOT/app/src/main/assets"

blocked() {
  echo "SMOKE BLOCKED: Android smoke has not been run."
  echo "This script only assembles an APK. It does not install or launch it."
  echo "$*"
  exit 1
}

if [ -z "${CANGJIE_HOME:-}" ]; then
  blocked "CANGJIE_HOME is unset. Install a cangjie-sdk-*-android 1.1.3 package from https://cangjie-lang.cn/download/1.1.3 and source envsetup.sh."
fi

case "$CANGJIE_HOME" in
  *" "*) blocked "CANGJIE_HOME must not contain spaces: $CANGJIE_HOME" ;;
esac

if [ -f "$CANGJIE_HOME/envsetup.sh" ]; then
  set +u
  # shellcheck disable=SC1091
  . "$CANGJIE_HOME/envsetup.sh"
  set -u
fi

command -v cjpm >/dev/null 2>&1 || blocked "cjpm is not on PATH after sourcing envsetup.sh."
command -v cjc >/dev/null 2>&1 || blocked "cjc is not on PATH after sourcing envsetup.sh."

NDK="${ANDROID_NDK_HOME:-${ANDROID_NDK_ROOT:-}}"
if [ -z "$NDK" ] && [ -n "${ANDROID_HOME:-}" ] && [ -d "$ANDROID_HOME/ndk" ]; then
  NDK="$(find "$ANDROID_HOME/ndk" -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)"
fi
if [ -z "$NDK" ] || [ ! -d "$NDK" ]; then
  blocked "Android NDK not found. Set ANDROID_NDK_HOME to the NDK root (API 26+). The Cangjie cross-compile page says to download the NDK from the Android site."
fi
case "$NDK" in
  *" "*) blocked "ANDROID_NDK_HOME must not contain spaces: $NDK" ;;
esac

HOST_HINT=""
case "$(uname -s)-$(uname -m)" in
  Linux-x86_64) HOST_HINT="linux-x86_64" ;;
  Linux-aarch64) HOST_HINT="linux-aarch64" ;;
  Darwin-arm64) HOST_HINT="darwin-arm64" ;;
  Darwin-x86_64) HOST_HINT="darwin-x86_64" ;;
  MINGW*|MSYS*) HOST_HINT="windows-x86_64" ;;
esac

PREBUILT=""
if [ -n "$HOST_HINT" ] && [ -d "$NDK/toolchains/llvm/prebuilt/$HOST_HINT/sysroot" ]; then
  PREBUILT="$NDK/toolchains/llvm/prebuilt/$HOST_HINT"
fi
if [ -z "$PREBUILT" ]; then
  for dir in "$NDK"/toolchains/llvm/prebuilt/*; do
    if [ -d "$dir/sysroot" ]; then
      PREBUILT="$dir"
      break
    fi
  done
fi
if [ -z "$PREBUILT" ]; then
  blocked "NDK sysroot not found under $NDK/toolchains/llvm/prebuilt. The cross-compile page example is .../prebuilt/linux-x86_64/sysroot."
fi

SYSROOT="$PREBUILT/sysroot"
BUILTINS_FILE=""
while IFS= read -r candidate; do
  if [ -n "$candidate" ]; then
    BUILTINS_FILE="$candidate"
    break
  fi
done << EOF
$(find "$PREBUILT" -type f -name 'libclang_rt.builtins-aarch64-android.a')
EOF
if [ -z "$BUILTINS_FILE" ]; then
  blocked "libclang_rt.builtins-aarch64-android.a not found under $PREBUILT. The cross-compile page expects it at prebuilt/<host>/lib64/clang/<ver>/lib/linux."
fi
BUILTINS_DIR="$(dirname "$BUILTINS_FILE")"

# Default triple is API 26. The page's higher-API example is aarch64-linux-android31.
TARGET="${YILU_ANDROID_TARGET:-aarch64-linux-android}"
API="26"
case "$TARGET" in
  aarch64-linux-android[0-9]*)
    API="${TARGET#aarch64-linux-android}"
    ;;
esac

if [ -n "${YILU_CJ_ANDROID_RUNTIME:-}" ]; then
  RUNTIME="$YILU_CJ_ANDROID_RUNTIME"
else
  RUNTIME=""
  for candidate in \
    "$CANGJIE_HOME/runtime/lib/linux_android${API}_aarch64_cjnative" \
    "$CANGJIE_HOME/runtime/lib/linux_android_aarch64_cjnative"
  do
    if [ -d "$candidate" ]; then
      RUNTIME="$candidate"
      break
    fi
  done
fi
if [ -z "$RUNTIME" ] || [ ! -d "$RUNTIME" ]; then
  echo "Cangjie Android runtime directory not found."
  echo "The cross-compile page example (API 31) is:"
  echo "  \$CANGJIE_HOME/runtime/lib/linux_android31_aarch64_cjnative"
  echo "Set YILU_CJ_ANDROID_RUNTIME to the directory that actually exists."
  if [ -d "$CANGJIE_HOME/runtime/lib" ]; then
    echo "Contents of \$CANGJIE_HOME/runtime/lib:"
    find "$CANGJIE_HOME/runtime/lib" -maxdepth 1 -type d | sort
  fi
  blocked "runtime .so directory missing."
fi

SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
if [ -z "$SDK" ] || [ ! -d "$SDK/platforms/android-34" ]; then
  blocked "Android SDK platform 34 not found. Set ANDROID_HOME. This Gradle project uses compileSdk 34 and minSdk 26 (Cangjie Android minimum is API 26)."
fi

if ! command -v java >/dev/null 2>&1; then
  blocked "java is not on PATH. Gradle 8.7 / AGP 8.5.2 need a JDK (17)."
fi

echo "---- cjc -v ----"
cjc -v
echo "---- android target ----"
echo "YILU_ANDROID_TARGET=$TARGET"
echo "NDK=$NDK"
echo "SYSROOT=$SYSROOT"
echo "BUILTINS_DIR=$BUILTINS_DIR"
echo "RUNTIME=$RUNTIME"
echo "SMOKE BLOCKED: compile only, no emulator launch."

mkdir -p "$STAGE"
cat > "$STAGE/cjpm.toml" << EOF
[package]
  cjc-version = "1.1.3"
  name = "yilu_zip"
  description = "Generated Android dynamic build. Do not commit."
  version = "1.0.0"
  output-type = "dynamic"
  src-dir = "../src"

[target.${TARGET}]
  compile-option = "--sysroot ${SYSROOT} -L ${BUILTINS_DIR}"
EOF

cd "$STAGE"
cjpm build --target "$TARGET" -V

so_list="$(find target -type f -name 'libyilu_zip*.so' | sort)"
if [ -z "$so_list" ]; then
  echo "cjpm did not produce libyilu_zip*.so under $STAGE/target"
  echo "Expected cjpm output-type dynamic, which maps to cjc --output-type=dylib (.so on Linux targets)."
  echo "Files found:"
  find target -type f | sort
  blocked "missing libyilu_zip.so"
fi
if ! printf '%s\n' "$so_list" | grep -q 'libyilu_zip.so$'; then
  echo "Found Cangjie libraries but not libyilu_zip.so:"
  printf '%s\n' "$so_list"
  blocked "root libyilu_zip.so missing"
fi

rm -f "$JNILIBS"/*.so
mkdir -p "$JNILIBS" "$ASSETS"
cp "$SHARED/levels/zhuojun-fanyang.json" "$ASSETS/level.json"

runtime_list="$(find "$RUNTIME" -maxdepth 1 -type f -name '*.so' | sort)"
if [ -z "$runtime_list" ]; then
  blocked "No .so files in $RUNTIME"
fi

: > "$ASSETS/cangjie_native_libs.txt"
while IFS= read -r lib; do
  [ -n "$lib" ] || continue
  cp "$lib" "$JNILIBS/"
  base="$(basename "$lib")"
  base="${base#lib}"
  base="${base%.so}"
  printf '%s\n' "$base" >> "$ASSETS/cangjie_native_libs.txt"
done << EOF
$runtime_list
EOF

# Engine libraries after the runtime. Root last so DT_NEEDED inside the set resolves.
engine_first="$(printf '%s\n' "$so_list" | grep -E 'libyilu_zip\..*\.so$' || true)"
root_so="$(printf '%s\n' "$so_list" | grep -E 'libyilu_zip\.so$' || true)"
while IFS= read -r lib; do
  [ -n "$lib" ] || continue
  cp "$lib" "$JNILIBS/"
  base="$(basename "$lib")"
  base="${base#lib}"
  base="${base%.so}"
  printf '%s\n' "$base" >> "$ASSETS/cangjie_native_libs.txt"
done << EOF
$engine_first
$root_so
EOF

echo "jniLibs:"
find "$JNILIBS" -type f -name '*.so' | sort
echo "load order:"
cat "$ASSETS/cangjie_native_libs.txt"

cd "$ROOT"
if [ -x "$ROOT/gradlew" ]; then
  "$ROOT/gradlew" :app:assembleDebug
else
  command -v gradle >/dev/null 2>&1 || blocked "Neither ./gradlew nor gradle is runnable."
  gradle :app:assembleDebug
fi

echo "assembleDebug finished. APK is under android/app/build/outputs/apk/debug/."
echo "SMOKE BLOCKED: not installed, not launched, no UI pass."
