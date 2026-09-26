/* Bring up the Cangjie runtime before the first @C call.
 *
 * Mac crash 2026-09-26 (com.yilu.xundian.ios, arm64 simulator):
 *   yilu_load_level_json
 *   -> CJ_MCC_N2CStub
 *   -> MRT_TryNewAndRunCJThread
 *   -> MapleRuntime::Logger::FormatLog
 *   -> abort
 * No managed frame ran. The board never appeared.
 *
 * Current runtime (cangjielanguage/cangjie_runtime) names that helper
 * MRT_NewForeignCJThread. It calls Runtime::Current(), and Current()
 * fatals when the runtime singleton is still null:
 *   runtime/src/Common/Runtime.h  CHECK(runtime != nullptr)
 *   runtime/src/Base/Log.cpp      RTLOG_FATAL then std::abort()
 * The 1.1.3 iOS SDK's symbol is MRT_TryNewAndRunCJThread; the stack
 * shape matches that check. This VM cannot nm the Mac SDK.
 *
 * cjstart only calls MRT_LibraryOnLoad (aarch64_ios/Cjstart.S).
 * LoaderManager::LoadFile queues that address and does not create the
 * runtime (LoaderManager.cpp: "MRT_LibraryOnLoad can be invoked before
 * runtime init"). The zero-arg start used by the runtime itself is
 * MRT_CjRuntimeInit, exported on Apple as CJ_MRT_CjRuntimeInit
 * (runtime/src/CjScheduler.cpp).
 *
 * On Apple, CJFile::LoadMacCJFileMeta dereferences the header slots, and
 * those slots are the section.o globals (os/Macos/Section.cpp). InitData
 * fills them by matching dladdr's path to _dyld_get_image_name. If that
 * match fails, _CJMetadataStart stays 0 and MRT_LibraryOnLoad returns
 * immediately (CangjieRuntime.cpp). The sections are still in the main
 * image; this file fills the same globals from dyld when the pointer is 0.
 *
 * Official link order remains section.o, cjstart.o, -lc++:
 * https://cj-docs.gitcode.com/zh/1.1.3/dev-guide/source_zh_cn/compile_and_build/cross_compilation.html
 */

#include <mach-o/dyld.h>
#include <mach-o/getsect.h>
#include <mach-o/loader.h>
#include <stddef.h>
#include <stdint.h>

extern unsigned long _CJMetadataSize;
extern uintptr_t _CJMetadataStart;
extern unsigned long _CJSDKVersionSize;
extern uintptr_t _CJSDKVersion;
extern unsigned long _CJMethodInfoSize;
extern uintptr_t _CJMethodInfo;
extern unsigned long _CJGlobalInitFuncSize;
extern uintptr_t _CJGlobalInitFunc;
extern unsigned long _CJStringPoolDictSize;
extern uintptr_t _CJStringPoolDict;
extern unsigned long _CJStringPoolSize;
extern uintptr_t _CJStringPool;
extern unsigned long _CJStackMapSize;
extern uintptr_t _CJStackMap;
extern unsigned long _CJGCTibSize;
extern uintptr_t _CJGCTib;
extern unsigned long _CJGCRootsSize;
extern uintptr_t _CJGCRoots;
extern unsigned long _CJTypeTemplateSize;
extern uintptr_t _CJTypeTemplate;
extern unsigned long _CJTypeInfoSize;
extern uintptr_t _CJTypeInfo;
extern unsigned long _CJTypeFieldsSize;
extern uintptr_t _CJTypeFields;
extern unsigned long _CJMTableSize;
extern uintptr_t _CJMTable;
extern unsigned long _CJInnerTypeExtensionsSize;
extern uintptr_t _CJInnerTypeExtensions;
extern unsigned long _CJOuterTypeExtensionsSize;
extern uintptr_t _CJOuterTypeExtensions;
extern unsigned long _CJStaticGITableSize;
extern uintptr_t _CJStaticGITable;
extern unsigned long _CJGCFlagsSize;
extern uintptr_t _CJGCFlags;
extern unsigned long _CJGCReflectPkgInfoSize;
extern uintptr_t _CJReflectPkgInfo;
extern unsigned long _CJReflectGVSize;
extern uintptr_t _CJReflectGV;
extern unsigned long _CJReflectGISize;
extern uintptr_t _CJReflectGI;
extern unsigned long _CJTypeExtSize;
extern uintptr_t _CJTypeExt;
extern int _CJMetaDataSize;
extern unsigned long *g_runtimeStaticStart;
extern unsigned long *g_runtimeStaticEnd;

extern void MRT_LibraryOnLoad(uint64_t address, _Bool enable_gc);
extern void CJ_MRT_CjRuntimeInit(void);

static const struct mach_header_64 *image_with_cj_header(void)
{
    uint32_t count = _dyld_image_count();
    uint32_t i;
    for (i = 0; i < count; i++) {
        const struct mach_header *raw = _dyld_get_image_header(i);
        const struct mach_header_64 *mh;
        unsigned long size = 0;
        uint8_t *bytes;
        if (raw == 0 || raw->magic != MH_MAGIC_64) {
            continue;
        }
        mh = (const struct mach_header_64 *)raw;
        bytes = getsectiondata(mh, "__CJMETAHEADER", "__cjmetaheader", &size);
        if (bytes != 0 && size != 0) {
            return mh;
        }
    }
    return 0;
}

static uintptr_t take_section(
    const struct mach_header_64 *mh,
    const char *seg,
    const char *sect,
    unsigned long *size_out
) {
    unsigned long size = 0;
    uint8_t *bytes = getsectiondata(mh, seg, sect, &size);
    if (size_out != 0) {
        *size_out = size;
    }
    if (bytes == 0) {
        return 0;
    }
    return (uintptr_t)bytes;
}

static void note_span(uintptr_t addr, unsigned long size, uintptr_t *lo, uintptr_t *hi, int *any)
{
    uintptr_t end;
    if (addr == 0 && size == 0) {
        return;
    }
    end = addr + (uintptr_t)size;
    if (!*any || addr < *lo) {
        *lo = addr;
    }
    if (!*any || end > *hi) {
        *hi = end;
    }
    *any = 1;
}

/* Same slots as Section.cpp InitSectionInformation / InitData. */
static void fill_metadata_globals(const struct mach_header_64 *mh)
{
    uintptr_t lo = 0;
    uintptr_t hi = 0;
    int any = 0;
    unsigned long text_size = 0;
    uintptr_t text;

    _CJMetadataStart = take_section(mh, "__CJMETAHEADER", "__cjmetaheader", &_CJMetadataSize);
    _CJSDKVersion = take_section(mh, "__CJ_METADATA", "__cjsdkversion", &_CJSDKVersionSize);
    _CJMethodInfo = take_section(mh, "__CJ_METADATA", "__cjmethodinfo", &_CJMethodInfoSize);
    _CJGlobalInitFunc = take_section(mh, "__CJ_METADATA", "__cjglobalFunc", &_CJGlobalInitFuncSize);
    _CJStringPoolDict = take_section(mh, "__CJ_METADATA", "__cjstrpooldict", &_CJStringPoolDictSize);
    _CJStringPool = take_section(mh, "__CJ_METADATA", "__cjstrpool", &_CJStringPoolSize);
    _CJStackMap = take_section(mh, "__CJ_METADATA", "__cjstackmap", &_CJStackMapSize);
    _CJGCTib = take_section(mh, "__CJ_METADATA", "__cjgctib", &_CJGCTibSize);
    _CJGCRoots = take_section(mh, "__CJ_METADATA", "__cjgcroots", &_CJGCRootsSize);
    _CJTypeTemplate = take_section(mh, "__CJ_METADATA", "__cjtemplate", &_CJTypeTemplateSize);
    _CJTypeInfo = take_section(mh, "__CJ_METADATA", "__cjtypeinfo", &_CJTypeInfoSize);
    _CJTypeFields = take_section(mh, "__CJ_METADATA", "__cj_fields", &_CJTypeFieldsSize);
    _CJMTable = take_section(mh, "__CJ_METADATA", "__cjmtable", &_CJMTableSize);
    _CJInnerTypeExtensions = take_section(mh, "__CJ_METADATA", "__cjinnerty_eds", &_CJInnerTypeExtensionsSize);
    _CJOuterTypeExtensions = take_section(mh, "__CJ_METADATA", "__cjouterty_eds", &_CJOuterTypeExtensionsSize);
    _CJStaticGITable = take_section(mh, "__CJ_METADATA", "__cjstatic_gi", &_CJStaticGITableSize);
    _CJGCFlags = take_section(mh, "__CJ_METADATA", "__cjgcflags", &_CJGCFlagsSize);
    _CJReflectPkgInfo = take_section(mh, "__CJ_METADATA", "__cjref_pkginfo", &_CJGCReflectPkgInfoSize);
    _CJReflectGV = take_section(mh, "__CJ_METADATA", "__cjref_gv", &_CJReflectGVSize);
    _CJReflectGI = take_section(mh, "__CJ_METADATA", "__cjref_gi", &_CJReflectGISize);
    _CJTypeExt = take_section(mh, "__CJ_METADATA", "__cjtype_ext", &_CJTypeExtSize);

    text = take_section(mh, "__TEXT", "__cjrt_text", &text_size);
    g_runtimeStaticStart = (unsigned long *)text;
    g_runtimeStaticEnd = (unsigned long *)(text + (uintptr_t)text_size);

    note_span(_CJSDKVersion, _CJSDKVersionSize, &lo, &hi, &any);
    note_span(_CJMethodInfo, _CJMethodInfoSize, &lo, &hi, &any);
    note_span(_CJGlobalInitFunc, _CJGlobalInitFuncSize, &lo, &hi, &any);
    note_span(_CJStringPoolDict, _CJStringPoolDictSize, &lo, &hi, &any);
    note_span(_CJStringPool, _CJStringPoolSize, &lo, &hi, &any);
    note_span(_CJStackMap, _CJStackMapSize, &lo, &hi, &any);
    note_span(_CJGCTib, _CJGCTibSize, &lo, &hi, &any);
    note_span(_CJGCRoots, _CJGCRootsSize, &lo, &hi, &any);
    note_span(_CJTypeTemplate, _CJTypeTemplateSize, &lo, &hi, &any);
    note_span(_CJTypeInfo, _CJTypeInfoSize, &lo, &hi, &any);
    note_span(_CJTypeFields, _CJTypeFieldsSize, &lo, &hi, &any);
    note_span(_CJMTable, _CJMTableSize, &lo, &hi, &any);
    note_span(_CJInnerTypeExtensions, _CJInnerTypeExtensionsSize, &lo, &hi, &any);
    note_span(_CJOuterTypeExtensions, _CJOuterTypeExtensionsSize, &lo, &hi, &any);
    note_span(_CJStaticGITable, _CJStaticGITableSize, &lo, &hi, &any);
    note_span(_CJGCFlags, _CJGCFlagsSize, &lo, &hi, &any);
    note_span(_CJReflectPkgInfo, _CJGCReflectPkgInfoSize, &lo, &hi, &any);
    note_span(_CJReflectGV, _CJReflectGVSize, &lo, &hi, &any);
    note_span(_CJReflectGI, _CJReflectGISize, &lo, &hi, &any);
    note_span(_CJTypeExt, _CJTypeExtSize, &lo, &hi, &any);
    if (any && hi >= lo) {
        _CJMetaDataSize = (int)(hi - lo);
    }
}

void yilu_ensure_cj_runtime(void)
{
    static int started = 0;
    const struct mach_header_64 *mh;

    if (started) {
        return;
    }
    started = 1;

    if (_CJMetadataStart == 0) {
        mh = image_with_cj_header();
        if (mh != 0) {
            fill_metadata_globals(mh);
        }
        /* cjstart's constructor no-ops on a null pointer, so the image
           was not queued. Queue it before runtime init drains the list. */
        if (_CJMetadataStart != 0) {
            MRT_LibraryOnLoad((uint64_t)_CJMetadataStart, 1);
        }
    }

    /* Do not call this twice. A second MRT_CjRuntimeInit fatals with
       "don't support init again" (SetRuntimeInitFlag). */
    CJ_MRT_CjRuntimeInit();
}
