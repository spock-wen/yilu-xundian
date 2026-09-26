#ifndef YILU_ZIP_H
#define YILU_ZIP_H

#include <stdint.h>

/* C ABI exported by mobile/shared/src/ffi.cj (@C, unmangled names).
   https://cj-docs.gitcode.com/zh/1.1.3/dev-guide/source_zh_cn/FFI/cangjie-c.html
   iOS links this staticlib; Android JNI calls the same symbols from the .so. */

#ifdef __cplusplus
extern "C" {
#endif

int32_t yilu_load_level_json(const char *json);
int32_t yilu_ready(void);
int32_t yilu_last_error(uint8_t *buf, int32_t cap);
int32_t yilu_level_id(void);
int32_t yilu_cols(void);
int32_t yilu_rows(void);
int32_t yilu_copy_name(uint8_t *buf, int32_t cap);
int32_t yilu_number_at(int32_t x, int32_t y);
int32_t yilu_wall_count(void);
int32_t yilu_wall_at(int32_t index, int32_t *x1, int32_t *y1, int32_t *x2, int32_t *y2);
int32_t yilu_path_len(void);
int32_t yilu_path_at(int32_t index, int32_t *x, int32_t *y);
int32_t yilu_filled(void);
int32_t yilu_next_required(void);
int32_t yilu_is_win(void);
int32_t yilu_try_step(int32_t x, int32_t y);
int32_t yilu_undo(void);
void yilu_clear(void);
int32_t yilu_touch_to_cell(
    double px,
    double py,
    double origin_x,
    double origin_y,
    double cell,
    int32_t *out_x,
    int32_t *out_y);

#ifdef __cplusplus
}
#endif

#endif
