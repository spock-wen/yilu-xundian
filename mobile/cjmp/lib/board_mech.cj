package ohos_app_cangjie_entry

import std.math.*
import std.collection.ArrayList
import ohos_app_cangjie_entry.engine.Cell
import ohos_app_cangjie_entry.game.{PatrolGame, LevelDef, REJECT_PARITY, REJECT_ONE_WAY, REJECT_SEALED_GATE, REJECT_BURDEN_FORBIDDEN, REJECT_FERRY}

/*
 * Pure builders for mechanic board pieces (slide / seal gates / one-way gates /
 * collapse edge / token & forbidden cells). No ohos dependency.
 */

public func isSlideCellOf(level: LevelDef, x: Int64, y: Int64): Bool {
    for (c in level.slideCells) {
        if (c.x == x && c.y == y) {
            return true
        }
    }
    return false
}

public func mechCellFill(game: PatrolGame, x: Int64, y: Int64, base: Int64): Int64 {
    if (!game.level.hasMechanics()) {
        return base
    }
    if (isSlideCellOf(game.level, x, y)) {
        return Theme.ze
    }
    if (game.level.isTokenCell(x, y) && game.path.contains(Cell(x, y))) {
        return Theme.path
    }
    if (game.level.isForbiddenCell(x, y)) {
        return Theme.paperShade
    }
    return base
}

public func mechCellStroke(game: PatrolGame, x: Int64, y: Int64): Int64 {
    if (game.level.hasMechanics() && game.level.isForbiddenCell(x, y)) {
        return Theme.inkMuted
    }
    return Theme.paperLine
}

public func mechCellStrokeW(game: PatrolGame, x: Int64, y: Int64): Float64 {
    if (game.level.hasMechanics() && game.level.isForbiddenCell(x, y)) {
        return 1.5
    }
    return 1.0
}

public func seamBarOff(geom: BoardGeom, ax: Int64, ay: Int64, bx: Int64, by: Int64, half: Float64, off: Float64, color: Int64, width: Float64): BoardSeg {
    let (mx, my) = geom.seamMid(ax, ay, bx, by)
    if (ay == by) {
        /* 左右相邻 → 竖缝：沿 y 方向的短横杆 */
        return BoardSeg(mx + off, my - half, mx + off, my + half, color, width)
    }
    /* 上下相邻 → 横缝：沿 x 方向的短横杆 */
    return BoardSeg(mx - half, my + off, mx + half, my + off, color, width)
}

public func buildBoardMechWalls(game: PatrolGame, geom: BoardGeom): Array<BoardSeg> {
    if (!game.level.hasMechanics()) {
        return Array<BoardSeg>()
    }
    let list = ArrayList<BoardSeg>()
    match (game.level.collapse) {
        case Some(cd) =>
            if (game.isEdgeCollapsed(cd.x1, cd.y1, cd.x2, cd.y2)) {
                /* 塌桥占位：沿用墙样式 */
                list.add(seamBarOff(geom, cd.x1, cd.y1, cd.x2, cd.y2, 10.0, 0.0, Theme.ink, 4.0))
            }
        case None => ()
    }
    for (g in game.level.sealGates) {
        if (!game.hasToken) {
            /* 闸未开：粗闸条 */
            list.add(seamBarOff(geom, g.x1, g.y1, g.x2, g.y2, 12.0, 0.0, Theme.qingDeep, 6.0))
        } else {
            /* 已开：两条细线分列两侧 */
            list.add(seamBarOff(geom, g.x1, g.y1, g.x2, g.y2, 12.0, -2.5, Theme.qing, 1.2))
            list.add(seamBarOff(geom, g.x1, g.y1, g.x2, g.y2, 12.0, 2.5, Theme.qing, 1.2))
        }
    }
    return list.toArray()
}

public func buildBoardGates(game: PatrolGame, geom: BoardGeom): Array<BoardImg> {
    if (game.level.oneWays.size == 0) {
        return Array<BoardImg>()
    }
    let list = ArrayList<BoardImg>()
    for (ow in game.level.oneWays) {
        list.add(rejectGateImg(geom, ow.fromX, ow.fromY, ow.toX, ow.toY))
    }
    return list.toArray()
}

/* J13:单向门切片几何(idle 与 reject 共用):缝中点、len=0.72c、thick=len*27/60,
   左右相邻(fromY==toY)竖放 vertical=true,否则横放。 */
public func rejectGateImg(geom: BoardGeom, fromX: Int64, fromY: Int64, toX: Int64, toY: Int64): BoardImg {
    let (mx, my) = geom.seamMid(fromX, fromY, toX, toY)
    let len = 0.72 * geom.c
    let thick = len * 27.0 / 60.0
    if (fromY == toY) {
        return BoardImg(mx - thick * 0.5, my - len * 0.5, thick, len, true)
    }
    return BoardImg(mx - len * 0.5, my - thick * 0.5, len, thick, false)
}

func centerLabel(cx: Float64, cy: Float64, size: Float64, text: String, color: Int64): BoardLabel {
    return BoardLabel(cx - size * 0.5, cy - 0.53 * size, size * 3.0, size * 1.5, text, color, size)
}

public func buildBoardMechLabels(game: PatrolGame, geom: BoardGeom): Array<BoardLabel> {
    if (!game.level.hasMechanics()) {
        return Array<BoardLabel>()
    }
    let list = ArrayList<BoardLabel>()
    let c = geom.c
    match (game.level.ferry) {
        case Some(f) =>
            let jx = geom.centerX(f.jiaX)
            let jy = geom.centerY(f.jiaY)
            let yx = geom.centerX(f.yiX)
            let yy = geom.centerY(f.yiY)
            if (game.level.numberAt(f.jiaX, f.jiaY) != 0) {
                list.add(BoardLabel(geom.cellX(f.jiaX) + 0.08 * c, geom.cellY(f.jiaY) + 0.06 * c, c, 0.2 * c * 1.5, "甲", Theme.qingDeep, 0.2 * c))
            } else {
                list.add(centerLabel(jx, jy, 0.30 * c, "甲", Theme.qingDeep))
            }
            if (game.level.numberAt(f.yiX, f.yiY) != 0) {
                list.add(BoardLabel(geom.cellX(f.yiX) + 0.08 * c, geom.cellY(f.yiY) + 0.06 * c, c, 0.2 * c * 1.5, "乙", Theme.qingDeep, 0.2 * c))
            } else {
                list.add(centerLabel(yx, yy, 0.30 * c, "乙", Theme.qingDeep))
            }
            list.add(centerLabel((jx + yx) * 0.5, (jy + yy) * 0.5, 0.24 * c, "渡", Theme.qing))
        case None => ()
    }
    if (game.hasToken) {
        for (g in game.level.sealGates) {
            let (mx, my) = geom.seamMid(g.x1, g.y1, g.x2, g.y2)
            list.add(centerLabel(mx, my, 0.24 * c, "开", Theme.qing))
        }
    }
    for (t in game.level.tokenCells) {
        let visited = game.path.contains(Cell(t.x, t.y))
        let color = if (visited) { Theme.whitePaper } else { Theme.ink }
        list.add(centerLabel(geom.centerX(t.x), geom.centerY(t.y), 0.34 * c, "符", color))
    }
    for (s in game.level.slideCells) {
        /* 官方稿:块笔约 11.3vp,字号 12.2vp(字形占字号≈0.93),墨色。 */
        list.add(BoardLabel(geom.cellX(s.x) + 0.08 * c, geom.cellY(s.y) + 0.06 * c, c, 12.2 * 1.5, "滑", Theme.ink, 12.2))
        var idx: Int64 = -1
        var i: Int64 = 0
        while (i < game.path.size()) {
            let p = game.path.at(i)
            if (p.x == s.x && p.y == s.y) {
                idx = i
                break
            }
            i = i + 1
        }
        if (idx >= 1) {
            let prev = game.path.at(idx - 1)
            let dx = s.x - prev.x
            let dy = s.y - prev.y
            let adx = if (dx < 0) { -dx } else { dx }
            let ady = if (dy < 0) { -dy } else { dy }
            if (adx + ady == 1) {
                var continues = false
                if (idx + 1 < game.path.size()) {
                    let nx = game.path.at(idx + 1)
                    if (nx.x == s.x + dx && nx.y == s.y + dy && isSlideCellOf(game.level, nx.x, nx.y)) {
                        continues = true
                    }
                }
                if (!continues) {
                    list.add(BoardLabel(geom.cellX(s.x) + 0.60 * c, geom.cellY(s.y) + 0.72 * c, c, 0.3 * c, "停", Theme.inkMuted, 0.2 * c))
                }
            }
        }
    }
    return list.toArray()
}

public func buildBoardMechDots(game: PatrolGame, geom: BoardGeom): Array<BoardDot> {
    let list = ArrayList<BoardDot>()
    match (game.level.ferry) {
        case Some(f) =>
            let jx = geom.centerX(f.jiaX)
            let jy = geom.centerY(f.jiaY)
            list.add(BoardDot(jx, jy, 0.38 * geom.c, 0x01000000, Theme.qingDeep, 1.5, true))
            list.add(BoardDot(jx, jy, 0.30 * geom.c, 0x01000000, Theme.qingDeep, 1.0, true))
            let yx = geom.centerX(f.yiX)
            let yy = geom.centerY(f.yiY)
            list.add(BoardDot(yx, yy, 0.38 * geom.c, 0x01000000, Theme.qingDeep, 1.5, true))
            list.add(BoardDot(yx, yy, 0.30 * geom.c, 0x01000000, Theme.qingDeep, 1.0, true))
        case None => ()
    }
    return list.toArray()
}

/* 沿 ax,ay→bx,by 画 2vp 实 / 7vp 空虚线；坐标 ×f 转设备像素。 */
func dashSub(sb: StringBuilder, ax: Float64, ay: Float64, bx: Float64, by: Float64, f: Float64): Unit {
    let dx = bx - ax
    let dy = by - ay
    let L = sqrt(dx * dx + dy * dy)
    if (L <= 0.0) {
        return
    }
    let ux = dx / L
    let uy = dy / L
    var t = 0.0
    while (t < L) {
        let t2 = if (t + 2.0 < L) { t + 2.0 } else { L }
        if (sb.size > 0) {
            sb.append(" ")
        }
        sb.append("M ${(ax + ux * t) * f} ${(ay + uy * t) * f} L ${(ax + ux * t2) * f} ${(ay + uy * t2) * f}")
        t = t + 9.0
    }
}

public func buildBoardMechPaths(game: PatrolGame, geom: BoardGeom, pxPerVp: Float64): Array<BoardPath> {
    if (!game.level.hasMechanics()) {
        return Array<BoardPath>()
    }
    let list = ArrayList<BoardPath>()
    let c = geom.c
    let f = if (pxPerVp <= 0.0) { 3.0 } else { pxPerVp }
    /* a. 锁：未开的闸在缝中点画一把挂锁（矩身 + 锁梁）。 */
    if (!game.hasToken) {
        for (g in game.level.sealGates) {
            let (mx, my) = geom.seamMid(g.x1, g.y1, g.x2, g.y2)
            let bw = 0.28 * c
            let bh = 0.22 * c
            let x0 = mx - bw * 0.5
            let x1 = mx + bw * 0.5
            let y0 = my - 0.06 * c
            let y1 = y0 + bh
            let xl = mx - 0.09 * c
            let xr = mx + 0.09 * c
            let ys = y0 - 0.05 * c
            let yt = y0 - 0.14 * c
            let sbL = StringBuilder()
            sbL.append("M ${x0 * f} ${y0 * f} L ${x1 * f} ${y0 * f} L ${x1 * f} ${y1 * f} L ${x0 * f} ${y1 * f} Z")
            sbL.append(" M ${xl * f} ${y0 * f} L ${xl * f} ${ys * f} Q ${xl * f} ${yt * f} ${mx * f} ${yt * f} Q ${xr * f} ${yt * f} ${xr * f} ${ys * f} L ${xr * f} ${y0 * f}")
            list.add(BoardPath(sbL.toString(), Theme.whitePaper, 1.3, stroke: Theme.ink, fillOp: 1.0))
        }
    }
    /* b. 符格金框：所有 tokenCells 合并成一个 BoardPath（双层 0.10c/0.17c 内缩矩形）。 */
    if (game.level.tokenCells.size > 0) {
        let sbT = StringBuilder()
        for (t in game.level.tokenCells) {
            for (ins in [0.10 * c, 0.17 * c]) {
                let xa = geom.cellX(t.x) + ins
                let ya = geom.cellY(t.y) + ins
                let xb = geom.cellX(t.x) + c - ins
                let yb = geom.cellY(t.y) + c - ins
                if (sbT.size > 0) {
                    sbT.append(" ")
                }
                sbT.append("M ${xa * f} ${ya * f} L ${xb * f} ${ya * f} L ${xb * f} ${yb * f} L ${xa * f} ${yb * f} Z")
            }
        }
        list.add(BoardPath(sbT.toString(), Theme.gold, 1.2, stroke: Theme.gold, fillOp: 0.0))
    }
    /* c. 滑行 chevron：路径上每个泽地格（从相邻前格滑入）画一个指向滑行方向的箭头，合并成一个 BoardPath。 */
    let sbV = StringBuilder()
    var i: Int64 = 1
    while (i < game.path.size()) {
        let cell = game.path.at(i)
        if (isSlideCellOf(game.level, cell.x, cell.y)) {
            let prev = game.path.at(i - 1)
            let dx = cell.x - prev.x
            let dy = cell.y - prev.y
            let adx = if (dx < 0) { -dx } else { dx }
            let ady = if (dy < 0) { -dy } else { dy }
            if (adx + ady == 1) {
                let cx = geom.centerX(cell.x)
                let cy = geom.centerY(cell.y)
                let fdx = Float64(dx)
                let fdy = Float64(dy)
                let perpx = -fdy
                let perpy = fdx
                /* 官方稿 hard-fx 41/44 实心青深 chevron:局部坐标(前进向右,原点=包围盒左上)
                   P1=(1.8,1.8)→顶点 P2=(16.5,12.35)→P3=(1.8,22.9),开放折线,圆端点外接盒
                   恰为 18.3(前进)×24.7(垂直)vp;包围盒中心=格心沿前进方向前移 2.2vp。
                   点=center+f*(u-9.15+2.2)+perp*(v-12.35);常量为 vp 绝对值,不随 c 缩放。 */
                let p1x = cx + fdx * (1.8 - 9.15 + 2.2) + perpx * (1.8 - 12.35)
                let p1y = cy + fdy * (1.8 - 9.15 + 2.2) + perpy * (1.8 - 12.35)
                let p2x = cx + fdx * (16.5 - 9.15 + 2.2) + perpx * (12.35 - 12.35)
                let p2y = cy + fdy * (16.5 - 9.15 + 2.2) + perpy * (12.35 - 12.35)
                let p3x = cx + fdx * (1.8 - 9.15 + 2.2) + perpx * (22.9 - 12.35)
                let p3y = cy + fdy * (1.8 - 9.15 + 2.2) + perpy * (22.9 - 12.35)
                if (sbV.size > 0) {
                    sbV.append(" ")
                }
                sbV.append("M ${p1x * f} ${p1y * f} L ${p2x * f} ${p2y * f} L ${p3x * f} ${p3y * f}")
            }
        }
        i = i + 1
    }
    if (sbV.size > 0) {
        /* 实心青深 chevron:描边折线,线宽 3.6vp,fillOp 0(视觉由粗描边构成)。 */
        list.add(BoardPath(sbV.toString(), Theme.qingDeep, 3.6, stroke: Theme.qingDeep, fillOp: 0.0))
    }
    /* d. 渡口虚线：甲乙圆点间断开圆环的虚线连线；路径走过 甲→乙 则用深色加粗。 */
    match (game.level.ferry) {
        case Some(fr) =>
            let jx = geom.centerX(fr.jiaX)
            let jy = geom.centerY(fr.jiaY)
            let yx = geom.centerX(fr.yiX)
            let yy = geom.centerY(fr.yiY)
            let dx = yx - jx
            let dy = yy - jy
            let L = sqrt(dx * dx + dy * dy)
            if (L > 0.0) {
                let ux = dx / L
                let uy = dy / L
                let r = 0.38 * c + 1.0
                let g = 0.16 * c
                if (L > 2.0 * r + 2.0 * g) {
                    let sx = jx + ux * r
                    let sy = jy + uy * r
                    let ex = yx - ux * r
                    let ey = yy - uy * r
                    let mx = (sx + ex) * 0.5
                    let my = (sy + ey) * 0.5
                    let sbF = StringBuilder()
                    dashSub(sbF, sx, sy, mx - ux * g, my - uy * g, f)
                    dashSub(sbF, mx + ux * g, my + uy * g, ex, ey, f)
                    if (sbF.size > 0) {
                        var traversed = false
                        var ji: Int64 = -1
                        var pi: Int64 = 0
                        while (pi < game.path.size()) {
                            let pc = game.path.at(pi)
                            if (pc.x == fr.jiaX && pc.y == fr.jiaY) {
                                ji = pi
                                break
                            }
                            pi = pi + 1
                        }
                        if (ji >= 0 && ji + 1 < game.path.size()) {
                            let nc = game.path.at(ji + 1)
                            if (nc.x == fr.yiX && nc.y == fr.yiY) {
                                traversed = true
                            }
                        }
                        if (traversed) {
                            list.add(BoardPath(sbF.toString(), Theme.path, 2.5, stroke: Theme.path, fillOp: 0.0))
                        } else {
                            list.add(BoardPath(sbF.toString(), Theme.qing, 1.5, stroke: Theme.qing, fillOp: 0.0))
                        }
                    }
                }
            }
        case None => ()
    }
    return list.toArray()
}

/* 该次拒绝是否应当在 from→to 这条边上闪烁提示。
   仅机制类拒绝（奇偶/单向/闸门/负禁/进甲）且 from/to 都有效并曼哈顿相邻才闪；
   WALL/VISITED/WAYPOINT/BOUNDS/START 与塌桥断边不闪。 */
public func rejectShouldFlash(game: PatrolGame): Bool {
    let code = game.lastReject
    if (code != REJECT_PARITY && code != REJECT_ONE_WAY && code != REJECT_SEALED_GATE
        && code != REJECT_BURDEN_FORBIDDEN && code != REJECT_FERRY) {
        return false
    }
    if (game.lastRejectFromX < 0 || game.lastRejectFromY < 0
        || game.lastRejectToX < 0 || game.lastRejectToY < 0) {
        return false
    }
    let dx = game.lastRejectToX - game.lastRejectFromX
    let dy = game.lastRejectToY - game.lastRejectFromY
    var ax = dx
    if (ax < 0) {
        ax = -ax
    }
    var ay = dy
    if (ay < 0) {
        ay = -ay
    }
    return ax + ay == 1
}

/* 奇偶拒绝的 toast 文案；非奇偶拒绝返回 ""。 */
public func parityToastText(game: PatrolGame): String {
    if (game.lastRejectParity == 1) {
        return "此步须奇"
    }
    if (game.lastRejectParity == 2) {
        return "此步须偶"
    }
    return ""
}
