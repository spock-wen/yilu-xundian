package ohos_app_cangjie_entry.engine

/* Growing orthogonal path backed by the reusable undo stack. */
public class GridPath {
    let stack = UndoStack<Cell>()

    public init() {}

    public func push(cell: Cell): Unit {
        this.stack.push(cell)
    }

    public func undo(): Option<Cell> {
        return this.stack.pop()
    }

    public func clear(): Unit {
        this.stack.clear()
    }

    public func last(): Option<Cell> {
        return this.stack.peek()
    }

    public func prev(): Option<Cell> {
        return this.stack.peekOffset(1)
    }

    public func contains(cell: Cell): Bool {
        var i: Int64 = 0
        while (i < this.stack.size()) {
            if (this.stack.at(i).equals(cell)) {
                return true
            }
            i = i + 1
        }
        return false
    }

    public func size(): Int64 {
        return this.stack.size()
    }

    public func at(index: Int64): Cell {
        return this.stack.at(index)
    }
}
