package yilu_zip

import yilu_zip.engine.{Cell, GridLayout, touchToCell}
import yilu_zip.game.{PatrolGame, blankLevel, levelFromJson}

/* C ABI for the iOS and Android shells. @C exports keep the C names (no CJ_ prefix).
   https://cj-docs.gitcode.com/zh/1.1.3/dev-guide/source_zh_cn/FFI/cangjie-c.html
   iOS must link cjstart.o so the runtime is up before these run.
   Android loads the Cangjie runtime .so files before libyilu_zip.so.
   https://cj-docs.gitcode.com/zh/1.1.3/dev-guide/source_zh_cn/compile_and_build/cross_compilation.html */

var gGame: PatrolGame = PatrolGame(blankLevel())
var gReady: Bool = false
var gError: String = ""

func flag(ok: Bool): Int32 {
    if (ok) {
        return 1
    }
    return 0
}

func writeUtf8(text: String, buf: CPointer<UInt8>, cap: Int32): Int32 {
    if (buf.isNull() || cap <= 0) {
        return -1
    }
    var n = text.size
    let limit = Int64(cap) - 1
    if (n > limit) {
        n = limit
    }
    if (n < 0) {
        return -1
    }
    var i: Int64 = 0
    while (i < n) {
        let b = text[i]
        unsafe {
            let p = buf + i
            p.write(b)
        }
        i = i + 1
    }
    unsafe {
        let p = buf + n
        p.write(0u8)
    }
    return Int32(n)
}

@C
public func yilu_load_level_json(json: CString): Int32 {
    if (json.isNull()) {
        gReady = false
        gError = "null json pointer"
        return 1
    }
    let text = json.toString()
    let loaded = levelFromJson(text)
    match (loaded.level) {
        case Some(level) =>
            gGame.reset(level)
            gReady = true
            gError = ""
            return 0
        case None =>
            gReady = false
            gError = loaded.error
            return 1
    }
}

@C
public func yilu_ready(): Int32 {
    return flag(gReady)
}

@C
public func yilu_last_error(buf: CPointer<UInt8>, cap: Int32): Int32 {
    return writeUtf8(gError, buf, cap)
}

@C
public func yilu_level_id(): Int32 {
    if (!gReady) {
        return -1
    }
    return Int32(gGame.level.id)
}

@C
public func yilu_cols(): Int32 {
    if (!gReady) {
        return 0
    }
    return Int32(gGame.grid.cols)
}

@C
public func yilu_rows(): Int32 {
    if (!gReady) {
        return 0
    }
    return Int32(gGame.grid.rows)
}

@C
public func yilu_copy_name(buf: CPointer<UInt8>, cap: Int32): Int32 {
    if (!gReady) {
        return writeUtf8("", buf, cap)
    }
    return writeUtf8(gGame.level.name, buf, cap)
}

@C
public func yilu_number_at(x: Int32, y: Int32): Int32 {
    if (!gReady) {
        return 0
    }
    return Int32(gGame.numberAt(Int64(x), Int64(y)))
}

@C
public func yilu_wall_count(): Int32 {
    if (!gReady) {
        return 0
    }
    return Int32(gGame.level.walls.size)
}

@C
public func yilu_wall_at(
    index: Int32,
    x1: CPointer<Int32>,
    y1: CPointer<Int32>,
    x2: CPointer<Int32>,
    y2: CPointer<Int32>
): Int32 {
    if (!gReady || x1.isNull() || y1.isNull() || x2.isNull() || y2.isNull()) {
        return 0
    }
    let i = Int64(index)
    if (i < 0 || i >= gGame.level.walls.size) {
        return 0
    }
    let wall = gGame.level.walls[i]
    unsafe {
        x1.write(Int32(wall.x1))
        y1.write(Int32(wall.y1))
        x2.write(Int32(wall.x2))
        y2.write(Int32(wall.y2))
    }
    return 1
}

@C
public func yilu_path_len(): Int32 {
    if (!gReady) {
        return 0
    }
    return Int32(gGame.path.size())
}

@C
public func yilu_path_at(index: Int32, x: CPointer<Int32>, y: CPointer<Int32>): Int32 {
    if (!gReady || x.isNull() || y.isNull()) {
        return 0
    }
    let i = Int64(index)
    if (i < 0 || i >= gGame.path.size()) {
        return 0
    }
    let cell = gGame.path.at(i)
    unsafe {
        x.write(Int32(cell.x))
        y.write(Int32(cell.y))
    }
    return 1
}

@C
public func yilu_filled(): Int32 {
    if (!gReady) {
        return 0
    }
    return Int32(gGame.filled())
}

@C
public func yilu_next_required(): Int32 {
    if (!gReady) {
        return 0
    }
    return Int32(gGame.nextRequired())
}

@C
public func yilu_is_win(): Int32 {
    if (!gReady) {
        return 0
    }
    return flag(gGame.isWin())
}

@C
public func yilu_try_step(x: Int32, y: Int32): Int32 {
    if (!gReady) {
        return 0
    }
    return flag(gGame.tryStep(Cell(Int64(x), Int64(y))))
}

@C
public func yilu_undo(): Int32 {
    if (!gReady) {
        return 0
    }
    return flag(gGame.undo())
}

@C
public func yilu_clear(): Unit {
    if (!gReady) {
        return
    }
    gGame.clear()
}

@C
public func yilu_touch_to_cell(
    px: Float64,
    py: Float64,
    originX: Float64,
    originY: Float64,
    cell: Float64,
    outX: CPointer<Int32>,
    outY: CPointer<Int32>
): Int32 {
    if (!gReady || cell <= 0.0 || outX.isNull() || outY.isNull()) {
        return 0
    }
    let layout = GridLayout(originX, originY, cell, gGame.grid.cols, gGame.grid.rows)
    match (touchToCell(px, py, layout)) {
        case Some(hit) =>
            unsafe {
                outX.write(Int32(hit.x))
                outY.write(Int32(hit.y))
            }
            return 1
        case None => return 0
    }
}
