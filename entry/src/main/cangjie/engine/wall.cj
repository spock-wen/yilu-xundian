package ohos_app_cangjie_entry.engine

/* Orthogonal edge between two adjacent cells. */
public class Wall {
    public var x1: Int64
    public var y1: Int64
    public var x2: Int64
    public var y2: Int64

    public init(x1: Int64, y1: Int64, x2: Int64, y2: Int64) {
        this.x1 = x1
        this.y1 = y1
        this.x2 = x2
        this.y2 = y2
    }

    public func matches(a: Cell, b: Cell): Bool {
        let same = (this.x1 == a.x && this.y1 == a.y && this.x2 == b.x && this.y2 == b.y)
        let rev = (this.x1 == b.x && this.y1 == b.y && this.x2 == a.x && this.y2 == a.y)
        return same || rev
    }
}
