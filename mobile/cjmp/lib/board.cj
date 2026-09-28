package ohos_app_cangjie_entry

import std.math.*
import std.collection.ArrayList
import ohos_app_cangjie_entry.engine.{Cell, GridLayout, Wall}
import ohos_app_cangjie_entry.game.{PatrolGame, Waypoint, ParityEdge}

/*
 * Pure data helpers for board rendering in CJMP Keels (0.2.2).
 * Converts PatrolGame + GridLayout + device pxPerVp into small renderable structs.
 */

public struct BoardRect {
    public let x: Float64
    public let y: Float64
    public let w: Float64
    public let h: Float64
    public let color: Int64

    public init(x: Float64, y: Float64, w: Float64, h: Float64, color: Int64) {
        this.x = x
        this.y = y
        this.w = w
        this.h = h
        this.color = color
    }
}

public struct BoardSeg {
    public let x1: Float64
    public let y1: Float64
    public let x2: Float64
    public let y2: Float64
    public let color: Int64
    public let width: Float64

    public init(x1: Float64, y1: Float64, x2: Float64, y2: Float64, color: Int64, width: Float64) {
        this.x1 = x1
        this.y1 = y1
        this.x2 = x2
        this.y2 = y2
        this.color = color
        this.width = width
    }
}

public struct BoardDot {
    public let cx: Float64
    public let cy: Float64
    public let r: Float64
    public let fill: Int64
    public let stroke: Int64
    public let strokeW: Float64
    public let hasStroke: Bool

    public init(cx: Float64, cy: Float64, r: Float64, fill: Int64, stroke: Int64, strokeW: Float64, hasStroke: Bool) {
        this.cx = cx
        this.cy = cy
        this.r = r
        this.fill = fill
        this.stroke = stroke
        this.strokeW = strokeW
        this.hasStroke = hasStroke
    }
}

public struct BoardLabel {
    public let x: Float64
    public let y: Float64
    public let w: Float64
    public let h: Float64
    public let text: String
    public let color: Int64
    public let size: Float64

    public init(x: Float64, y: Float64, w: Float64, h: Float64, text: String, color: Int64, size: Float64) {
        this.x = x
        this.y = y
        this.w = w
        this.h = h
        this.text = text
        this.color = color
        this.size = size
    }
}

public struct BoardPath {
    public let commands: String
    public let color: Int64
    public let strokeW: Float64

    public init(commands: String, color: Int64, strokeW: Float64) {
        this.commands = commands
        this.color = color
        this.strokeW = strokeW
    }
}

func appendFullCircle(sb: StringBuilder, ccx: Float64, ccy: Float64, r: Float64): Unit {
    let xRight = ccx + r
    let xLeft = ccx - r
    sb.append(" M ${xRight} ${ccy} A ${r} ${r} 0 0 1 ${xLeft} ${ccy} A ${r} ${r} 0 0 1 ${xRight} ${ccy}")
}

func appendArc(sb: StringBuilder, ccx: Float64, ccy: Float64, r: Float64, startAngle: Float64, endAngle: Float64, needMove: Bool): Unit {
    let sx = ccx + r * cos(startAngle)
    let sy = ccy + r * sin(startAngle)
    let ex = ccx + r * cos(endAngle)
    let ey = ccy + r * sin(endAngle)
    var span = endAngle - startAngle
    while (span < 0.0) {
        span = span + 6.283185307179586
    }
    while (span >= 6.283185307179586) {
        span = span - 6.283185307179586
    }
    let largeArc = if (span > 3.141592653589793) { 1 } else { 0 }
    let sweep = 1
    if (needMove) {
        sb.append(" M ${sx} ${sy}")
    } else {
        sb.append(" L ${sx} ${sy}")
    }
    sb.append(" A ${r} ${r} 0 ${largeArc} ${sweep} ${ex} ${ey}")
}

func appendDigitCommands(sb: StringBuilder, d: Int64, cx: Float64, cy: Float64, h: Float64, px: Float64): Unit {
    let scx = cx * px
    let scy = cy * px
    let sh = h * px

    if (d == 0) {
        appendFullCircle(sb, scx, scy, sh * 0.22)
    } else if (d == 1) {
        sb.append(" M ${scx - sh * 0.16} ${scy - sh * 0.18}")
        sb.append(" L ${scx + sh * 0.04} ${scy - sh * 0.32}")
        sb.append(" L ${scx + sh * 0.04} ${scy + sh * 0.32}")
        sb.append(" M ${scx - sh * 0.18} ${scy + sh * 0.32}")
        sb.append(" L ${scx + sh * 0.20} ${scy + sh * 0.32}")
    } else if (d == 2) {
        appendArc(sb, scx, scy - sh * 0.14, sh * 0.18, 2.90, 0.35, true)
        sb.append(" L ${scx - sh * 0.22} ${scy + sh * 0.32}")
        sb.append(" L ${scx + sh * 0.22} ${scy + sh * 0.32}")
    } else if (d == 3) {
        appendArc(sb, scx, scy - sh * 0.14, sh * 0.16, 2.70, 0.70, true)
        sb.append(" M ${scx + sh * 0.16} ${scy + sh * 0.14}")
        appendArc(sb, scx, scy + sh * 0.14, sh * 0.17, 5.60, 2.20, false)
    } else if (d == 4) {
        sb.append(" M ${scx + sh * 0.14} ${scy + sh * 0.32}")
        sb.append(" L ${scx + sh * 0.14} ${scy - sh * 0.32}")
        sb.append(" L ${scx - sh * 0.22} ${scy + sh * 0.04}")
        sb.append(" L ${scx + sh * 0.24} ${scy + sh * 0.04}")
    } else if (d == 5) {
        sb.append(" M ${scx + sh * 0.20} ${scy - sh * 0.32}")
        sb.append(" L ${scx - sh * 0.18} ${scy - sh * 0.32}")
        sb.append(" L ${scx - sh * 0.18} ${scy - sh * 0.02}")
        sb.append(" L ${scx + sh * 0.06} ${scy - sh * 0.02}")
        appendArc(sb, scx, scy + sh * 0.14, sh * 0.18, 5.20, 2.40, false)
    } else if (d == 6) {
        appendFullCircle(sb, scx, scy + sh * 0.10, sh * 0.18)
        sb.append(" M ${scx - sh * 0.18} ${scy + sh * 0.10}")
        sb.append(" L ${scx - sh * 0.10} ${scy - sh * 0.32}")
    } else if (d == 7) {
        sb.append(" M ${scx - sh * 0.22} ${scy - sh * 0.32}")
        sb.append(" L ${scx + sh * 0.22} ${scy - sh * 0.32}")
        sb.append(" L ${scx - sh * 0.04} ${scy + sh * 0.32}")
    } else if (d == 8) {
        appendFullCircle(sb, scx, scy - sh * 0.14, sh * 0.14)
        appendFullCircle(sb, scx, scy + sh * 0.16, sh * 0.16)
    } else if (d == 9) {
        appendFullCircle(sb, scx, scy - sh * 0.10, sh * 0.18)
        sb.append(" M ${scx + sh * 0.18} ${scy - sh * 0.10}")
        sb.append(" L ${scx + sh * 0.12} ${scy + sh * 0.32}")
    }
}

public func stationDigitCommands(n: Int64, cx: Float64, cy: Float64, h: Float64, pxPerVp: Float64): String {
    let factor = if (pxPerVp <= 0.0) { 3.0 } else { pxPerVp }
    let sb = StringBuilder()
    if (n >= 10) {
        let pair = h * 0.90
        appendDigitCommands(sb, 1, cx - h * 0.34, cy, pair, factor)
        appendDigitCommands(sb, n - 10, cx + h * 0.30, cy, pair, factor)
    } else {
        appendDigitCommands(sb, n, cx, cy, h, factor)
    }
    return sb.toString().trimAscii()
}

public func stationStateOf(game: PatrolGame, n: Int64): Int64 {
    let nxt = game.nextRequired()
    if (n < nxt) {
        return 2
    }
    if (n == nxt) {
        return 1
    }
    return 0
}

public func buildBoardCells(game: PatrolGame, layout: GridLayout): Array<BoardRect> {
    let cs = layout.cellSize
    let cols = layout.cols
    let rows = layout.rows
    let list = ArrayList<BoardRect>()
    var y: Int64 = 0
    while (y < rows) {
        var x: Int64 = 0
        while (x < cols) {
            let cell = Cell(x, y)
            let color = if (game.path.contains(cell)) {
                Theme.paperShade
            } else {
                Theme.whitePaper
            }
            list.add(BoardRect(Float64(x) * cs, Float64(y) * cs, cs, cs, color))
            x = x + 1
        }
        y = y + 1
    }
    return list.toArray()
}

public func buildBoardGrid(layout: GridLayout): Array<BoardSeg> {
    let cs = layout.cellSize
    let cols = layout.cols
    let rows = layout.rows
    let bw = Float64(cols) * cs
    let bh = Float64(rows) * cs
    let list = ArrayList<BoardSeg>()
    var gx: Int64 = 0
    while (gx <= cols) {
        let px = Float64(gx) * cs
        list.add(BoardSeg(px, 0.0, px, bh, Theme.paperLine, Theme.hairline))
        gx = gx + 1
    }
    var gy: Int64 = 0
    while (gy <= rows) {
        let py = Float64(gy) * cs
        list.add(BoardSeg(0.0, py, bw, py, Theme.paperLine, Theme.hairline))
        gy = gy + 1
    }
    return list.toArray()
}

public func buildBoardWalls(game: PatrolGame, layout: GridLayout): Array<BoardSeg> {
    let cs = layout.cellSize
    let list = ArrayList<BoardSeg>()
    for (wall in game.level.walls) {
        var ax = wall.x1
        var ay = wall.y1
        var bx = wall.x2
        var by = wall.y2
        if (ay == by && ax + 1 == bx) {
            let px = Float64(bx) * cs
            list.add(BoardSeg(px, Float64(ay) * cs + 4.0, px, Float64(ay + 1) * cs - 4.0, Theme.ink, 3.0))
        } else if (ay == by && bx + 1 == ax) {
            let px = Float64(ax) * cs
            list.add(BoardSeg(px, Float64(ay) * cs + 4.0, px, Float64(ay + 1) * cs - 4.0, Theme.ink, 3.0))
        } else if (ax == bx && ay + 1 == by) {
            let py = Float64(by) * cs
            list.add(BoardSeg(Float64(ax) * cs + 4.0, py, Float64(ax + 1) * cs - 4.0, py, Theme.ink, 3.0))
        } else if (ax == bx && by + 1 == ay) {
            let py = Float64(ay) * cs
            list.add(BoardSeg(Float64(ax) * cs + 4.0, py, Float64(ax + 1) * cs - 4.0, py, Theme.ink, 3.0))
        }
    }
    return list.toArray()
}

public func buildBoardParityLabels(game: PatrolGame, layout: GridLayout, pxFactor: Float64): Array<BoardLabel> {
    let cs = layout.cellSize
    let list = ArrayList<BoardLabel>()
    // HarmonyOS parity: 11 device px (Canvas px); readability noted in M2 report
    let factor = if (pxFactor <= 0.0) { 3.0 } else { pxFactor }
    let fontVp = 11.0 / factor
    for (pe in game.level.parityEdges) {
        let mx = (Float64(pe.x1) + Float64(pe.x2) + 1.0) * cs * 0.5
        let my = (Float64(pe.y1) + Float64(pe.y2) + 1.0) * cs * 0.5
        let label = if (pe.requireOdd) { "奇" } else { "偶" }
        // Left edge at mx-5.5, top at my+4.0-0.88*fontVp (ascent offset so baseline lands at my+4.0)
        list.add(BoardLabel(mx - 5.5, my + 4.0 - 0.88 * fontVp, 60.0, fontVp * 1.5, label, Theme.inkMuted, fontVp))
    }
    return list.toArray()
}

public func buildBoardRoute(game: PatrolGame, layout: GridLayout): Array<BoardSeg> {
    let cs = layout.cellSize
    let list = ArrayList<BoardSeg>()
    let sz = game.path.size()
    if (sz >= 2) {
        var i: Int64 = 0
        while (i + 1 < sz) {
            let c1 = game.path.at(i)
            let c2 = game.path.at(i + 1)
            let x1 = (Float64(c1.x) + 0.5) * cs
            let y1 = (Float64(c1.y) + 0.5) * cs
            let x2 = (Float64(c2.x) + 0.5) * cs
            let y2 = (Float64(c2.y) + 0.5) * cs
            list.add(BoardSeg(x1, y1, x2, y2, Theme.path, Theme.pathStroke))
            i = i + 1
        }
    }
    return list.toArray()
}

public func buildBoardHeadDot(game: PatrolGame, layout: GridLayout): Array<BoardDot> {
    let cs = layout.cellSize
    let list = ArrayList<BoardDot>()
    let sz = game.path.size()
    if (sz >= 1) {
        let last = game.path.at(sz - 1)
        let hx = (Float64(last.x) + 0.5) * cs
        let hy = (Float64(last.y) + 0.5) * cs
        list.add(BoardDot(hx, hy, 6.0, Theme.whitePaper, Theme.ink, Theme.hairline, true))
    }
    return list.toArray()
}

public func buildBoardStationCircles(game: PatrolGame, layout: GridLayout): Array<BoardDot> {
    let cs = layout.cellSize
    let list = ArrayList<BoardDot>()
    let r = Theme.stationD * cs / 48.0 / 2.0
    for (wp in game.level.waypoints) {
        let cx = (Float64(wp.x) + 0.5) * cs
        let cy = (Float64(wp.y) + 0.5) * cs
        let st = stationStateOf(game, wp.n)
        if (st == 2) {
            list.add(BoardDot(cx, cy, r, Theme.qing, Theme.qing, 0.0, false))
        } else {
            list.add(BoardDot(cx, cy, r, Theme.whitePaper, Theme.ink, Theme.hairline, true))
            if (st == 1) {
                list.add(BoardDot(cx, cy, r + 3.0, 0x01000000, Theme.gold, Theme.hairline, true))
            }
        }
    }
    return list.toArray()
}

public func buildBoardNextLabels(game: PatrolGame, layout: GridLayout, pxFactor: Float64): Array<BoardLabel> {
    let cs = layout.cellSize
    let list = ArrayList<BoardLabel>()
    let r = Theme.stationD * cs / 48.0 / 2.0
    // HarmonyOS parity: 11 device px (Canvas px); readability noted in M2 report
    let factor = if (pxFactor <= 0.0) { 3.0 } else { pxFactor }
    let fontVp = 11.0 / factor
    for (wp in game.level.waypoints) {
        let cx = (Float64(wp.x) + 0.5) * cs
        let cy = (Float64(wp.y) + 0.5) * cs
        let st = stationStateOf(game, wp.n)
        if (st == 1) {
            // Left edge at cx, top at cy+r+12.0-0.88*fontVp (ascent offset so baseline lands at cy+r+12.0)
            list.add(BoardLabel(cx, cy + r + 12.0 - 0.88 * fontVp, 60.0, fontVp * 1.5, "下一驿", Theme.gold, fontVp))
        }
    }
    return list.toArray()
}

public func buildBoardDigits(game: PatrolGame, layout: GridLayout, pxPerVp: Float64): Array<BoardPath> {
    let cs = layout.cellSize
    let list = ArrayList<BoardPath>()
    var glyphH: Float64 = Theme.stationD * cs / 48.0 * 0.60
    if (glyphH < Float64(Theme.stationNumberMin)) {
        glyphH = Float64(Theme.stationNumberMin)
    }
    for (wp in game.level.waypoints) {
        let cx = (Float64(wp.x) + 0.5) * cs
        let cy = (Float64(wp.y) + 0.5) * cs
        let st = stationStateOf(game, wp.n)
        let color = if (st == 2) { Theme.whitePaper } else { Theme.ink }
        let strokeW = glyphH * 0.16
        let cmds = stationDigitCommands(wp.n, cx, cy, glyphH, pxPerVp)
        list.add(BoardPath(cmds, color, strokeW))
    }
    return list.toArray()
}
