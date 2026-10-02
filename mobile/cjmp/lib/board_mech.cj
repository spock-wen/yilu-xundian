package ohos_app_cangjie_entry

import std.math.*
import std.collection.ArrayList
import ohos_app_cangjie_entry.engine.Cell
import ohos_app_cangjie_entry.game.{PatrolGame, LevelDef, REJECT_PARITY, REJECT_ONE_WAY, REJECT_SEALED_GATE, REJECT_BURDEN_FORBIDDEN, REJECT_FERRY, REJECT_WALL}

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
        /* P4 禁区格:空载沿用 base(走过 paperShade 否则 whitePaper),负重 paperShade。 */
        if (game.laden) {
            return Theme.paperShade
        }
        return base
    }
    return base
}

public func mechCellStroke(game: PatrolGame, x: Int64, y: Int64): Int64 {
    if (game.level.hasMechanics() && game.level.isForbiddenCell(x, y) && game.laden) {
        return Theme.inkMuted
    }
    return Theme.paperLine
}

public func mechCellStrokeW(game: PatrolGame, x: Int64, y: Int64): Float64 {
    /* P4:禁区格两种载态边宽都是 1.0(ruling §负重)。 */
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
    /* P4:塌桥不再画墨墙占位(断桩/板条由 buildBoardMechUnder 的 BoardPath 画)。 */
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

/* P4 塌桥/负重「格底之下」皮肤层(BRIDGE_BURDEN_SKIN_20261003):禁区斜纹、
   塌桥三态(缺角标/板条/断桩)、装卸粮袋。全部 BoardPath(Path 命令串),
   画在格底之上、路径/墙/闸门之下。 */
public func buildBoardMechUnder(game: PatrolGame, geom: BoardGeom, pxPerVp: Float64): Array<BoardPath> {
    if (!game.level.hasMechanics()) {
        return Array<BoardPath>()
    }
    let list = ArrayList<BoardPath>()
    let c = geom.c
    let f = if (pxPerVp <= 0.0) { 3.0 } else { pxPerVp }
    /* 1. 禁区斜纹:所有禁区格合并为一个 BoardPath;空载 paper-line 1 宽距 6,
          负重 ink-muted 1.5 宽距 5(inset=线宽/2)。 */
    match (game.level.burden) {
        case Some(b) =>
            if (b.forbidden.size > 0) {
                let col = if (game.laden) { Theme.inkMuted } else { Theme.paperLine }
                let wid = if (game.laden) { 1.5 } else { 1.0 }
                let pitch = if (game.laden) { 5.0 } else { 6.0 }
                let segs = ArrayList<Float64>()
                for (fc in b.forbidden) {
                    for (v in hatchSegs(geom.cellX(fc.x), geom.cellY(fc.y), c, pitch, wid * 0.5)) {
                        segs.add(v)
                    }
                }
                let cmds = segsPathCmds(segs.toArray(), f)
                if (cmds.size > 0) {
                    list.add(BoardPath(cmds, col, wid, stroke: col, fillOp: 0.0))
                }
            }
        case None => ()
    }
    /* 2. 塌桥:触发格缺角标常驻;未断画板条+板缝,已断画两截断桩。 */
    match (game.level.collapse) {
        case Some(cd) =>
            let notch = collapseNotchPts(geom.cellX(cd.triggerX), geom.cellY(cd.triggerY), c)
            list.add(BoardPath(polyPathCmds(notch, f), Theme.inkMuted, 0.0, fillOp: 1.0))
            if (!game.isEdgeCollapsed(cd.x1, cd.y1, cd.x2, cd.y2)) {
                let pr = bridgePlankRect(geom, cd.x1, cd.y1, cd.x2, cd.y2)
                list.add(BoardPath(rrectPathCmds(pr[0], pr[1], pr[2], pr[3], 2.0, f),
                    Theme.qing, 1.0, stroke: Theme.qingDeep, fillOp: 1.0))
                list.add(BoardPath(segsPathCmds(bridgeSeamSegs(geom, cd.x1, cd.y1, cd.x2, cd.y2), f),
                    Theme.qingDeep, 1.0, fillOp: 0.0))
            } else {
                let sp = bridgeStumpPolys(geom, cd.x1, cd.y1, cd.x2, cd.y2)
                var side: Int64 = 0
                while (side < 2) {
                    let pts = Array<Float64>(14, repeat: 0.0)
                    var j: Int64 = 0
                    while (j < 14) {
                        pts[j] = sp[side * 14 + j]
                        j = j + 1
                    }
                    list.add(BoardPath(polyPathCmds(pts, f), Theme.inkMuted, 0.0, fillOp: 1.0))
                    side = side + 1
                }
            }
        case None => ()
    }
    /* 3. 负重装卸点:装粮袋实心金、卸粮袋空心。 */
    match (game.level.burden) {
        case Some(b) =>
            for (p in bagPaths(geom.centerX(b.loadX), geom.centerY(b.loadY), skinK(c), false, f)) {
                list.add(p)
            }
            for (p in bagPaths(geom.centerX(b.unloadX), geom.centerY(b.unloadY), skinK(c), true, f)) {
                list.add(p)
            }
        case None => ()
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
   k=c/36.3:dep=18k、h=25k;入向左/上时中心沿入向整体偏 0.18c,
   避让右下「滑」角标(SLIDE_GATE_FOLLOWUP_20261002 §1,原 0.16c)。
   返回 [arm1x,arm1y,tipx,tipy,arm2x,arm2y](vp,未乘 pxPerVp)。 */
public func slideChevronPts(cx: Float64, cy: Float64, c: Float64, dx: Int64, dy: Int64): Array<Float64> {
    let k = c / 36.3
    let dep = 18.0 * k
    let h = 25.0 * k
    let fdx = Float64(dx)
    let fdy = Float64(dy)
    let perpx = -fdy
    let perpy = fdx
    let shift = if (dx < 0 || dy < 0) { 0.18 * c } else { 0.0 } /* FOLLOWUP §1:0.16c→0.18c */
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
   定位以墨迹包围盒为准(FOLLOWUP §1):墨迹高=max(gh,0.78gh+s)(最下排三短横
   下探到 0.78gh+s=12.76k),oy = 格下 - 1k - 墨迹高。
   返回 [x0,y0,x1,y1]*7,与 render_slide_cell_spec.py 的 hua() 一致(以脚本为准)。 */
public func slideHuaRects(c: Float64): Array<Float64> {
    let k = c / 36.3
    let gw = 11.0 * k
    let gh = 12.0 * k
    let ox = c - gw - 2.0 * k
    var s = 3.4 * k
    if (s < 2.0) {
        s = 2.0
    }
    var inkH = 0.78 * gh + s
    if (inkH < gh) {
        inkH = gh
    }
    let oy = c - 1.0 * k - inkH
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
    /* e. P4 路径头负重徽章:仅负重时,头格右上 (+10,-10) 直径 16 white-paper
          圆(ink 描边 1)内放 0.5 倍粮袋,压在最上层(ruling §负重)。 */
    match (game.level.burden) {
        case Some(_) =>
            if (game.laden && head >= 0) {
                let hcell = game.path.at(head)
                let bcx = geom.centerX(hcell.x) + 10.0
                let bcy = geom.centerY(hcell.y) - 10.0
                list.add(BoardPath(circlePathCmds(bcx, bcy, 7.5, f),
                    Theme.whitePaper, 1.0, stroke: Theme.ink, fillOp: 1.0))
                for (p in bagPaths(bcx, bcy + 0.5, 0.5, false, f)) {
                    list.add(p)
                }
            }
        case None => ()
    }
    return list.toArray()
}

/* P4:该次 WALL 拒绝是否塌桥断边被拒(from/to 与 collapse 边无向相等且已断)。
   是则按机制拒绝闪边(toast「此路不通」)。 */
public func isCollapseReject(game: PatrolGame): Bool {
    if (game.lastReject != REJECT_WALL) {
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
    if (ax + ay != 1) {
        return false
    }
    match (game.level.collapse) {
        case Some(cd) =>
            let fwd = game.lastRejectFromX == cd.x1 && game.lastRejectFromY == cd.y1
                && game.lastRejectToX == cd.x2 && game.lastRejectToY == cd.y2
            let rev = game.lastRejectFromX == cd.x2 && game.lastRejectFromY == cd.y2
                && game.lastRejectToX == cd.x1 && game.lastRejectToY == cd.y1
            return (fwd || rev) && game.isEdgeCollapsed(cd.x1, cd.y1, cd.x2, cd.y2)
        case None =>
            return false
    }
}

/* 该次拒绝是否应当在 from→to 这条边上闪烁提示。
   仅机制类拒绝（奇偶/单向/闸门/负禁/进甲）且 from/to 都有效并曼哈顿相邻才闪；
   WALL 里只有塌桥断边(isCollapseReject)闪；VISITED/WAYPOINT/BOUNDS/START 与
   实体墙的 WALL 不闪。 */
public func rejectShouldFlash(game: PatrolGame): Bool {
    let code = game.lastReject
    if (code == REJECT_WALL) {
        return isCollapseReject(game)
    }
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

/* P4:机制拒绝 toast 文案;奇偶优先,塌桥断边「此路不通」,负重禁区「粮重不可进」。 */
public func mechToastText(game: PatrolGame): String {
    let p = parityToastText(game)
    if (p.size > 0) {
        return p
    }
    if (isCollapseReject(game)) {
        return "此路不通"
    }
    if (game.lastReject == REJECT_BURDEN_FORBIDDEN) {
        return "粮重不可进"
    }
    return ""
}

/* P4:toast 宽度:空 86;否则 14/字 + 30(4 字=86、5 字=100),字数按 Rune 计。 */
public func mechToastWidth(text: String): Float64 {
    if (text.size == 0) {
        return 86.0
    }
    return 14.0 * Float64(text.toRuneArray().size) + 30.0
}

/* ---- P4 塌桥/负重皮肤纯几何(坐标一律 vp;*PathCmds 才乘 f=pxPerVp)。
   依据 render_bridge_burden.py,K=c/36.3 记作 k,间隔 G 与线宽不随 k 缩放。 */

public func skinK(c: Float64): Float64 {
    return c / 36.3
}

/* 整椭圆 path 命令:4 段三次贝塞尔(kappa=0.5522847498)拼成闭合,同 circlePathCmds。 */
public func ellipsePathCmds(cx: Float64, cy: Float64, rx: Float64, ry: Float64, f: Float64): String {
    let kx = 0.5522847498 * rx
    let ky = 0.5522847498 * ry
    let lx = (cx - rx) * f
    let rxi = (cx + rx) * f
    let ty = (cy - ry) * f
    let byy = (cy + ry) * f
    let cxf = cx * f
    let cyf = cy * f
    let sb = StringBuilder()
    sb.append("M ${lx} ${cyf} C ${lx} ${(cy - ky) * f} ${(cx - kx) * f} ${ty} ${cxf} ${ty}")
    sb.append(" C ${(cx + kx) * f} ${ty} ${rxi} ${(cy - ky) * f} ${rxi} ${cyf}")
    sb.append(" C ${rxi} ${(cy + ky) * f} ${(cx + kx) * f} ${byy} ${cxf} ${byy}")
    sb.append(" C ${(cx - kx) * f} ${byy} ${lx} ${(cy + ky) * f} ${lx} ${cyf} Z")
    return sb.toString()
}

/* 圆角矩形 path 命令:四角三次贝塞尔(同 kappa),直边相连,闭合。 */
public func rrectPathCmds(x0: Float64, y0: Float64, x1: Float64, y1: Float64, r: Float64, f: Float64): String {
    let kr = 0.5522847498 * r
    let xr0 = (x0 + r) * f
    let xr1 = (x1 - r) * f
    let yr0 = (y0 + r) * f
    let yr1 = (y1 - r) * f
    let sb = StringBuilder()
    sb.append("M ${xr0} ${y0 * f} L ${xr1} ${y0 * f}")
    sb.append(" C ${(xr1 + kr * f)} ${y0 * f} ${x1 * f} ${(yr0 - kr * f)} ${x1 * f} ${yr0}")
    sb.append(" L ${x1 * f} ${yr1}")
    sb.append(" C ${x1 * f} ${(yr1 + kr * f)} ${(xr1 + kr * f)} ${y1 * f} ${xr1} ${y1 * f}")
    sb.append(" L ${xr0} ${y1 * f}")
    sb.append(" C ${(xr0 - kr * f)} ${y1 * f} ${x0 * f} ${(yr1 + kr * f)} ${x0 * f} ${yr1}")
    sb.append(" L ${x0 * f} ${yr0}")
    sb.append(" C ${x0 * f} ${(yr0 - kr * f)} ${(xr0 - kr * f)} ${y0 * f} ${xr0} ${y0 * f} Z")
    return sb.toString()
}

/* 闭合多边形:pts=x,y 平铺,首点 M、其余 L、末尾 Z。 */
public func polyPathCmds(pts: Array<Float64>, f: Float64): String {
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
    sb.append(" Z")
    return sb.toString()
}

/* 线段族:每 4 个数(ax,ay,bx,by)一段 "M ax ay L bx by",空格相连。 */
public func segsPathCmds(segs: Array<Float64>, f: Float64): String {
    let sb = StringBuilder()
    var i: Int64 = 0
    while (i + 3 < segs.size) {
        if (sb.size > 0) {
            sb.append(" ")
        }
        sb.append("M ${segs[i] * f} ${segs[i + 1] * f} L ${segs[i + 2] * f} ${segs[i + 3] * f}")
        i = i + 4
    }
    return sb.toString()
}

/* ---- 粮袋(脚本 sack(cx,cy,k),k 为缩放系数) ---- */

/* 袋口梯形 4 顶点(x,y 平铺):下宽 5k、上宽 10k、高 6k,位于 cy 上方。 */
public func bagNeckPts(cx: Float64, cy: Float64, k: Float64): Array<Float64> {
    return [cx - 2.5 * k, cy - 3.0 * k, cx + 2.5 * k, cy - 3.0 * k,
        cx + 5.0 * k, cy - 9.0 * k, cx - 5.0 * k, cy - 9.0 * k]
}

/* 袋身椭圆 [中心x,中心y,rx,ry]:包围盒 [cx-8k,cy-3.5k,cx+8k,cy+10.5k]。 */
public func bagBodyEllipse(cx: Float64, cy: Float64, k: Float64): Array<Float64> {
    return [cx, cy + 3.5 * k, 8.0 * k, 7.0 * k]
}

/* 系口线两端点(x0,y0,x1,y1)。 */
public func bagTiePts(cx: Float64, cy: Float64, k: Float64): Array<Float64> {
    return [cx - 3.4 * k, cy - 3.2 * k, cx + 3.4 * k, cy - 3.2 * k]
}

/* 粮袋 3 个 BoardPath(梯形、椭圆、系口线);前两个填 hollow?whitePaper:gold、
   ink 描边 1.4k,第三个只描边同宽。墨迹外框 (16k+1.4k)×(19.5k+1.4k)。 */
public func bagPaths(cx: Float64, cy: Float64, k: Float64, hollow: Bool, f: Float64): Array<BoardPath> {
    let fill = if (hollow) { Theme.whitePaper } else { Theme.gold }
    let sw = 1.4 * k
    let e = bagBodyEllipse(cx, cy, k)
    return [BoardPath(polyPathCmds(bagNeckPts(cx, cy, k), f), fill, sw, stroke: Theme.ink, fillOp: 1.0),
        BoardPath(ellipsePathCmds(e[0], e[1], e[2], e[3], f), fill, sw, stroke: Theme.ink, fillOp: 1.0),
        BoardPath(segsPathCmds(bagTiePts(cx, cy, k), f), Theme.ink, sw, stroke: Theme.ink, fillOp: 0.0)]
}

/* ---- 塌桥(格 (ax,ay)-(bx,by) 相邻,ay==by 为左右相邻;k=skinK(c),A=8k) ---- */

/* 断前的木板条 [x0,y0,x1,y1]:缝中点居中,沿通行方向长 G+4,横向宽 16k。 */
public func bridgePlankRect(geom: BoardGeom, ax: Int64, ay: Int64, bx: Int64, by: Int64): Array<Float64> {
    let (mx, my) = geom.seamMid(ax, ay, bx, by)
    let a = 8.0 * skinK(geom.c)
    let hw = geom.gap * 0.5 + 2.0
    if (ay == by) {
        return [mx - hw, my - a, mx + hw, my + a]
    }
    return [mx - a, my - hw, mx + a, my + hw]
}

/* 板缝两条线段(8 个数):左右相邻时 x=mx±1.7、y 从 my-A+1 到 my+A-1。 */
public func bridgeSeamSegs(geom: BoardGeom, ax: Int64, ay: Int64, bx: Int64, by: Int64): Array<Float64> {
    let (mx, my) = geom.seamMid(ax, ay, bx, by)
    let a = 8.0 * skinK(geom.c)
    if (ay == by) {
        return [mx - 1.7, my - a + 1.0, mx - 1.7, my + a - 1.0,
            mx + 1.7, my - a + 1.0, mx + 1.7, my + a - 1.0]
    }
    return [mx - a + 1.0, my - 1.7, mx + a - 1.0, my - 1.7,
        mx - a + 1.0, my + 1.7, mx + a - 1.0, my + 1.7]
}

/* 断后两截残板顶点(28 个数,各 7 顶点):局部 u 沿通行方向、v 垂直,
   v_i=-A+i*(2A/4);左/下截边缘 u=-(G/2+2)、内侧 u=-1.2+jl[i],
   右/上截边缘 u=+(G/2+2)、内侧 u=+1.2+jr[i];左右相邻 x=mx+u、y=my+v,
   上下相邻转置。jl/jr 见脚本 bridge()。 */
public func bridgeStumpPolys(geom: BoardGeom, ax: Int64, ay: Int64, bx: Int64, by: Int64): Array<Float64> {
    let (mx, my) = geom.seamMid(ax, ay, bx, by)
    let a = 8.0 * skinK(geom.c)
    let hw = geom.gap * 0.5 + 2.0
    let jl = [0.0, -1.0, 0.5, -0.9, 0.2]
    let jr = [0.3, 1.0, -0.3, 1.1, 0.0]
    let uv = ArrayList<Float64>()
    var side: Int64 = 0
    while (side < 2) {
        let sgn = if (side == 0) { -1.0 } else { 1.0 }
        let js = if (side == 0) { jl } else { jr }
        uv.add(sgn * hw)
        uv.add(-a)
        var j: Int64 = 0
        while (j <= 4) {
            uv.add(sgn * 1.2 + js[j])
            uv.add(-a + Float64(j) * (2.0 * a / 4.0))
            j = j + 1
        }
        uv.add(sgn * hw)
        uv.add(a)
        side = side + 1
    }
    let out = ArrayList<Float64>()
    var m: Int64 = 0
    while (m + 1 < uv.size) {
        let u = uv[m]
        let v = uv[m + 1]
        if (ay == by) {
            out.add(mx + u)
            out.add(my + v)
        } else {
            out.add(mx + v)
            out.add(my + u)
        }
        m = m + 2
    }
    return out.toArray()
}

/* 触发格左上缺角三角(7 顶点,14 个数),L=8k;斜边锯齿见脚本 corner_notch()。 */
public func collapseNotchPts(cellX: Float64, cellY: Float64, c: Float64): Array<Float64> {
    let l = 8.0 * skinK(c)
    let x = cellX
    let y = cellY
    return [x + 1.0, y + 1.0, x + l, y + 1.0, x + 0.78 * l, y + 0.32 * l, x + 0.55 * l, y + 0.5 * l,
        x + 0.36 * l, y + 0.62 * l, x + 0.30 * l, y + 0.8 * l, x + 1.0, y + l]
}

/* 方格 [x0,x0+c]x[y0,y0+c] 内 45° 斜纹(左下→右上):线族 x+y=x0+y0+c+i*pitch,
   i 从 -1 到 int(2c/pitch)+1;每条裁到内缩 inset 的方格,长度>0 才输出;
   返回 ax,ay,bx,by 平铺(a 左下端、b 右上端)。 */
public func hatchSegs(x0: Float64, y0: Float64, c: Float64, pitch: Float64, inset: Float64): Array<Float64> {
    let bx0 = x0 + inset
    let by0 = y0 + inset
    let bx1 = x0 + c - inset
    let by1 = y0 + c - inset
    let out = ArrayList<Float64>()
    let n = Int64(2.0 * c / pitch) + 1
    var i: Int64 = -1
    while (i <= n) {
        let s = x0 + y0 + c + Float64(i) * pitch
        var ax = s - by1
        if (ax < bx0) {
            ax = bx0
        }
        var bx = s - by0
        if (bx > bx1) {
            bx = bx1
        }
        if (bx - ax > 0.0) {
            out.add(ax)
            out.add(s - ax)
            out.add(bx)
            out.add(s - bx)
        }
        i = i + 1
    }
    return out.toArray()
}

/* 一排 chip 水平居中时各 chip 左边缘 x:total=sum(widths)+gap*(n-1),
   x0=(rowW-total)/2,依次累加。 */
public func chipRowOffsets(rowW: Float64, widths: Array<Float64>, gap: Float64): Array<Float64> {
    let out = ArrayList<Float64>()
    if (widths.size == 0) {
        return out.toArray()
    }
    var total = 0.0
    for (w in widths) {
        total = total + w
    }
    total = total + gap * Float64(widths.size - 1)
    var x = (rowW - total) * 0.5
    for (w in widths) {
        out.add(x)
        x = x + w + gap
    }
    return out.toArray()
}
