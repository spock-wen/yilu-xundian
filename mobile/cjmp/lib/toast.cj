package ohos_app_cangjie_entry

import std.collection.ArrayList

/*
 * Parity reject overlay toast avoidance (designer final ruling).
 * Toast is 86 wide x 28 high vp, one line.
 * All coordinates are tray coordinates in vp (u). E = rejected-edge midpoint (midX, midY).
 * Obstacles = ToastBox list from collectToastObstacles().
 *
 * Validity of candidate rect (x, y, 86, 28):
 *   - horizontally inside tray with >= 16 from left/right edges: 16 <= x and x + 86 <= trayW - 16
 *   - vertically inside tray with >= 8 from top/bottom edges: 8 <= y and y + 28 <= trayH - 8
 *   - for every obstacle box b, clearance >= b.clear: box inflated by b.clear must not overlap rect
 *
 * Candidate x set: {midX - 43, 16, trayW - 16 - 86} plus for each obstacle box b:
 *   b.x0 - b.clear - 86 and b.x1 + b.clear
 *
 * Placement order:
 *  (a) ABOVE: y = midY - 36 (bottom = midY - 8). Horizontal shift only, |dx| <= 96 where dx = (x + 43) - midX.
 *      Choose valid x with smallest |dx|; on tie LEFT wins ("left first then right"). Centred (dx = 0) is smallest |dx|.
 *  (b) If (a) has no valid x: lift upward in 2u steps, lift = 2, 4, ..., 24 (y = midY - 36 - lift),
 *      same horizontal search (|dx| <= 96); take the SMALLEST lift that has a fit.
 *  (c) If (b) has none: BELOW, y = midY + 8 (top = midY + 8), same horizontal search, |dx| <= 96.
 *  (d) If nothing fits: do NOT place toast; return shown = false, step = 0, x = midX - 43, y = midY - 36, lift = 0.
 */

public struct ToastBox {
    public let x0: Float64
    public let y0: Float64
    public let x1: Float64
    public let y1: Float64
    public let clear: Float64

    public init(x0: Float64, y0: Float64, x1: Float64, y1: Float64) {
        this(x0, y0, x1, y1, 6.0)
    }

    public init(x0: Float64, y0: Float64, x1: Float64, y1: Float64, clear: Float64) {
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
        this.clear = clear
    }
}

public struct ToastPlacement {
    public let x: Float64
    public let y: Float64
    public let shown: Bool
    public let step: Int64
    public let lift: Float64

    public init(x: Float64, y: Float64, shown: Bool, step: Int64, lift: Float64) {
        this.x = x
        this.y = y
        this.shown = shown
        this.step = step
        this.lift = lift
    }
}

public func isBlocking(box: ToastBox, x: Float64, tw: Float64, top: Float64, bottom: Float64): Bool {
    // Check if obstacle's y-range inflated by box.clear overlaps [top, bottom] with gap < clear.
    // 1e-6 epsilon guards against floating point rounding errors.
    if (box.y1 + box.clear <= top + 1e-6 || box.y0 - box.clear >= bottom - 1e-6) {
        return false
    }
    // Check if obstacle's x-range inflated by box.clear overlaps [x, x + tw] with gap < clear.
    if (box.x1 + box.clear <= x + 1e-6 || box.x0 - box.clear >= x + tw - 1e-6) {
        return false
    }
    return true
}

func isValid(x: Float64, y: Float64, trayW: Float64, trayH: Float64, boxes: Array<ToastBox>): Bool {
    let tw: Float64 = 86.0
    let th: Float64 = 28.0
    if (y < 8.0 - 1e-6 || y + th > trayH - 8.0 + 1e-6) {
        return false
    }
    if (x < 16.0 - 1e-6 || x + tw > trayW - 16.0 + 1e-6) {
        return false
    }
    for (box in boxes) {
        if (isBlocking(box, x, tw, y, y + th)) {
            return false
        }
    }
    return true
}

func absVal(v: Float64): Float64 {
    if (v < 0.0) {
        return -v
    }
    return v
}

func searchAtY(y: Float64, midX: Float64, trayW: Float64, trayH: Float64, cands: ArrayList<Float64>, boxes: Array<ToastBox>): Option<Float64> {
    var bestX = 0.0
    var bestAbsDx = 1e9
    var bestDx = 0.0
    var found = false

    for (candX in cands) {
        if (isValid(candX, y, trayW, trayH, boxes)) {
            let dx = (candX + 43.0) - midX
            let adx = absVal(dx)
            if (adx <= 96.0 + 1e-6) {
                if (!found) {
                    bestX = candX
                    bestAbsDx = adx
                    bestDx = dx
                    found = true
                } else if (adx < bestAbsDx - 1e-6) {
                    bestX = candX
                    bestAbsDx = adx
                    bestDx = dx
                } else if (absVal(adx - bestAbsDx) <= 1e-6) {
                    // Tie: left one wins ("left first then right")
                    if (dx < bestDx - 1e-6) {
                        bestX = candX
                        bestAbsDx = adx
                        bestDx = dx
                    }
                }
            }
        }
    }

    if (found) {
        return Some(bestX)
    }
    return None
}

public func toastPlace(trayW: Float64, trayH: Float64, midX: Float64, midY: Float64, boxes: Array<ToastBox>): ToastPlacement {
    let tw: Float64 = 86.0
    let cX: Float64 = midX - 43.0
    let minX: Float64 = 16.0
    let maxX: Float64 = trayW - 16.0 - tw

    // Deterministic candidate x generation
    let cands = ArrayList<Float64>()
    cands.add(cX)
    cands.add(minX)
    cands.add(maxX)
    for (b in boxes) {
        cands.add(b.x0 - b.clear - tw)
        cands.add(b.x1 + b.clear)
    }

    // (a) ABOVE: y = midY - 36 (bottom = midY - 8)
    let yAbove: Float64 = midY - 36.0
    match (searchAtY(yAbove, midX, trayW, trayH, cands, boxes)) {
        case Some(x) => return ToastPlacement(x, yAbove, true, 1, 0.0)
        case None => ()
    }

    // (b) Lift upward in 2u steps, lift=2,4,...,24 (y = midY - 36 - lift)
    var lift: Float64 = 2.0
    while (lift <= 24.0 + 1e-6) {
        let yLift = yAbove - lift
        match (searchAtY(yLift, midX, trayW, trayH, cands, boxes)) {
            case Some(x) => return ToastPlacement(x, yLift, true, 2, lift)
            case None => ()
        }
        lift += 2.0
    }

    // (c) BELOW: y = midY + 8 (top = midY + 8)
    let yBelow: Float64 = midY + 8.0
    match (searchAtY(yBelow, midX, trayW, trayH, cands, boxes)) {
        case Some(x) => return ToastPlacement(x, yBelow, true, 3, 0.0)
        case None => ()
    }

    // (d) If nothing fits: do NOT place toast; report shown=false, step=0, x=midX-43, y=midY-36
    return ToastPlacement(cX, yAbove, false, 0, 0.0)
}
