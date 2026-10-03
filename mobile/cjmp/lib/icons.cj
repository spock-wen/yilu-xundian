package ohos_app_cangjie_entry

import std.math.*

/*
 * Pure builders for vector icon paths (check circle / check mark / lock icon).
 * Path commands are in device pixels (= vp * f).
 * No ohos dependency.
 */

public func openPolyPathCmds(pts: Array<Float64>, f: Float64): String {
    let sb = StringBuilder()
    var i: Int64 = 0
    while (i + 1 < pts.size) {
        if (i == 0) {
            sb.append("M ${pts[0] * f} ${pts[1] * f}")
        } else {
            sb.append(" L ${pts[i] * f} ${pts[i + 1] * f}")
        }
        i = i + 2
    }
    return sb.toString()
}

/* 1. celadon ✓ 圆: 颜色 Theme.success(#5E7A6A)。
 * 返回 2 个 BoardPath:
 * a) 圆环: ellipsePathCmds(cx, cy, r - 0.8, r - 0.8, f), stroke 1.6, fillOp 0.0;
 * b) 对勾: 3点 (-0.34r, +0.02r) -> (-0.08r, +0.28r) -> (+0.36r, -0.24r),
 *    用两段线段 segsPathCmds 生成, stroke 1.6, fillOp 0.0。
 */
public func checkCircleIconPaths(cx: Float64, cy: Float64, r: Float64, f: Float64): Array<BoardPath> {
    let circleCmds = ellipsePathCmds(cx, cy, r - 0.8, r - 0.8, f)
    let p0x = cx - 0.34 * r
    let p0y = cy + 0.02 * r
    let p1x = cx - 0.08 * r
    let p1y = cy + 0.28 * r
    let p2x = cx + 0.36 * r
    let p2y = cy - 0.24 * r
    let checkSegs = [p0x, p0y, p1x, p1y, p1x, p1y, p2x, p2y]
    let checkCmds = segsPathCmds(checkSegs, f)

    return [
        BoardPath(circleCmds, Theme.success, 1.6, stroke: Theme.success, fillOp: 0.0),
        BoardPath(checkCmds, Theme.success, 1.6, stroke: Theme.success, fillOp: 0.0)
    ]
}

/* 2. 仅对勾(无圆), 宽 w (用于分组头里 12u 宽的 ✓, 1.6 线, success 色):
 * 三点 (-0.5w, +0.0w) -> (-0.12w, +0.38w) -> (+0.5w, -0.34w) 相对 (cx, cy),
 * 一个 BoardPath。
 */
public func checkMarkIconPaths(cx: Float64, cy: Float64, w: Float64, f: Float64): Array<BoardPath> {
    let p0x = cx - 0.5 * w
    let p0y = cy + 0.0 * w
    let p1x = cx - 0.12 * w
    let p1y = cy + 0.38 * w
    let p2x = cx + 0.5 * w
    let p2y = cy - 0.34 * w
    let checkSegs = [p0x, p0y, p1x, p1y, p1x, p1y, p2x, p2y]
    let cmds = segsPathCmds(checkSegs, f)

    return [
        BoardPath(cmds, Theme.success, 1.6, stroke: Theme.success, fillOp: 0.0)
    ]
}

/* 3. 锁图标含描边外框 (宽, 高) = (16.0 * k, 20.0 * k), 供布局和测试。 */
public func lockIconBox(k: Float64): (Float64, Float64) {
    return (16.0 * k, 20.0 * k)
}

/* 小锁图标: k 为缩放(设计要求 0.62 倍, 线宽 1.6*k 但不小于 1.0), color 传 Theme.locked 等。
 * 几何(k=1 基准, 相对 (cx, cy)):
 * 锁体: x in [-8, 8], y in [-1, 10], 4 角各切 1.5 的八边形, polyPathCmds 绘制, fillOp 0.0;
 * 锁梁: 从 (-5, -1) 向上到 (-5, -5), 半圆(8段线段折线近似, 圆心 (0, -5) 半径 5)
 * 到 (5, -5), 再向下到 (5, -1); 全部 * k。锁梁 BoardPath 只描边 fillOp 0.0。
 * 所有点落在 lockIconBox 外框 [cx±8k, cy-10k..cy+10k] 内。
 */
public func lockIconPaths(cx: Float64, cy: Float64, k: Float64, color: Int64, f: Float64): Array<BoardPath> {
    let sw = if (1.6 * k < 1.0) { 1.0 } else { 1.6 * k }

    // 锁体: 4角各切 1.5 的八边形 (k=1: x in [-8,8], y in [-1,10])
    let bodyPts: Array<Float64> = [
        cx - 6.5 * k, cy - 1.0 * k,
        cx + 6.5 * k, cy - 1.0 * k,
        cx + 8.0 * k, cy + 0.5 * k,
        cx + 8.0 * k, cy + 8.5 * k,
        cx + 6.5 * k, cy + 10.0 * k,
        cx - 6.5 * k, cy + 10.0 * k,
        cx - 8.0 * k, cy + 8.5 * k,
        cx - 8.0 * k, cy + 0.5 * k
    ]
    let bodyCmds = polyPathCmds(bodyPts, f)
    let bodyPath = BoardPath(bodyCmds, color, sw, stroke: color, fillOp: 0.0)

    // 锁梁: (-5,-1) -> (-5,-5) -> 8段半圆到 (5,-5) -> (5,-1)
    // 半圆中心 (cx, cy - 5*k), 半径 5*k.
    // 角度从 180° 到 0° (屏幕坐标 y 向下: y = cy - 5*k - 5*k * sin(theta))
    // 8 段共 9 点, 每步 22.5°
    let shacklePts: Array<Float64> = [
        cx - 5.0 * k, cy - 1.0 * k,
        cx - 5.0 * k, cy - 5.0 * k,
        cx - 4.6193976626 * k, cy - 6.9134171618 * k,
        cx - 3.5355339059 * k, cy - 8.5355339059 * k,
        cx - 1.9134171618 * k, cy - 9.6193976626 * k,
        cx + 0.0 * k, cy - 10.0 * k,
        cx + 1.9134171618 * k, cy - 9.6193976626 * k,
        cx + 3.5355339059 * k, cy - 8.5355339059 * k,
        cx + 4.6193976626 * k, cy - 6.9134171618 * k,
        cx + 5.0 * k, cy - 5.0 * k,
        cx + 5.0 * k, cy - 1.0 * k
    ]
    let shackleCmds = openPolyPathCmds(shacklePts, f)
    let shacklePath = BoardPath(shackleCmds, color, sw, stroke: color, fillOp: 0.0)

    return [bodyPath, shacklePath]
}
