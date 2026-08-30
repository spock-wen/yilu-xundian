package ohos_app_cangjie_entry.game

import std.collection.ArrayList
import ohos_app_cangjie_entry.engine.Wall

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

public class LevelDef {
    public var id: Int64
    public var name: String
    public var cols: Int64
    public var rows: Int64
    public var waypoints: ArrayList<Waypoint>
    public var walls: ArrayList<Wall>

    public init(
        id: Int64,
        name: String,
        cols: Int64,
        rows: Int64,
        waypoints: ArrayList<Waypoint>,
        walls: ArrayList<Wall>
    ) {
        this.id = id
        this.name = name
        this.cols = cols
        this.rows = rows
        this.waypoints = waypoints
        this.walls = walls
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
