package ohos_app_cangjie_entry.game

import std.collection.ArrayList
import ohos_app_cangjie_entry.engine.{Cell, GridMap, GridPath}

/* Thin Zip / 「驿路巡点」 rules on top of the reusable grid engine. */
public class PatrolGame {
    public var level: LevelDef
    public var grid: GridMap
    public var path: GridPath = GridPath()
    /* 0 = none, 1 = needs odd step, 2 = needs even step; set on parity reject so UI can toast. */
    public var lastRejectParity: Int64 = 0
    /* 每次成功输入的起始已铺格数；一次输入 = 一个撤销单元（渡口输入铺 [甲,乙] 两格）。 */
    var units: ArrayList<Int64> = ArrayList<Int64>()

    public init(level: LevelDef) {
        this.level = level
        this.grid = GridMap(level.cols, level.rows, level.walls)
    }

    public func reset(level: LevelDef): Unit {
        this.level = level
        this.grid = GridMap(level.cols, level.rows, level.walls)
        this.path.clear()
        this.clearUnits()
        this.lastRejectParity = 0
    }

    /* 已铺格数（含当前站立格），即顶栏「第 N 步」的 N。 */
    public func filled(): Int64 {
        return this.path.size()
    }

    public func numberAt(x: Int64, y: Int64): Int64 {
        return this.level.numberAt(x, y)
    }

    public func nextRequired(): Int64 {
        var seen: Int64 = 0
        var i: Int64 = 0
        while (i < this.path.size()) {
            let cell = this.path.at(i)
            let n = this.level.numberAt(cell.x, cell.y)
            if (n == seen + 1) {
                seen = n
            }
            i = i + 1
        }
        return seen + 1
    }

    /* SoT: filled odd → require_odd; even → require_even (filled = cells laid, standing cell counted, before push). */
    func checkParity(last: Cell, cell: Cell): Bool {
        let filled = this.filled()
        for (pe in this.level.parityEdges) {
            if (pe.matches(last, cell)) {
                if (pe.requireOdd && filled % 2 == 0) {
                    this.lastRejectParity = 1
                    return false
                }
                if (pe.requireEven && filled % 2 == 1) {
                    this.lastRejectParity = 2
                    return false
                }
            }
        }
        return true
    }

    /* 一次输入铺出的格段，None 表示该输入非法（语义同旧 canEnter 的 false）。
       普通格 = 单格段；踏上渡口甲 = [甲,乙] 两格段（甲→乙 跳跃本身忽略墙）。 */
    func expandInput(cell: Cell): Option<ArrayList<Cell>> {
        this.lastRejectParity = 0
        if (!this.grid.inBounds(cell)) {
            return None
        }
        if (this.path.contains(cell)) {
            return None
        }
        let lastOpt = this.path.last()
        match (lastOpt) {
            case None =>
                if (this.level.numberAt(cell.x, cell.y) == 1) {
                    let seg0 = ArrayList<Cell>()
                    seg0.add(cell)
                    return Some(seg0)
                }
                return None
            case Some(last) =>
                if (this.grid.blocked(last, cell)) {
                    return None
                }
                if (!this.checkParity(last, cell)) {
                    return None
                }
                let seg = ArrayList<Cell>()
                match (this.level.ferry) {
                    case Some(f) =>
                        if (cell.x == f.jiaX && cell.y == f.jiaY) {
                            let yi = Cell(f.yiX, f.yiY)
                            /* 乙已在 path 里（或 乙==甲）→ 拒绝进入甲。 */
                            if (this.path.contains(yi) || (f.yiX == f.jiaX && f.yiY == f.jiaY)) {
                                return None
                            }
                            seg.add(cell)
                            seg.add(yi)
                        }
                    case None => ()
                }
                if (seg.size == 0) {
                    seg.add(cell)
                }
                if (!this.segClueOk(seg)) {
                    return None
                }
                return Some(seg)
        }
    }

    /* 整段数字格顺序检查（甲、乙 同段，按段内顺序推进 nextRequired）。 */
    func segClueOk(seg: ArrayList<Cell>): Bool {
        var n = this.nextRequired()
        var i: Int64 = 0
        while (i < seg.size) {
            let cv = this.level.numberAt(seg[i].x, seg[i].y)
            if (cv != 0 && cv != n) {
                return false
            }
            if (cv == n) {
                n = n + 1
            }
            i = i + 1
        }
        let head = seg[0]
        let headNum = this.level.numberAt(head.x, head.y)
        if (headNum == this.level.maxNumber() && this.filled() + seg.size != this.grid.cellCount()) {
            return false
        }
        return true
    }

    /* 普通格输入合法 iff expandInput 给出一段。 */
    func canEnter(cell: Cell): Bool {
        match (this.expandInput(cell)) {
            case Some(_) => return true
            case None => return false
        }
    }

    /* One input = one undo unit. Drag onto the cell the latest unit started
       from (pre-input head), or onto any non-head cell of that unit, rewinds
       the whole unit; other drags fall through to expandInput as before. */
    public func tryStep(cell: Cell): Bool {
        this.lastRejectParity = 0
        if (this.units.size > 0) {
            let startLen = this.units[this.units.size - 1]
            if (startLen > 0 && cell.equals(this.path.at(startLen - 1))) {
                this.undoUnit()
                return true
            }
            /* 本单元除头（末格）以外的格（1 格单元该范围为空）→ 撤销整个单元：
               2 格渡口单元 [甲,乙] 只查甲（乙是头，落头不撤销，走已访拒绝）。 */
            var u: Int64 = startLen
            while (u <= this.path.size() - 2) {
                if (cell.equals(this.path.at(u))) {
                    this.undoUnit()
                    return true
                }
                u = u + 1
            }
        }
        match (this.expandInput(cell)) {
            case None => return false
            case Some(seg) =>
                this.units.add(this.path.size())
                var i: Int64 = 0
                while (i < seg.size) {
                    this.path.push(seg[i])
                    i = i + 1
                }
                return true
        }
    }

    public func undo(): Bool {
        this.lastRejectParity = 0
        return this.undoUnit()
    }

    /* Rewind the latest unit: pop the path back to its startLen. */
    func undoUnit(): Bool {
        if (this.units.size == 0) {
            return false
        }
        let startLen = this.units[this.units.size - 1]
        while (this.path.size() > startLen) {
            this.path.undo()
        }
        this.units.remove(at: this.units.size - 1)
        return true
    }

    func clearUnits(): Unit {
        while (this.units.size > 0) {
            this.units.remove(at: this.units.size - 1)
        }
    }

    public func clear(): Unit {
        this.path.clear()
        this.clearUnits()
        this.lastRejectParity = 0
    }

    public func isWin(): Bool {
        let lastOpt = this.path.last()
        match (lastOpt) {
            case None => return false
            case Some(last) =>
                if (this.path.size() != this.grid.cellCount()) {
                    return false
                }
                return this.level.numberAt(last.x, last.y) == this.level.maxNumber() &&
                    this.nextRequired() == this.level.maxNumber() + 1
        }
    }
}
