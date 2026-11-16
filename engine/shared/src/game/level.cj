/* Extracted for the iOS shell. Package is yilu_zip.* so this tree does not import ohos/ArkUI.
   Behavior copy of entry/src/main/cangjie/game/level.cj. See ios/ENGINE.md. */
package yilu_zip.game

import std.collection.ArrayList
import yilu_zip.engine.{Cell, Wall}

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

/* 渡口：踏上甲的那一次输入同时铺甲与乙，落点为乙。 */
public class FerryDef {
    public var jiaX: Int64
    public var jiaY: Int64
    public var yiX: Int64
    public var yiY: Int64

    public init(jiaX: Int64, jiaY: Int64, yiX: Int64, yiY: Int64) {
        this.jiaX = jiaX
        this.jiaY = jiaY
        this.yiX = yiX
        this.yiY = yiY
    }
}

/* 单向门：该邻边只允许 from → to 正向通过。 */
public class OneWay {
    public var fromX: Int64
    public var fromY: Int64
    public var toX: Int64
    public var toY: Int64

    public init(fromX: Int64, fromY: Int64, toX: Int64, toY: Int64) {
        this.fromX = fromX
        this.fromY = fromY
        this.toX = toX
        this.toY = toY
    }
}

/* 符节闸：无向邻边，未得符不可过（locked_until_token 恒真，故不存该字段）。 */
public class SealGate {
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
}

/* 塌桥：踏上触发格后，从下一格起 (x1,y1)-(x2,y2) 断开。 */
public class CollapseDef {
    public var triggerX: Int64
    public var triggerY: Int64
    public var x1: Int64
    public var y1: Int64
    public var x2: Int64
    public var y2: Int64

    public init(triggerX: Int64, triggerY: Int64, x1: Int64, y1: Int64, x2: Int64, y2: Int64) {
        this.triggerX = triggerX
        this.triggerY = triggerY
        this.x1 = x1
        this.y1 = y1
        this.x2 = x2
        this.y2 = y2
    }
}

/* 负重：laden 时不可进禁区格；load 格装粮、unload 格卸粮。 */
public class BurdenDef {
    public var forbidden: ArrayList<Cell>
    public var loadX: Int64
    public var loadY: Int64
    public var unloadX: Int64
    public var unloadY: Int64
    public var startLaden: Bool

    public init(
        forbidden: ArrayList<Cell>,
        loadX: Int64,
        loadY: Int64,
        unloadX: Int64,
        unloadY: Int64,
        startLaden: Bool
    ) {
        this.forbidden = forbidden
        this.loadX = loadX
        this.loadY = loadY
        this.unloadX = unloadX
        this.unloadY = unloadY
        this.startLaden = startLaden
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
    /* 机制键（可选，缺省即无机制）；坐标已是引擎内部 x=列, y=行。 */
    public var ferry: Option<FerryDef> = None
    public var oneWays: ArrayList<OneWay> = ArrayList<OneWay>()
    public var slideCells: ArrayList<Cell> = ArrayList<Cell>()
    public var sealGates: ArrayList<SealGate> = ArrayList<SealGate>()
    public var tokenCells: ArrayList<Cell> = ArrayList<Cell>()
    public var collapse: Option<CollapseDef> = None
    public var burden: Option<BurdenDef> = None

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

    /* 任一机制键存在则为真（无机制关保持原行为）。 */
    public func hasMechanics(): Bool {
        var any = false
        match (this.ferry) {
            case Some(_) => any = true
            case None => ()
        }
        match (this.collapse) {
            case Some(_) => any = true
            case None => ()
        }
        match (this.burden) {
            case Some(_) => any = true
            case None => ()
        }
        if (this.oneWays.size > 0 || this.slideCells.size > 0 || this.sealGates.size > 0 || this.tokenCells.size > 0) {
            any = true
        }
        return any
    }

    public func isTokenCell(x: Int64, y: Int64): Bool {
        for (c in this.tokenCells) {
            if (c.x == x && c.y == y) {
                return true
            }
        }
        return false
    }

    /* burden 禁区格（无 burden 时恒假）。 */
    public func isForbiddenCell(x: Int64, y: Int64): Bool {
        var hit = false
        match (this.burden) {
            case None => ()
            case Some(b) =>
                for (c in b.forbidden) {
                    if (c.x == x && c.y == y) {
                        hit = true
                    }
                }
        }
        return hit
    }

    /* 该邻边是否被某条单向约束（无向匹配）。 */
    public func oneWayConstrains(a: Cell, b: Cell): Bool {
        for (ow in this.oneWays) {
            if (ow.fromX == a.x && ow.fromY == a.y && ow.toX == b.x && ow.toY == b.y) {
                return true
            }
            if (ow.fromX == b.x && ow.fromY == b.y && ow.toX == a.x && ow.toY == a.y) {
                return true
            }
        }
        return false
    }

    /* 单向只放行正向 from → to。 */
    public func oneWayAllows(from: Cell, to: Cell): Bool {
        for (ow in this.oneWays) {
            if (ow.fromX == from.x && ow.fromY == from.y && ow.toX == to.x && ow.toY == to.y) {
                return true
            }
        }
        return false
    }

    /* 该邻边是否为符节闸（无向匹配）。 */
    public func gateAt(a: Cell, b: Cell): Bool {
        for (g in this.sealGates) {
            if (g.x1 == a.x && g.y1 == a.y && g.x2 == b.x && g.y2 == b.y) {
                return true
            }
            if (g.x1 == b.x && g.y1 == b.y && g.x2 == a.x && g.y2 == a.y) {
                return true
            }
        }
        return false
    }
}
