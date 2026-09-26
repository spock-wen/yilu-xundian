#include <jni.h>
#include <stdint.h>
#include <string.h>

#include "yilu_zip.h"
#include "CangjieRuntimeBootstrap.h"

/* JNI_OnLoad runs after YiluZip.prepare has dlopen'd the Cangjie .so files,
   so their .init_array constructors have already queued metadata. Every
   native method also calls the guard: a second CJ_MRT_CjRuntimeInit fatals. */
JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM *vm, void *reserved)
{
    (void)vm;
    (void)reserved;
    yilu_ensure_cj_runtime();
    return JNI_VERSION_1_6;
}

static jstring copy_buf(JNIEnv *env, int32_t (*read)(uint8_t *, int32_t)) {
    uint8_t buf[512];
    int32_t n = read(buf, (int32_t)sizeof(buf));
    if (n < 0) {
        n = 0;
    }
    if (n >= (int32_t)sizeof(buf)) {
        n = (int32_t)sizeof(buf) - 1;
    }
    buf[n] = 0;
    return (*env)->NewStringUTF(env, (const char *)buf);
}

static int write_pair(JNIEnv *env, jintArray out, int32_t x, int32_t y) {
    jint xy[2];
    if (out == NULL || (*env)->GetArrayLength(env, out) < 2) {
        return 0;
    }
    xy[0] = (jint)x;
    xy[1] = (jint)y;
    (*env)->SetIntArrayRegion(env, out, 0, 2, xy);
    return 1;
}

JNIEXPORT jint JNICALL
Java_com_yilu_xundian_YiluZip_nativeLoadLevel(JNIEnv *env, jclass clazz, jstring json) {
    const char *utf;
    int32_t rc;
    (void)clazz;
    yilu_ensure_cj_runtime();
    if (json == NULL) {
        return 1;
    }
    utf = (*env)->GetStringUTFChars(env, json, NULL);
    if (utf == NULL) {
        return 1;
    }
    rc = yilu_load_level_json(utf);
    (*env)->ReleaseStringUTFChars(env, json, utf);
    return rc;
}

JNIEXPORT jint JNICALL
Java_com_yilu_xundian_YiluZip_nativeReady(JNIEnv *env, jclass clazz) {
    (void)env;
    (void)clazz;
    yilu_ensure_cj_runtime();
    return yilu_ready();
}

JNIEXPORT jstring JNICALL
Java_com_yilu_xundian_YiluZip_nativeLastError(JNIEnv *env, jclass clazz) {
    (void)clazz;
    yilu_ensure_cj_runtime();
    return copy_buf(env, yilu_last_error);
}

JNIEXPORT jint JNICALL
Java_com_yilu_xundian_YiluZip_nativeLevelId(JNIEnv *env, jclass clazz) {
    (void)env;
    (void)clazz;
    yilu_ensure_cj_runtime();
    return yilu_level_id();
}

JNIEXPORT jint JNICALL
Java_com_yilu_xundian_YiluZip_nativeCols(JNIEnv *env, jclass clazz) {
    (void)env;
    (void)clazz;
    yilu_ensure_cj_runtime();
    return yilu_cols();
}

JNIEXPORT jint JNICALL
Java_com_yilu_xundian_YiluZip_nativeRows(JNIEnv *env, jclass clazz) {
    (void)env;
    (void)clazz;
    yilu_ensure_cj_runtime();
    return yilu_rows();
}

JNIEXPORT jstring JNICALL
Java_com_yilu_xundian_YiluZip_nativeLevelName(JNIEnv *env, jclass clazz) {
    (void)clazz;
    yilu_ensure_cj_runtime();
    return copy_buf(env, yilu_copy_name);
}

JNIEXPORT jint JNICALL
Java_com_yilu_xundian_YiluZip_nativeNumberAt(JNIEnv *env, jclass clazz, jint x, jint y) {
    (void)env;
    (void)clazz;
    yilu_ensure_cj_runtime();
    return yilu_number_at(x, y);
}

JNIEXPORT jint JNICALL
Java_com_yilu_xundian_YiluZip_nativeWallCount(JNIEnv *env, jclass clazz) {
    (void)env;
    (void)clazz;
    yilu_ensure_cj_runtime();
    return yilu_wall_count();
}

JNIEXPORT jint JNICALL
Java_com_yilu_xundian_YiluZip_nativeWallAt(JNIEnv *env, jclass clazz, jint index, jintArray out) {
    int32_t x1 = 0;
    int32_t y1 = 0;
    int32_t x2 = 0;
    int32_t y2 = 0;
    jint vals[4];
    (void)clazz;
    yilu_ensure_cj_runtime();
    if (out == NULL || (*env)->GetArrayLength(env, out) < 4) {
        return 0;
    }
    if (yilu_wall_at(index, &x1, &y1, &x2, &y2) != 1) {
        return 0;
    }
    vals[0] = (jint)x1;
    vals[1] = (jint)y1;
    vals[2] = (jint)x2;
    vals[3] = (jint)y2;
    (*env)->SetIntArrayRegion(env, out, 0, 4, vals);
    return 1;
}

JNIEXPORT jint JNICALL
Java_com_yilu_xundian_YiluZip_nativePathLen(JNIEnv *env, jclass clazz) {
    (void)env;
    (void)clazz;
    yilu_ensure_cj_runtime();
    return yilu_path_len();
}

JNIEXPORT jint JNICALL
Java_com_yilu_xundian_YiluZip_nativePathAt(JNIEnv *env, jclass clazz, jint index, jintArray out) {
    int32_t x = 0;
    int32_t y = 0;
    (void)clazz;
    yilu_ensure_cj_runtime();
    if (yilu_path_at(index, &x, &y) != 1) {
        return 0;
    }
    return write_pair(env, out, x, y);
}

JNIEXPORT jint JNICALL
Java_com_yilu_xundian_YiluZip_nativeFilled(JNIEnv *env, jclass clazz) {
    (void)env;
    (void)clazz;
    yilu_ensure_cj_runtime();
    return yilu_filled();
}

JNIEXPORT jint JNICALL
Java_com_yilu_xundian_YiluZip_nativeNextRequired(JNIEnv *env, jclass clazz) {
    (void)env;
    (void)clazz;
    yilu_ensure_cj_runtime();
    return yilu_next_required();
}

JNIEXPORT jint JNICALL
Java_com_yilu_xundian_YiluZip_nativeIsWin(JNIEnv *env, jclass clazz) {
    (void)env;
    (void)clazz;
    yilu_ensure_cj_runtime();
    return yilu_is_win();
}

JNIEXPORT jint JNICALL
Java_com_yilu_xundian_YiluZip_nativeTryStep(JNIEnv *env, jclass clazz, jint x, jint y) {
    (void)env;
    (void)clazz;
    yilu_ensure_cj_runtime();
    return yilu_try_step(x, y);
}

JNIEXPORT jint JNICALL
Java_com_yilu_xundian_YiluZip_nativeUndo(JNIEnv *env, jclass clazz) {
    (void)env;
    (void)clazz;
    yilu_ensure_cj_runtime();
    return yilu_undo();
}

JNIEXPORT void JNICALL
Java_com_yilu_xundian_YiluZip_nativeClear(JNIEnv *env, jclass clazz) {
    (void)env;
    (void)clazz;
    yilu_ensure_cj_runtime();
    yilu_clear();
}

JNIEXPORT jint JNICALL
Java_com_yilu_xundian_YiluZip_nativeTouch(
    JNIEnv *env,
    jclass clazz,
    jdouble px,
    jdouble py,
    jdouble origin_x,
    jdouble origin_y,
    jdouble cell,
    jintArray out
) {
    int32_t x = 0;
    int32_t y = 0;
    (void)clazz;
    yilu_ensure_cj_runtime();
    if (yilu_touch_to_cell(px, py, origin_x, origin_y, cell, &x, &y) != 1) {
        return 0;
    }
    return write_pair(env, out, x, y);
}
