package ohos_app_cangjie_entry.engine

import std.collection.ArrayList

/* UI-free undo stack. Reusable for any grid game. */
public class UndoStack<T> {
    var items: ArrayList<T> = ArrayList<T>()

    public init() {}

    public func push(item: T): Unit {
        this.items.add(item)
    }

    public func pop(): Option<T> {
        if (this.items.size == 0) {
            return None
        }
        let last = this.items[this.items.size - 1]
        this.items.remove(at: this.items.size - 1)
        return Some(last)
    }

    public func peek(): Option<T> {
        if (this.items.size == 0) {
            return None
        }
        return Some(this.items[this.items.size - 1])
    }

    public func peekOffset(fromEnd: Int64): Option<T> {
        if (fromEnd < 0 || fromEnd >= this.items.size) {
            return None
        }
        return Some(this.items[this.items.size - 1 - fromEnd])
    }

    public func clear(): Unit {
        while (this.items.size > 0) {
            this.items.remove(at: this.items.size - 1)
        }
    }

    public func size(): Int64 {
        return this.items.size
    }

    public func at(index: Int64): T {
        return this.items[index]
    }
}
