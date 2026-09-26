package com.yilu.xundian

import android.content.Context
import java.io.IOException

/** JNI pass-through. Zip rules stay in the Cangjie `yilu_zip` library. */
object YiluZip {
    private var nativesReady = false

    fun prepare(context: Context) {
        if (nativesReady) {
            return
        }
        val names = try {
            context.assets.open("cangjie_native_libs.txt").bufferedReader().use { it.readText() }
        } catch (e: IOException) {
            throw IllegalStateException(
                "assets/cangjie_native_libs.txt is missing. Run android/scripts/build_debug.sh. " +
                    "Android smoke is BLOCKED until the Cangjie Android SDK and NDK exist.",
                e
            )
        }
        for (raw in names.lineSequence()) {
            val name = raw.trim()
            if (name.isEmpty() || name.startsWith("#")) {
                continue
            }
            System.loadLibrary(name)
        }
        /* Cangjie .so constructors (ELF .init_array -> MRT_LibraryOnLoad) must
           run before yilu_jni. JNI_OnLoad then calls CJ_MRT_CjRuntimeInit. */
        System.loadLibrary("yilu_jni")
        nativesReady = true
    }

    fun loadAssetLevel(context: Context): String? {
        val json = context.assets.open("level.json").bufferedReader().use { it.readText() }
        val rc = nativeLoadLevel(json)
        if (rc != 0 || nativeReady() != 1) {
            val err = nativeLastError()
            return if (err.isEmpty()) "yilu_load_level_json failed" else err
        }
        return null
    }

    fun levelName(): String = nativeLevelName()

    private external fun nativeLoadLevel(json: String): Int
    external fun nativeReady(): Int
    private external fun nativeLastError(): String
    external fun nativeLevelId(): Int
    external fun nativeCols(): Int
    external fun nativeRows(): Int
    private external fun nativeLevelName(): String
    external fun nativeNumberAt(x: Int, y: Int): Int
    external fun nativeWallCount(): Int
    external fun nativeWallAt(index: Int, out: IntArray): Int
    external fun nativePathLen(): Int
    external fun nativePathAt(index: Int, out: IntArray): Int
    external fun nativeFilled(): Int
    external fun nativeNextRequired(): Int
    external fun nativeIsWin(): Int
    external fun nativeTryStep(x: Int, y: Int): Int
    external fun nativeUndo(): Int
    external fun nativeClear()
    external fun nativeTouch(
        px: Double,
        py: Double,
        originX: Double,
        originY: Double,
        cell: Double,
        out: IntArray
    ): Int
}
