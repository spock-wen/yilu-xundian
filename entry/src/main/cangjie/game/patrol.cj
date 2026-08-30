package ohos_app_cangjie_entry.game

import ohos_app_cangjie_entry.engine.{Cell, GridMap, GridPath}

/* Thin Zip / 「驿路巡点」 rules on top of the reusable grid engine. */
public class PatrolGame {
    public var level: LevelDef
    public var grid: GridMap
    public var path: GridPath = GridPath()

    public init(level: LevelDef) {
        this.level = level
        this.grid = GridMap(level.cols, level.rows, level.walls)
    }

    public func reset(level: LevelDef): Unit {
        this.level = level
        this.grid = GridMap(level.cols, level.rows, level.walls)
        this.path.clear()
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

    func canEnter(cell: Cell): Bool {
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
        let removed = this.path.undo()
        match (removed) {
            case Some(cell) => return cell.equals(cell)
            case None => return false
        }
    }

    public func clear(): Unit {
        this.path.clear()
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
