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

/* J14:滑行 chevron 折线三点(格心 cx,cy,格宽 c,入向单位向量 dx,dy)。
   k=c/36.3:dep=18k、h=25k;入向左/上时中心沿入向整体偏 0.16c,
   避让右下「滑」角标(SLIDE_CELL_RULINGS_20261002 §2)。
   返回 [arm1x,arm1y,tipx,tipy,arm2x,arm2y](vp,未乘 pxPerVp)。 */
public func slideChevronPts(cx: Float64, cy: Float64, c: Float64, dx: Int64, dy: Int64): Array<Float64> {
    let k = c / 36.3
    let dep = 18.0 * k
    let h = 25.0 * k
    let fdx = Float64(dx)
    let fdy = Float64(dy)
    let perpx = -fdy
    let perpy = fdx
    let shift = if (dx < 0 || dy < 0) { 0.16 * c } else { 0.0 }
    let cenx = cx + fdx * shift
    let ceny = cy + fdy * shift
    let tipx = cenx + fdx * dep * 0.5
    let tipy = ceny + fdy * dep * 0.5
    let basex = tipx - fdx * dep
    let basey = tipy - fdy * dep
    return [basex + perpx * h * 0.5, basey + perpy * h * 0.5,
        tipx, tipy,
        basex - perpx * h * 0.5, basey - perpy * h * 0.5]
}

/* J14:「滑」块笔角标矩形(格局部坐标,原点=格左上,已含右下偏移 ox,oy)。
   k=c/36.3:gw=11k、gh=12k、距右 2k、距下 1k、笔画 s=max(2,3.4k)。
   返回 [x0,y0,x1,y1]*7,与 render_slide_cell_spec.py 的 hua() 一致(以脚本为准)。 */
public func slideHuaRects(c: Float64): Array<Float64> {
    let k = c / 36.3
    let gw = 11.0 * k
    let gh = 12.0 * k
    let ox = c - gw - 2.0 * k
    let oy = c - gh - 1.0 * k
    var s = 3.4 * k
    if (s < 2.0) {
        s = 2.0
    }
    let m = 0.42 * gh
    let by = 0.78 * gh
    let rects = ArrayList<Float64>()
    /* 顶横、竖干、中横 */
    rects.add(ox)
    rects.add(oy)
    rects.add(ox + gw)
    rects.add(oy + s)
    rects.add(ox + gw / 2.0 - s / 2.0)
    rects.add(oy)
    rects.add(ox + gw / 2.0 + s / 2.0)
    rects.add(oy + 0.72 * gh)
    rects.add(ox + 1.0 * k)
    rects.add(oy + m)
    rects.add(ox + gw - 1.0 * k)
    rects.add(oy + m + s)
    /* 三个下短横 */
    var i: Int64 = 0
    while (i < 3) {
        let x0 = 1.0 * k + 3.0 * k * Float64(i)
        rects.add(ox + x0)
        rects.add(oy + by)
        rects.add(ox + x0 + 2.0 * k)
        rects.add(oy + by + s)
        i = i + 1
    }
    /* 右钩 */
    rects.add(ox + gw - s)
    rects.add(oy + 0.35 * gh)
    rects.add(ox + gw)
    rects.add(oy + gh)
    return rects.toArray()
}

/* J14:路径 idx 处的滑行格是否为「停」末格:idx>=1、前格相邻(曼哈顿 1)、
   且路径下一格不是同方向继续的滑行格(或已到路径末尾)。原「停」Text 判据。 */
public func isSlideStopIndex(game: PatrolGame, idx: Int64): Bool {
    if (idx < 1 || idx >= game.path.size()) {
        return false
    }
    let cell = game.path.at(idx)
    if (!isSlideCellOf(game.level, cell.x, cell.y)) {
        return false
    }
    let prev = game.path.at(idx - 1)
    let dx = cell.x - prev.x
    let dy = cell.y - prev.y
    var adx = dx
    if (adx < 0) {
        adx = -adx
    }
    var ady = dy
    if (ady < 0) {
        ady = -ady
    }
    if (adx + ady != 1) {
        return false
    }
    if (idx + 1 >= game.path.size()) {
        return true
    }
    let nx = game.path.at(idx + 1)
    if (nx.x == cell.x + dx && nx.y == cell.y + dy && isSlideCellOf(game.level, nx.x, nx.y)) {
        return false
    }
    return true
}

/* J17:整圆 path 命令:4 段三次贝塞尔(kappa=0.5522847498)拼成闭合
   M…C…C…C…C…Z,坐标 ×f(pxPerVp)。「停」环外圈/孔共用。 */
public func circlePathCmds(cx: Float64, cy: Float64, r: Float64, f: Float64): String {
    let kr = 0.5522847498 * r
    let x0 = (cx - r) * f
    let x1 = cx * f
    let y1 = (cy - r) * f
    let x2 = (cx + r) * f
    let y3 = (cy + r) * f
    let kx = kr * f
    let sb = StringBuilder()
    sb.append("M ${x0} ${cy * f} C ${x0} ${(cy - kr) * f} ${x1 - kx} ${y1} ${x1} ${y1}")
    sb.append(" C ${x1 + kx} ${y1} ${x2} ${(cy - kr) * f} ${x2} ${cy * f}")
    sb.append(" C ${x2} ${(cy + kr) * f} ${x1 + kx} ${y3} ${x1} ${y3}")
    sb.append(" C ${x1 - kx} ${y3} ${x0} ${(cy + kr) * f} ${x0} ${cy * f} Z")
    return sb.toString()
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
    /* J14:「滑」角标与「停」环都改为 buildBoardMechPaths 的 fill-only
       路径(见 c1/c3),不再出 Text。 */
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
    /* J17:停环挪到 buildBoardMechPaths(chevron 之后),dots 层只回渡口 4 个。 */
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
    /* c1. 「滑」角标:每个滑行格(无论是否已入路径)右下的 draw_hua_block 块笔,
       墨色 fill-only,合并成一个 BoardPath(几何见 slideHuaRects,ruling §3)。 */
    if (game.level.slideCells.size > 0) {
        let sbH = StringBuilder()
        let rects = slideHuaRects(c)
        for (s in game.level.slideCells) {
            let bx = geom.cellX(s.x)
            let by = geom.cellY(s.y)
            var r: Int64 = 0
            while (r + 3 < rects.size) {
                if (sbH.size > 0) {
                    sbH.append(" ")
                }
                sbH.append("M ${(bx + rects[r]) * f} ${(by + rects[r + 1]) * f} L ${(bx + rects[r + 2]) * f} ${(by + rects[r + 1]) * f} L ${(bx + rects[r + 2]) * f} ${(by + rects[r + 3]) * f} L ${(bx + rects[r]) * f} ${(by + rects[r + 3]) * f} Z")
                r = r + 4
            }
        }
        list.add(BoardPath(sbH.toString(), Theme.ink, 0.0, stroke: Theme.ink, fillOp: 1.0))
    }
    /* c2. 滑行 chevron:路径上每个从相邻前格滑入的滑行格画一个指向滑行方向的
       实心青深箭头,k=c/36.3(dep=18k、h=25k、sw=max(3,4k)),合并成一个
       BoardPath;圆头线端由 index.cj Layer 的 strokeLineCap(Round) 全局提供。 */
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
                let pts = slideChevronPts(geom.centerX(cell.x), geom.centerY(cell.y), c, dx, dy)
                if (sbV.size > 0) {
                    sbV.append(" ")
                }
                sbV.append("M ${pts[0] * f} ${pts[1] * f} L ${pts[2] * f} ${pts[3] * f} L ${pts[4] * f} ${pts[5] * f}")
            }
        }
        i = i + 1
    }
    if (sbV.size > 0) {
        var sw = 4.0 * (c / 36.3)
        if (sw < 3.0) {
            sw = 3.0
        }
        list.add(BoardPath(sbV.toString(), Theme.qingDeep, sw, stroke: Theme.qingDeep, fillOp: 0.0))
    }
    /* c3. J17:「停」环:路径头(path 最后一格)是停末格时,在 chevron 之后追加
       两个 fill-only 圆 path(外圈 r=7k ink + 孔 r=3k whitePaper,圆心=格心,
       k=c/36.3),写法同「滑」角标;挪入 paths 层使环压在 chevron 之上(ruling §4)。
       buildBoardHeadDot 的「停末格不画自己的点」逻辑保持。 */
    let head = game.path.size() - 1
    if (head >= 1 && isSlideStopIndex(game, head)) {
        let cell = game.path.at(head)
        let cx = geom.centerX(cell.x)
        let cy = geom.centerY(cell.y)
        let k = c / 36.3
        list.add(BoardPath(circlePathCmds(cx, cy, 7.0 * k, f), Theme.ink, 0.0, stroke: Theme.ink, fillOp: 1.0))
        list.add(BoardPath(circlePathCmds(cx, cy, 3.0 * k, f), Theme.whitePaper, 0.0, stroke: Theme.whitePaper, fillOp: 1.0))
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
