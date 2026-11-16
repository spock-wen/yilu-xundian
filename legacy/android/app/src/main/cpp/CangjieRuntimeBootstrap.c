/* Bring up the Cangjie runtime before the first @C call on Android.
 *
 * Programmer Mac smoke, tip 4986524 (4986524a6cb3cb8889c73cd2d475fc832dade380),
 * AVD grokdump (Pixel 6 / Android 15 arm64), 2026-09-27 00:28:40 CST:
 *   Check failed: runtime != nullptr
 *   yilu_load_level_json
 *     <- Java_com_yilu_xundian_YiluZip_nativeLoadLevel
 *     <- MainActivity.onCreate
 * Native libraries had already loaded. The board (涿郡·范阳 / id 1) never showed.
 * The same check is Runtime::Current() when the singleton is still null
 * (cangjie_runtime v1.1.3 runtime/src/Common/Runtime.h). iOS hits it unless
 * the shell calls CJ_MRT_CjRuntimeInit; Android previously did not.
 *
 * Android is not the Mach-O path. The 1.1.3 Android runtime is the aarch64
 * Linux ELF build: runtime/build/cmake/toolchain/android_aarch64_cangjie.cmake
 * sets OS=linux and defines __ANDROID__. There is no os/Linux/Section.cpp and
 * no dyld image walk. Do not copy legacy/ios/.../CangjieRuntimeBootstrap.c.
 *
 * Each Cangjie .so links aarch64_linux/Cjstart.S (same file the Android target
 * uses). That file puts __CJ_Init_Start in .init_array.0. On dlopen the
 * constructor does:
 *   MRT_LibraryOnLoad(&__CJMetadataStart, 1)
 * __CJMetadataStart is the ELF symbol at .cjmetadata.rw.header inside that
 * .so, not a pointer global filled from another image. System.loadLibrary of
 * the runtime and libyilu_zip*.so (YiluZip.prepare, before yilu_jni) therefore
 * already queues package metadata.
 *   Cjstart.S: https://github.com/cangjielanguage/cangjie_runtime/blob/v1.1.3/runtime/src/arch/aarch64_linux/Cjstart.S
 *   MRT_LibraryOnLoad: https://github.com/cangjielanguage/cangjie_runtime/blob/v1.1.3/runtime/src/CangjieRuntime.cpp
 *   "MRT_LibraryOnLoad can be invoked before runtime init":
 *   https://github.com/cangjielanguage/cangjie_runtime/blob/v1.1.3/runtime/src/LoaderManager.cpp
 * LoaderManager::AddPreLoadedImageMetaAddr does not deduplicate. Calling
 * MRT_LibraryOnLoad again from here would register the same header twice.
 * CJ_MRT_CjRuntimeInit is what drains that queue (LoaderManager::Init ->
 * LoadPreLoadedImages) and creates the singleton. On non-Apple it is an alias
 * of MRT_CjRuntimeInit:
 *   https://github.com/cangjielanguage/cangjie_runtime/blob/v1.1.3/runtime/src/CjScheduler.cpp
 * The Android .so exports it as CJ_MRT_CjRuntimeInit@@CANGJIE (default version),
 * so a normal reference binds. A second MRT_CjRuntimeInit fatals with
 * "don't support init again" (SetRuntimeInitFlag in CangjieRuntimeApi.cpp).
 *
 * Declared from libcangjie-runtime.so. CMake links -lcangjie-runtime so
 * DT_NEEDED is the soname, resolved after YiluZip.prepare has loaded it.
 */

extern void CJ_MRT_CjRuntimeInit(void);

void yilu_ensure_cj_runtime(void)
{
    static int started = 0;

    /* JNI_OnLoad and later native methods must not both enter init. */
    if (!__sync_bool_compare_and_swap(&started, 0, 1)) {
        return;
    }
    CJ_MRT_CjRuntimeInit();
}
