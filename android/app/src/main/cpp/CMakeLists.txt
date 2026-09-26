cmake_minimum_required(VERSION 3.18)
project(yilu_jni C)

add_library(yilu_jni SHARED yilu_jni.c)

if(NOT YILU_C_HEADER_DIR)
    message(FATAL_ERROR "YILU_C_HEADER_DIR is unset. Pass -DYILU_C_HEADER_DIR=<repo>/mobile/include")
endif()
target_include_directories(yilu_jni PRIVATE "${YILU_C_HEADER_DIR}")

set(YILU_ZIP_SO "${CMAKE_CURRENT_SOURCE_DIR}/../jniLibs/arm64-v8a/libyilu_zip.so")
if(NOT EXISTS "${YILU_ZIP_SO}")
    message(FATAL_ERROR
        "Missing ${YILU_ZIP_SO}. Run android/scripts/build_debug.sh. "
        "Android smoke is BLOCKED until the Cangjie Android SDK and NDK are installed. "
        "See android/README.md.")
endif()

add_library(yilu_zip SHARED IMPORTED)
set_target_properties(yilu_zip PROPERTIES IMPORTED_LOCATION "${YILU_ZIP_SO}")

find_library(log-lib log)
target_link_libraries(yilu_jni yilu_zip ${log-lib})
