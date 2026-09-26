package ohos_app_cangjie_entry.game

import std.collection.ArrayList
import ohos_app_cangjie_entry.engine.{Cell, Wall}

public class Waypoint {
    public var n: Int64
    public var x: Int64
    public var y: Int64

    public init(n: Int64, x: Int64, y: Int64) {
        this.n = n
        this.x = x
        this.y = y
    }
}

/* Parity gate on the orthogonal edge between two cells (require odd or even step). */
public class ParityEdge {
    public var x1: Int64
    public var y1: Int64
    public var x2: Int64
    public var y2: Int64
    public var requireOdd: Bool
    public var requireEven: Bool

    public init(x1: Int64, y1: Int64, x2: Int64, y2: Int64, requireOdd: Bool, requireEven: Bool) {
        this.x1 = x1
        this.y1 = y1
        this.x2 = x2
        this.y2 = y2
        this.requireOdd = requireOdd
        this.requireEven = requireEven
    }

    public func matches(a: Cell, b: Cell): Bool {
        let same = (this.x1 == a.x && this.y1 == a.y && this.x2 == b.x && this.y2 == b.y)
        let rev = (this.x1 == b.x && this.y1 == b.y && this.x2 == a.x && this.y2 == a.y)
        return same || rev
    }
}

public class LevelDef {
    public var id: Int64
    public var name: String
    public var cols: Int64
    public var rows: Int64
    public var waypoints: ArrayList<Waypoint>
    public var walls: ArrayList<Wall>
    public var parityEdges: ArrayList<ParityEdge>
    public var stepLimit: Int64

    public init(
        id: Int64,
        name: String,
        cols: Int64,
        rows: Int64,
        waypoints: ArrayList<Waypoint>,
        walls: ArrayList<Wall>,
        parityEdges: ArrayList<ParityEdge>,
        stepLimit: Int64
    ) {
        this.id = id
        this.name = name
        this.cols = cols
        this.rows = rows
        this.waypoints = waypoints
        this.walls = walls
        this.parityEdges = parityEdges
        this.stepLimit = stepLimit
    }

    public func numberAt(x: Int64, y: Int64): Int64 {
        for (wp in this.waypoints) {
            if (wp.x == x && wp.y == y) {
                return wp.n
            }
        }
        return 0
    }

    public func maxNumber(): Int64 {
        var maxN: Int64 = 0
        for (wp in this.waypoints) {
            if (wp.n > maxN) {
                maxN = wp.n
            }
        }
        return maxN
    }
}
