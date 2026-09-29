package ohos_app_cangjie_entry

/*
 * U3: Parity reject overlay toast avoidance (designer ruling).
 * Shifts the toast horizontally so a gap of at least 6 vp remains to all board obstacles
 * (flash line, head dot, station circles, 下一驿 labels, parity labels).
 * Tries shifting LEFT first; if left edge < 16 vp, shifts RIGHT from default.
 * Toast y is fixed at midY - 36 (never moves vertically).
 */

public struct ToastBox {
    public let x0: Float64
    public let y0: Float64
    public let x1: Float64
    public let y1: Float64

    public init(x0: Float64, y0: Float64, x1: Float64, y1: Float64) {
        if (x0 <= x1) {
            this.x0 = x0
            this.x1 = x1
        } else {
            this.x0 = x1
            this.x1 = x0
        }
        if (y0 <= y1) {
            this.y0 = y0
            this.y1 = y1
        } else {
            this.y0 = y1
            this.y1 = y0
        }
    }
}

func isBlocking(box: ToastBox, x: Float64, tw: Float64, top: Float64, bottom: Float64): Bool {
    // Check if obstacle's y-range inflated by 6 overlaps [top, bottom] with gap < 6 vp.
    // 1e-6 epsilon guards against floating point rounding errors when setting exact 6 vp offsets.
    if (box.y1 + 6.0 <= top + 1e-6 || box.y0 - 6.0 >= bottom - 1e-6) {
        return false
    }
    // Check if obstacle's x-range inflated by 6 overlaps [x, x + tw] with gap < 6 vp.
    if (box.x1 + 6.0 <= x + 1e-6 || box.x0 - 6.0 >= x + tw - 1e-6) {
        return false
    }
    return true
}

public func toastAvoidX(trayW: Float64, midX: Float64, midY: Float64, boxes: Array<ToastBox>): Float64 {
    let tw: Float64 = 86.0
    let top: Float64 = midY - 36.0
    let bottom: Float64 = midY - 8.0
    let defaultX: Float64 = midX - 43.0

    // Check if default position is blocked by any obstacle
    var defaultBlocked = false
    for (box in boxes) {
        if (isBlocking(box, defaultX, tw, top, bottom)) {
            defaultBlocked = true
            break
        }
    }

    if (!defaultBlocked) {
        var x = defaultX
        if (x < 0.0) {
            x = 0.0
        }
        let maxW = trayW - tw
        if (x > maxW) {
            x = maxW
        }
        return x
    }

    // Shift left first: repeatedly set x = (min over blocking boxes of x0) - 6 - tw
    var curLeftX = defaultX
    var iter = 0
    while (iter < 16) {
        var hasBlocking = false
        var minX0 = 0.0
        for (box in boxes) {
            if (isBlocking(box, curLeftX, tw, top, bottom)) {
                if (!hasBlocking || box.x0 < minX0) {
                    minX0 = box.x0
                }
                hasBlocking = true
            }
        }
        if (!hasBlocking) {
            break
        }
        let nextX = minX0 - 6.0 - tw
        if (nextX >= curLeftX) {
            break
        }
        curLeftX = nextX
        iter = iter + 1
    }

    if (curLeftX >= 16.0) {
        return curLeftX
    }

    // If resulting left edge < 16 vp, shift right from default instead
    var curRightX = defaultX
    iter = 0
    while (iter < 16) {
        var hasBlocking = false
        var maxX1 = 0.0
        for (box in boxes) {
            if (isBlocking(box, curRightX, tw, top, bottom)) {
                if (!hasBlocking || box.x1 > maxX1) {
                    maxX1 = box.x1
                }
                hasBlocking = true
            }
        }
        if (!hasBlocking) {
            break
        }
        let nextX = maxX1 + 6.0
        if (nextX <= curRightX) {
            break
        }
        curRightX = nextX
        iter = iter + 1
    }

    let maxW = trayW - tw
    if (curRightX > maxW) {
        return maxW
    }
    return curRightX
}
