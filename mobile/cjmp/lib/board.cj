package ohos_app_cangjie_entry

import std.math.*
import std.collection.ArrayList
import ohos_app_cangjie_entry.engine.{Cell, GridLayout, Wall}
import ohos_app_cangjie_entry.game.{PatrolGame, Waypoint, ParityEdge}

/*
 * Pure data helpers for board rendering in CJMP Keels (0.2.2).
 * Converts PatrolGame + BoardGeom + device pxPerVp into small renderable structs.
 */

public struct BoardRect {
    public let x: Float64
    public let y: Float64
    public let w: Float64
    public let h: Float64
    public let color: Int64
    public let stroke: Int64
    public let strokeW: Float64

    public init(x: Float64, y: Float64, w: Float64, h: Float64, color: Int64, stroke!: Int64 = Theme.paperLine, strokeW!: Float64 = 1.0) {
        this.x = x
        this.y = y
        this.w = w
        this.h = h
        this.color = color
        this.stroke = stroke
        this.strokeW = strokeW
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
    public let stroke: Int64
    public let fillOp: Float64

    public init(commands: String, color: Int64, strokeW: Float64, stroke!: Int64 = -1, fillOp!: Float64 = 1.0) {
        this.commands = commands
        this.color = color
        this.strokeW = strokeW
        this.stroke = if (stroke < 0) { color } else { stroke }
        this.fillOp = fillOp
    }
}

public struct BoardImg {
    public let x: Float64
    public let y: Float64
    public let w: Float64
    public let h: Float64
    public let vertical: Bool

    public init(x: Float64, y: Float64, w: Float64, h: Float64, vertical: Bool) {
        this.x = x
        this.y = y
        this.w = w
        this.h = h
        this.vertical = vertical
    }
}

public struct BoardGeom {
    public let c: Float64
    public let gap: Float64
    public let pad: Float64
    public let cols: Int64
    public let rows: Int64

    public init(c: Float64, cols: Int64, rows: Int64, gap!: Float64 = 6.0, pad!: Float64 = 8.0) {
        this.c = c
        this.cols = cols
        this.rows = rows
        this.gap = gap
        this.pad = pad
    }

    public func pitch(): Float64 {
        return this.c + this.gap
    }

    public func cellX(i: Int64): Float64 {
        return this.pad + Float64(i) * this.pitch()
    }

    public func cellY(j: Int64): Float64 {
        return this.pad + Float64(j) * this.pitch()
    }

    public func centerX(i: Int64): Float64 {
        return this.cellX(i) + this.c * 0.5
    }

    public func centerY(j: Int64): Float64 {
        return this.cellY(j) + this.c * 0.5
    }

    public func trayW(): Float64 {
        return Float64(this.cols) * this.c + Float64(this.cols - 1) * this.gap + 2.0 * this.pad
    }

    public func trayH(): Float64 {
        return Float64(this.rows) * this.c + Float64(this.rows - 1) * this.gap + 2.0 * this.pad
    }

    public func seamMid(c1: Int64, r1: Int64, c2: Int64, r2: Int64): (Float64, Float64) {
        let mx = (this.centerX(c1) + this.centerX(c2)) * 0.5
        let my = (this.centerY(r1) + this.centerY(r2)) * 0.5
        return (mx, my)
    }

    public func hitTest(px: Float64, py: Float64): Option<Cell> {
        let p = this.pitch()
        let fi = floor((px - this.pad + 3.0) / p)
        let fj = floor((py - this.pad + 3.0) / p)
        if (fi >= 0.0 && fi < Float64(this.cols) && fj >= 0.0 && fj < Float64(this.rows)) {
            return Some(Cell(Int64(fi), Int64(fj)))
        }
        return None
    }
}

public func boardGeomFor(cols: Int64, rows: Int64, winW: Float64): BoardGeom {
    let w = if (winW > 0.0) { winW } else { 360.0 }
    let numCols = if (cols > 0) { cols } else { 6 }
    let numRows = if (rows > 0) { rows } else { 6 }
    let avail = w - 40.0 - 16.0 - Float64(numCols - 1) * 6.0
    var c = floor(avail / Float64(numCols))
    if (c > 43.0) {
        c = 43.0
    }
    if (c < 1.0) {
        c = 1.0
    }
    return BoardGeom(c, numCols, numRows, gap: 6.0, pad: 8.0)
}

func digitsOf(n: Int64): ArrayList<Int64> {
    let list = ArrayList<Int64>()
    if (n <= 0) {
        list.add(0)
        return list
    }
    var v = n
    while (v > 0) {
        list.add(v % 10)
        v = v / 10
    }
    let res = ArrayList<Int64>()
    var i = list.size - 1
    while (i >= 0) {
        res.add(list.get(i).getOrThrow())
        i = i - 1
    }
    return res
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

public func buildBoardCells(game: PatrolGame, geom: BoardGeom): Array<BoardRect> {
    let cs = geom.c
    let cols = geom.cols
    let rows = geom.rows
    let list = ArrayList<BoardRect>()
    var y: Int64 = 0
    while (y < rows) {
        var x: Int64 = 0
        while (x < cols) {
            let cell = Cell(x, y)
            let base = if (game.path.contains(cell)) { Theme.paperShade } else { Theme.whitePaper }
            let color = mechCellFill(game, x, y, base)
            let st = mechCellStroke(game, x, y)
            let sw = mechCellStrokeW(game, x, y)
            list.add(BoardRect(geom.cellX(x), geom.cellY(y), cs, cs, color, stroke: st, strokeW: sw))
            x = x + 1
        }
        y = y + 1
    }
    return list.toArray()
}

public func buildBoardGrid(geom: BoardGeom): Array<BoardSeg> {
    return Array<BoardSeg>()
}

public func buildBoardWalls(game: PatrolGame, geom: BoardGeom): Array<BoardSeg> {
    let list = ArrayList<BoardSeg>()
    for (wall in game.level.walls) {
        let ax = wall.x1
        let ay = wall.y1
        let bx = wall.x2
        let by = wall.y2
        let (mx, my) = geom.seamMid(ax, ay, bx, by)
        if (ay == by && (ax + 1 == bx || bx + 1 == ax)) {
            // vertical seam between columns; perpendicular round-cap bar along the seam (y direction)
            list.add(BoardSeg(mx, my - 10.0, mx, my + 10.0, Theme.ink, 4.0))
        } else if (ax == bx && (ay + 1 == by || by + 1 == ay)) {
            // horizontal seam between rows; perpendicular round-cap bar along the seam (x direction)
            list.add(BoardSeg(mx - 10.0, my, mx + 10.0, my, Theme.ink, 4.0))
        }
    }
    return list.toArray()
}

public func buildBoardParityLabels(game: PatrolGame, geom: BoardGeom, pxFactor: Float64): Array<BoardLabel> {
    let list = ArrayList<BoardLabel>()
    let factor = if (pxFactor <= 0.0) { 3.0 } else { pxFactor }
    let fontVp = 11.0 / factor
    for (pe in game.level.parityEdges) {
        let (mx, my) = geom.seamMid(pe.x1, pe.y1, pe.x2, pe.y2)
        let label = if (pe.requireOdd) { "奇" } else { "偶" }
        // Left edge at mx-5.5, top at my+4.0-0.88*fontVp (ascent offset so baseline lands at my+4.0)
        list.add(BoardLabel(mx - 5.5, my + 4.0 - 0.88 * fontVp, 60.0, fontVp * 1.5, label, Theme.inkMuted, fontVp))
    }
    return list.toArray()
}

public func buildBoardRoute(game: PatrolGame, geom: BoardGeom): Array<BoardSeg> {
    let list = ArrayList<BoardSeg>()
    let sz = game.path.size()
    if (sz >= 2) {
        var i: Int64 = 0
        while (i + 1 < sz) {
            let c1 = game.path.at(i)
            let c2 = game.path.at(i + 1)
            let adx = c1.x - c2.x
            let ady = c1.y - c2.y
            let ax = if (adx < 0) { -adx } else { adx }
            let ay = if (ady < 0) { -ady } else { ady }
            if (ax + ay == 1) {
                let x1 = geom.centerX(c1.x)
                let y1 = geom.centerY(c1.y)
                let x2 = geom.centerX(c2.x)
                let y2 = geom.centerY(c2.y)
                list.add(BoardSeg(x1, y1, x2, y2, Theme.path, Theme.pathStroke))
            }
            i = i + 1
        }
    }
    return list.toArray()
}

public func buildBoardHeadDot(game: PatrolGame, geom: BoardGeom): Array<BoardDot> {
    let list = ArrayList<BoardDot>()
    let sz = game.path.size()
    if (sz >= 1) {
        /* J14:头格是滑行「停」末格时不画自己的点,由 buildBoardSlideStopDots
           的圆环代替(环也是头点,ruling §4)。 */
        if (!isSlideStopIndex(game, sz - 1)) {
            let last = game.path.at(sz - 1)
            let hx = geom.centerX(last.x)
            let hy = geom.centerY(last.y)
            list.add(BoardDot(hx, hy, 6.0, Theme.whitePaper, Theme.ink, Theme.hairline, true))
        }
    }
    return list.toArray()
}

public func buildBoardStationCircles(game: PatrolGame, geom: BoardGeom): Array<BoardDot> {
    let list = ArrayList<BoardDot>()
    let r = 18.0 * geom.c / 43.0
    for (wp in game.level.waypoints) {
        let cx = geom.centerX(wp.x)
        let cy = geom.centerY(wp.y)
        let st = stationStateOf(game, wp.n)
        if (st == 2) {
            list.add(BoardDot(cx, cy, r, Theme.qing, Theme.qing, 0.0, false))
        } else {
            if (st == 1) {
                list.add(BoardDot(cx, cy, r + 2.5, 0x01000000, Theme.gold, 1.3, true))
            }
            list.add(BoardDot(cx, cy, r, Theme.whitePaper, Theme.ink, 2.0, true))
        }
    }
    return list.toArray()
}

public func buildBoardNextLabels(game: PatrolGame, geom: BoardGeom, pxFactor: Float64): Array<BoardLabel> {
    let list = ArrayList<BoardLabel>()
    let r = 18.0 * geom.c / 43.0
    let factor = if (pxFactor <= 0.0) { 3.0 } else { pxFactor }
    let fontVp = 11.0 / factor
    for (wp in game.level.waypoints) {
        let cx = geom.centerX(wp.x)
        let cy = geom.centerY(wp.y)
        let st = stationStateOf(game, wp.n)
        if (st == 1) {
            // Left edge at cx, top at cy+r+12.0-0.88*fontVp (ascent offset so baseline lands at cy+r+12.0)
            list.add(BoardLabel(cx, cy + r + 12.0 - 0.88 * fontVp, 60.0, fontVp * 1.5, "下一驿", Theme.gold, fontVp))
        }
    }
    return list.toArray()
}

public func buildBoardDigits(game: PatrolGame, geom: BoardGeom, pxPerVp: Float64): Array<BoardPath> {
    let list = ArrayList<BoardPath>()
    let size = 21.0 * geom.c / 43.0
    for (wp in game.level.waypoints) {
        let cx = geom.centerX(wp.x)
        let cy = geom.centerY(wp.y)
        let st = stationStateOf(game, wp.n)
        let color = if (st == 2) { Theme.whitePaper } else { Theme.ink }
        let digList = digitsOf(wp.n)
        if (digList.size == 1) {
            let d = digList.get(0).getOrThrow()
            let bbox = digitBBox(d)
            let left = cx - (bbox[0] + bbox[2]) * 0.5 * size / 1000.0
            let base = cy - (bbox[1] + bbox[3]) * 0.5 * size / 1000.0
            let cmds = digitPathCommands(d, left, base, size, pxPerVp)
            list.add(BoardPath(cmds, color, 0.0))
        } else {
            var pos = 0.0
            let pList = ArrayList<Float64>()
            var k: Int64 = 0
            while (k < digList.size) {
                let d = digList.get(k).getOrThrow()
                pList.add(pos)
                pos = pos + digitAdvance(d)
                k = k + 1
            }
            let firstD = digList.get(0).getOrThrow()
            let lastD = digList.get(digList.size - 1).getOrThrow()
            let firstBBox = digitBBox(firstD)
            let lastBBox = digitBBox(lastD)
            let lastPos = pList.get(pList.size - 1).getOrThrow()

            let xStart = pList.get(0).getOrThrow() + firstBBox[0]
            let xEnd = lastPos + lastBBox[2]

            var yMin = firstBBox[1]
            var yMax = firstBBox[3]
            var m: Int64 = 1
            while (m < digList.size) {
                let d = digList.get(m).getOrThrow()
                let bb = digitBBox(d)
                if (bb[1] < yMin) { yMin = bb[1] }
                if (bb[3] > yMax) { yMax = bb[3] }
                m = m + 1
            }

            let xMid = (xStart + xEnd) * 0.5 * size / 1000.0
            let yMid = (yMin + yMax) * 0.5 * size / 1000.0

            let originX = cx - xMid
            let base = cy - yMid

            let sbCmds = StringBuilder()
            var idx: Int64 = 0
            while (idx < digList.size) {
                let d = digList.get(idx).getOrThrow()
                let pEm = pList.get(idx).getOrThrow()
                let dLeft = originX + pEm * size / 1000.0
                let cmd = digitPathCommands(d, dLeft, base, size, pxPerVp)
                if (idx > 0 && cmd.size > 0) {
                    sbCmds.append(" ")
                }
                sbCmds.append(cmd)
                idx = idx + 1
            }
            list.add(BoardPath(sbCmds.toString(), color, 0.0))
        }
    }
    return list.toArray()
}

public func concatArr<T>(a: Array<T>, b: Array<T>): Array<T> {
    if (b.size == 0) { return a }
    if (a.size == 0) { return b }
    let l = ArrayList<T>()
    for (x in a) { l.add(x) }
    for (x in b) { l.add(x) }
    return l.toArray()
}
