/* Extracted for the iOS shell. Package is yilu_zip.* so this tree does not import ohos/ArkUI.
   Behavior copy of entry/src/main/cangjie/game/patrol.cj. See ios/ENGINE.md. */
package yilu_zip.game

import yilu_zip.engine.{Cell, GridMap, GridPath}

/* Thin Zip / 「驿路巡点」 rules on top of the reusable grid engine. */
public class PatrolGame {
    public var level: LevelDef
    public var grid: GridMap
    public var path: GridPath = GridPath()
    /* 0 = none, 1 = needs odd step, 2 = needs even step; set on parity reject so UI can toast. */
    public var lastRejectParity: Int64 = 0

    public init(level: LevelDef) {
        this.level = level
        this.grid = GridMap(level.cols, level.rows, level.walls)
    }

    public func reset(level: LevelDef): Unit {
        this.level = level
        this.grid = GridMap(level.cols, level.rows, level.walls)
        this.path.clear()
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

    func canEnter(cell: Cell): Bool {
        this.lastRejectParity = 0
        if (!this.grid.inBounds(cell)) {
            return false
        }
        if (this.path.contains(cell)) {
            return false
        }
        let lastOpt = this.path.last()
        match (lastOpt) {
            case None =>
                return this.level.numberAt(cell.x, cell.y) == 1
            case Some(last) =>
                if (this.grid.blocked(last, cell)) {
                    return false
                }
                if (!this.checkParity(last, cell)) {
                    return false
                }
                let num = this.level.numberAt(cell.x, cell.y)
                let nxt = this.nextRequired()
                if (num != 0 && num != nxt) {
                    return false
                }
                if (num == this.level.maxNumber() && this.path.size() + 1 != this.grid.cellCount()) {
                    return false
                }
                return true
        }
    }

    /* Drag onto the previous cell undoes the last step (Zip-style). */
    public func tryStep(cell: Cell): Bool {
        this.lastRejectParity = 0
        let prevOpt = this.path.prev()
        match (prevOpt) {
            case Some(prev) =>
                if (cell.equals(prev)) {
                    this.path.undo()
                    return true
                }
            case None => ()
        }
        if (this.canEnter(cell)) {
            this.path.push(cell)
            return true
        }
        return false
    }

    public func undo(): Bool {
        this.lastRejectParity = 0
        let removed = this.path.undo()
        match (removed) {
            case Some(cell) => return cell.equals(cell)
            case None => return false
        }
    }

    public func clear(): Unit {
        this.path.clear()
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
