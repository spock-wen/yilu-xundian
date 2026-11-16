package ohos_app_cangjie_entry

import std.collection.ArrayList

/*
 * Parity reject overlay toast avoidance (designer final ruling).
 * Toast width is given by tw in toastPlaceW: 86 = 4 chars, 100 = 5 chars
 * ("粮重不可进"); height fixed 28, one line. toastPlace keeps tw = 86.
 * All coordinates are tray coordinates in vp (u). E = rejected-edge midpoint (midX, midY).
 * Obstacles = ToastBox list from collectToastObstacles() (walls/route use clear 2.0).
 *
 * Validity of candidate rect (x, y, tw, 28):
 *   - horizontally inside tray with >= 16 from left/right edges: 16 <= x and x + tw <= trayW - 16
 *   - vertically inside tray with >= 8 from top/bottom edges: 8 <= y and y + 28 <= trayH - 8
 *   - for every obstacle box b, clearance >= b.clear: box inflated by b.clear must not overlap rect (walls/route use clear 2.0)
 *
 * Candidate x set: {midX - tw/2, 16, trayW - 16 - tw} plus for each obstacle box b:
 *   b.x0 - b.clear - tw and b.x1 + b.clear
 *
 * Placement order:
 *  (a) ABOVE: y = midY - 36 (bottom = midY - 8). Horizontal shift only, |dx| <= 96 where dx = (x + tw/2) - midX.
 *      Choose valid x with smallest |dx|; on tie LEFT wins ("left first then right"). Centred (dx = 0) is smallest |dx|.
 *  (b) If (a) has no valid x: lift upward in 2u steps, lift = 2, 4, ..., 24 (y = midY - 36 - lift),
 *      same horizontal search (|dx| <= 96); take the SMALLEST lift that has a fit.
 *  (c) If (b) has none: BELOW, y = midY + 8 (top = midY + 8), same horizontal search, |dx| <= 96.
 *  (d) If nothing fits: do NOT place toast; return shown = false, step = 0, x = midX - tw/2, y = midY - 36, lift = 0.
 *      (作废,由 (e) 取代)
 *  (e) FALLBACK: If (a)(b)(c) have no fit (including after pass 2 removing soft boxes):
 *      place toast outside tray, horizontally centred on tray: x = (trayW - tw) / 2.0,
 *      bottom edge 6u above tray top (y = -34.0), shown = true, step = 4, lift = 0.0, relaxed = false.
 *
 * Two-pass placement (soft / relaxed):
 *   Pass 1 runs placeOnce with ALL obstacle boxes. If it finds a valid placement
 *   (shown = true), return it with relaxed = false.
 *   Pass 2 ignores soft boxes (soft = true marks route-polyline boxes only; the
 *   rejected edge, head dot, station points, walls and the 下一驿 label stay
 *   hard). It runs placeOnce with the filtered hard-only boxes and the candidate
 *   x set generated from those filtered boxes. If pass 2 finds a valid
 *   placement, return it with relaxed = true. Clearances are unchanged.
 *   If pass 2 also fails, fallback (e) takes effect.
 */

public struct ToastBox {
    public let x0: Float64
    public let y0: Float64
    public let x1: Float64
    public let y1: Float64
    public let clear: Float64
    public let soft: Bool

    public init(x0: Float64, y0: Float64, x1: Float64, y1: Float64) {
        this(x0, y0, x1, y1, 6.0)
    }

    public init(x0: Float64, y0: Float64, x1: Float64, y1: Float64, clear: Float64) {
        this(x0, y0, x1, y1, clear, false)
    }

    public init(x0: Float64, y0: Float64, x1: Float64, y1: Float64, clear: Float64, soft: Bool) {
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
        this.soft = soft
    }
}

public struct ToastPlacement {
    public let x: Float64
    public let y: Float64
    public let shown: Bool
    public let step: Int64
    public let lift: Float64
    public let relaxed: Bool

    public init(x: Float64, y: Float64, shown: Bool, step: Int64, lift: Float64) {
        this.x = x
        this.y = y
        this.shown = shown
        this.step = step
        this.lift = lift
        this.relaxed = false
    }

    public init(x: Float64, y: Float64, shown: Bool, step: Int64, lift: Float64, relaxed: Bool) {
        this.x = x
        this.y = y
        this.shown = shown
        this.step = step
        this.lift = lift
        this.relaxed = relaxed
    }
}

public func toastIsOutsideTray(p: ToastPlacement): Bool {
    return p.step == 4
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

func isValid(x: Float64, y: Float64, trayW: Float64, trayH: Float64, tw: Float64, boxes: Array<ToastBox>): Bool {
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

func searchAtY(y: Float64, midX: Float64, trayW: Float64, trayH: Float64, tw: Float64, cands: ArrayList<Float64>, boxes: Array<ToastBox>): Option<Float64> {
    var bestX = 0.0
    var bestAbsDx = 1e9
    var bestDx = 0.0
    var found = false

    for (candX in cands) {
        if (isValid(candX, y, trayW, trayH, tw, boxes)) {
            let dx = (candX + tw / 2.0) - midX
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

private func placeOnce(trayW: Float64, trayH: Float64, midX: Float64, midY: Float64, boxes: Array<ToastBox>, tw: Float64): ToastPlacement {
    let cX: Float64 = midX - tw / 2.0
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
    match (searchAtY(yAbove, midX, trayW, trayH, tw, cands, boxes)) {
        case Some(x) => return ToastPlacement(x, yAbove, true, 1, 0.0)
        case None => ()
    }

    // (b) Lift upward in 2u steps, lift=2,4,...,24 (y = midY - 36 - lift)
    var lift: Float64 = 2.0
    while (lift <= 24.0 + 1e-6) {
        let yLift = yAbove - lift
        match (searchAtY(yLift, midX, trayW, trayH, tw, cands, boxes)) {
            case Some(x) => return ToastPlacement(x, yLift, true, 2, lift)
            case None => ()
        }
        lift += 2.0
    }

    // (c) BELOW: y = midY + 8 (top = midY + 8)
    let yBelow: Float64 = midY + 8.0
    match (searchAtY(yBelow, midX, trayW, trayH, tw, cands, boxes)) {
        case Some(x) => return ToastPlacement(x, yBelow, true, 3, 0.0)
        case None => ()
    }

    // (d) If nothing fits: do NOT place toast; report shown=false, step=0, x=midX-43, y=midY-36
    return ToastPlacement(cX, yAbove, false, 0, 0.0)
}

public func toastPlace(trayW: Float64, trayH: Float64, midX: Float64, midY: Float64, boxes: Array<ToastBox>): ToastPlacement {
    return toastPlaceW(trayW, trayH, midX, midY, boxes, 86.0)
}

public func toastPlaceNoFallback(trayW: Float64, trayH: Float64, midX: Float64, midY: Float64, boxes: Array<ToastBox>, tw: Float64): ToastPlacement {
    // Pass 1: all boxes
    let r1 = placeOnce(trayW, trayH, midX, midY, boxes, tw)
    if (r1.shown) {
        return r1
    }

    // Pass 2: hard boxes only (soft == false)
    let hard = ArrayList<ToastBox>()
    for (b in boxes) {
        if (!b.soft) {
            hard.add(b)
        }
    }
    let r2 = placeOnce(trayW, trayH, midX, midY, hard.toArray(), tw)
    if (r2.shown) {
        return ToastPlacement(r2.x, r2.y, true, r2.step, r2.lift, true)
    }

    // Both passes failed; return pass-1 result (shown=false)
    return r1
}

public func toastPlaceW(trayW: Float64, trayH: Float64, midX: Float64, midY: Float64, boxes: Array<ToastBox>, tw: Float64): ToastPlacement {
    let r = toastPlaceNoFallback(trayW, trayH, midX, midY, boxes, tw)
    if (r.shown) {
        return r
    }
    return ToastPlacement((trayW - tw) / 2.0, -34.0, true, 4, 0.0)
}
