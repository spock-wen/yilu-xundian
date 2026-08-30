package ohos_app_cangjie_entry.engine

import std.collection.ArrayList

/* Pixel layout used by touch-to-cell. Engine stays free of Canvas types. */
public class GridLayout {
    public var originX: Float64
    public var originY: Float64
    public var cellSize: Float64
    public var cols: Int64
    public var rows: Int64

    public init(originX: Float64, originY: Float64, cellSize: Float64, cols: Int64, rows: Int64) {
        this.originX = originX
        this.originY = originY
        this.cellSize = cellSize
        this.cols = cols
        this.rows = rows
    }
}

public class GridMap {
    public var cols: Int64
    public var rows: Int64
    public var walls: ArrayList<Wall>

    public init(cols: Int64, rows: Int64, walls: ArrayList<Wall>) {
        this.cols = cols
        this.rows = rows
        this.walls = walls
    }

    public func inBounds(cell: Cell): Bool {
        return cell.x >= 0 && cell.y >= 0 && cell.x < this.cols && cell.y < this.rows
    }

    public func isOrthogonalNeighbor(a: Cell, b: Cell): Bool {
        var dx = a.x - b.x
        var dy = a.y - b.y
        if (dx < 0) {
            dx = -dx
        }
        if (dy < 0) {
            dy = -dy
        }
        return dx + dy == 1
    }

    public func hasWall(a: Cell, b: Cell): Bool {
        for (wall in this.walls) {
            if (wall.matches(a, b)) {
                return true
            }
        }
        return false
    }

    public func blocked(a: Cell, b: Cell): Bool {
        return !this.isOrthogonalNeighbor(a, b) || this.hasWall(a, b)
    }

    public func cellCount(): Int64 {
        return this.cols * this.rows
    }
}

/* Convert a touch in the grid's local coordinates to a cell, or None. */
public func touchToCell(px: Float64, py: Float64, layout: GridLayout): Option<Cell> {
    if (px < layout.originX || py < layout.originY) {
        return None
    }
    let relX = px - layout.originX
    let relY = py - layout.originY
    var cx: Int64 = 0
    var cy: Int64 = 0
    while (Float64(cx + 1) * layout.cellSize <= relX) {
        cx = cx + 1
    }
    while (Float64(cy + 1) * layout.cellSize <= relY) {
        cy = cy + 1
    }
    if (cx < 0 || cy < 0 || cx >= layout.cols || cy >= layout.rows) {
        return None
    }
    return Some(Cell(cx, cy))
}
