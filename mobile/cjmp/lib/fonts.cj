package ohos_app_cangjie_entry

// Note: FfiFontManagerRegisterFont is a private engine FFI symbol (workaround, Smoke D).
foreign func dlopen(path: CString, mode: Int32): CPointer<Unit>
foreign func dlsym(handle: CPointer<Unit>, symbol: CString): CPointer<Unit>

public func registerYiluFonts(): Int64 {
    unsafe {
        let symName = LibC.mallocCString("FfiFontManagerRegisterFont")
        var sym = CPointer<Unit>()
        var okHandle: Int64 = 0

        // (1) dlopen("libkeels_android.so", 2)
        let p1 = LibC.mallocCString("libkeels_android.so")
        let h1 = dlopen(p1, 2)
        LibC.free(p1)
        if (!h1.isNull()) {
            sym = dlsym(h1, symName)
            if (!sym.isNull()) {
                okHandle = 1
            }
        }

        // (2) dlopen(CString(CPointer<UInt8>()), 2) [null path = main program + deps, works on iOS]
        if (sym.isNull()) {
            let h2 = dlopen(CString(CPointer<UInt8>()), 2)
            if (!h2.isNull()) {
                sym = dlsym(h2, symName)
                if (!sym.isNull()) {
                    okHandle = 2
                }
            }
        }

        // (3) dlopen("@rpath/libkeels_ios.framework/libkeels_ios", 2)
        if (sym.isNull()) {
            let p3 = LibC.mallocCString("@rpath/libkeels_ios.framework/libkeels_ios")
            let h3 = dlopen(p3, 2)
            LibC.free(p3)
            if (!h3.isNull()) {
                sym = dlsym(h3, symName)
                if (!sym.isNull()) {
                    okHandle = 3
                }
            }
        }

        if (!sym.isNull()) {
            let regFont = CFunc<(CString, CString) -> Unit>(sym)
            let nameA = LibC.mallocCString(Theme.serif)
            let srcA = LibC.mallocCString("resource://RAWFILE/YiluSerif-Regular.otf")
            regFont(nameA, srcA)
            LibC.free(nameA)
            LibC.free(srcA)

            let nameB = LibC.mallocCString(Theme.serifBold)
            let srcB = LibC.mallocCString("resource://RAWFILE/YiluSerif-Bold.otf")
            regFont(nameB, srcB)
            LibC.free(nameB)
            LibC.free(srcB)

            // PENDING: YiluSans subsets are delivered by design; build scripts fail if the files are missing.
            let nameC = LibC.mallocCString(Theme.sansRegular)
            let srcC = LibC.mallocCString("resource://RAWFILE/YiluSans-Regular.otf")
            regFont(nameC, srcC)
            LibC.free(nameC)
            LibC.free(srcC)

            let nameD = LibC.mallocCString(Theme.sansMedium)
            let srcD = LibC.mallocCString("resource://RAWFILE/YiluSans-Medium.otf")
            regFont(nameD, srcD)
            LibC.free(nameD)
            LibC.free(srcD)
        }

        LibC.free(symName)
        return okHandle
    }
}
