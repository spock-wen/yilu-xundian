cmake_minimum_required(VERSION 3.18)
project(yilu_jni C)

add_library(yilu_jni SHARED yilu_jni.c CangjieRuntimeBootstrap.c)

if(NOT YILU_C_HEADER_DIR)
    message(FATAL_ERROR "YILU_C_HEADER_DIR is unset. Pass -DYILU_C_HEADER_DIR=<repo>/engine/include")
endif()
target_include_directories(yilu_jni PRIVATE "${YILU_C_HEADER_DIR}")

set(YILU_ZIP_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../jniLibs/arm64-v8a")
set(YILU_ZIP_SO "${YILU_ZIP_DIR}/libyilu_zip.so")
set(YILU_CJ_RUNTIME_SO "${YILU_ZIP_DIR}/libcangjie-runtime.so")
if(NOT EXISTS "${YILU_ZIP_SO}")
    message(FATAL_ERROR
        "Missing ${YILU_ZIP_SO}. Run legacy/android/scripts/build_debug.sh. "
        "See legacy/android/README.md (tip f25f813: programmer Mac smoke PASSED, tester gate PASS).")
endif()
if(NOT EXISTS "${YILU_CJ_RUNTIME_SO}")
    message(FATAL_ERROR
        "Missing ${YILU_CJ_RUNTIME_SO}. CJ_MRT_CjRuntimeInit is exported from "
        "libcangjie-runtime.so. Run legacy/android/scripts/build_debug.sh. "
        "See legacy/android/README.md (tip f25f813: programmer Mac smoke PASSED, tester gate PASS).")
endif()

# Link via -L/-l so DT_NEEDED is "libyilu_zip.so" / "libcangjie-runtime.so",
# not an absolute host path (IMPORTED_LOCATION alone embeds the build-machine
# path and breaks device dlopen).
find_library(log-lib log)
target_link_directories(yilu_jni PRIVATE "${YILU_ZIP_DIR}")
target_link_libraries(yilu_jni PRIVATE yilu_zip cangjie-runtime ${log-lib})
