#!/bin/sh
# Fail the Xcode build with a pointer at the Mac setup script when the
# Cangjie staticlib has not been produced yet. SRCROOT is ios/app.
set -eu

LIB="${SRCROOT}/YiluXundian/Cangjie/libyilu_zip.a"
LOCAL="${SRCROOT}/Config/Cangjie.local.xcconfig"

if [ ! -f "$LIB" ] || [ ! -f "$LOCAL" ]; then
  echo "error: Cangjie iOS staticlib is not ready."
  echo "error: from the repo root, on a Mac with Xcode and cangjie-sdk-mac-aarch64-ios:"
  echo "error:   source \"\$CANGJIE_HOME/envsetup.sh\""
  echo "error:   ios/scripts/build_simulator.sh"
  echo "error: missing: $LIB"
  echo "error: missing: $LOCAL"
  exit 1
fi
