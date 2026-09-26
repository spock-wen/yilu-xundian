/* Extracted for the iOS shell. Package is yilu_zip.* so this tree does not import ohos/ArkUI.
   Behavior copy of entry/src/main/cangjie/engine/cell.cj. See ios/ENGINE.md. */
package yilu_zip.engine

/* Reusable grid cell. x = column, y = row, origin top-left. */
public class Cell {
    public var x: Int64
    public var y: Int64

    public init(x: Int64, y: Int64) {
        this.x = x
        this.y = y
    }

    public func equals(other: Cell): Bool {
        return this.x == other.x && this.y == other.y
    }
}
