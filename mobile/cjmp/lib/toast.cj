package ohos_app_cangjie_entry

import std.collection.ArrayList

/*
 * U3: Parity reject overlay toast avoidance (designer ruling).
 * Toast is 86 wide x 28 high vp, one line.
 * All coordinates are tray coordinates in vp. E = rejected-edge midpoint (midX, midY).
 * Obstacles = ToastBox list from collectToastObstacles().
 * Candidate toast rect R is VALID if:
 *   - clearance >= 6 from every obstacle box (box inflated by 6 on both axes must not overlap R),
 *   - horizontally inside tray with >= 16 from both tray edges: 16 <= x and x + 86 <= trayW - 16,
 *   - vertically inside tray with >= 16 from both tray edges: 16 <= y and y + 28 <= trayH - 16.
 *
 * Placement order:
 *  1. CENTRED: x = midX - 43, ABOVE: y = midY - 36 (bottom edge 8 above E). If valid, use it.
 *  2. ABOVE with horizontal shift, |dx| <= 72 where dx = (x + 43) - midX, y = midY - 36.
 *     LEFT first: among valid candidates with dx < 0 and dx >= -72 pick smallest |dx|;
 *     if none, RIGHT: among valid candidates with dx > 0 and dx <= 72 pick smallest dx.
 *  3. If nothing valid in step 2: BELOW: y = midY + 8 (top edge 8 under E), same horizontal
 *     search (centred first, then left-first-then-right, |dx| <= 72, same validity).
 *  4. Only if steps 1-3 all fail: go beyond 72 ABOVE (y = midY - 36): choose the valid x
 *     with smallest |dx| (left wins ties). If even that has no valid x above, try the same
 *     BELOW. If still nothing, return centred-above clamped x into [16, trayW-16-86].
 *     In cases 4 the result is flagged with fallback = true.
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

public struct ToastPlacement {
    public let x: Float64
    public let y: Float64
    public let above: Bool
    public let fallback: Bool

    public init(x: Float64, y: Float64, above: Bool, fallback: Bool) {
        this.x = x
        this.y = y
        this.above = above
        this.fallback = fallback
    }
}

public func isBlocking(box: ToastBox, x: Float64, tw: Float64, top: Float64, bottom: Float64): Bool {
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

func isValid(x: Float64, y: Float64, trayW: Float64, trayH: Float64, boxes: Array<ToastBox>): Bool {
    let tw: Float64 = 86.0
    let th: Float64 = 28.0
    if (y < 16.0 - 1e-6 || y + th > trayH - 16.0 + 1e-6) {
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

func searchWithin72(y: Float64, midX: Float64, trayW: Float64, trayH: Float64, cands: ArrayList<Float64>, boxes: Array<ToastBox>): Option<Float64> {
    let cX = midX - 43.0
    // Centred first
    if (isValid(cX, y, trayW, trayH, boxes)) {
        return Some(cX)
    }

    // LEFT first: dx < 0 and dx >= -72, pick smallest |dx| (largest dx)
    var bestLeftX = 0.0
    var bestLeftDx = -1e9
    var foundLeft = false

    // RIGHT: dx > 0 and dx <= 72, pick smallest dx
    var bestRightX = 0.0
    var bestRightDx = 1e9
    var foundRight = false

    for (candX in cands) {
        if (isValid(candX, y, trayW, trayH, boxes)) {
            let dx = (candX + 43.0) - midX
            if (dx < -1e-6 && dx >= -72.0 - 1e-6) {
                if (!foundLeft || dx > bestLeftDx) {
                    bestLeftDx = dx
                    bestLeftX = candX
                    foundLeft = true
                }
            } else if (dx > 1e-6 && dx <= 72.0 + 1e-6) {
                if (!foundRight || dx < bestRightDx) {
                    bestRightDx = dx
                    bestRightX = candX
                    foundRight = true
                }
            }
        }
    }

    if (foundLeft) {
        return Some(bestLeftX)
    }
    if (foundRight) {
        return Some(bestRightX)
    }
    return None
}

func searchBeyond(y: Float64, midX: Float64, trayW: Float64, trayH: Float64, cands: ArrayList<Float64>, boxes: Array<ToastBox>): Option<Float64> {
    var bestX = 0.0
    var bestAbsDx = 1e9
    var bestDx = 0.0
    var found = false

    for (candX in cands) {
        if (isValid(candX, y, trayW, trayH, boxes)) {
            let dx = (candX + 43.0) - midX
            let adx = absVal(dx)
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
                // Tie: left wins (smaller dx wins)
                if (dx < bestDx) {
                    bestX = candX
                    bestAbsDx = adx
                    bestDx = dx
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
    let yAbove: Float64 = midY - 36.0
    let yBelow: Float64 = midY + 8.0

    // Deterministic candidate x generation
    let cands = ArrayList<Float64>()
    cands.add(cX)
    cands.add(minX)
    cands.add(maxX)
    for (b in boxes) {
        cands.add(b.x0 - 6.0 - tw)
        cands.add(b.x1 + 6.0)
    }

    // Steps 1 & 2: ABOVE (|dx| <= 72, centred first, then left-first-then-right)
    match (searchWithin72(yAbove, midX, trayW, trayH, cands, boxes)) {
        case Some(x) => return ToastPlacement(x, yAbove, true, false)
        case None => ()
    }

    // Step 3: BELOW (|dx| <= 72, centred first, then left-first-then-right)
    match (searchWithin72(yBelow, midX, trayW, trayH, cands, boxes)) {
        case Some(x) => return ToastPlacement(x, yBelow, false, false)
        case None => ()
    }

    // Step 4: Beyond 72 (fallback = true)
    // 4a. Above beyond 72 (smallest |dx|, left wins ties)
    match (searchBeyond(yAbove, midX, trayW, trayH, cands, boxes)) {
        case Some(x) => return ToastPlacement(x, yAbove, true, true)
        case None => ()
    }

    // 4b. Below beyond 72 (smallest |dx|, left wins ties)
    match (searchBeyond(yBelow, midX, trayW, trayH, cands, boxes)) {
        case Some(x) => return ToastPlacement(x, yBelow, false, true)
        case None => ()
    }

    // 4c. Centred-above clamped into [16, trayW - 16 - 86]
    var clampX = cX
    if (clampX < minX) {
        clampX = minX
    }
    if (clampX > maxX) {
        clampX = maxX
    }
    return ToastPlacement(clampX, yAbove, true, true)
}
