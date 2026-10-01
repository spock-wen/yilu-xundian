/* Extracted for the iOS shell. Package is yilu_zip.* so this tree does not import ohos/ArkUI.
   Behavior copy of entry/src/main/cangjie/game/patrol.cj. See ios/ENGINE.md. */
package yilu_zip.game

import std.collection.ArrayList
import yilu_zip.engine.{Cell, GridMap, GridPath}

/* Reason of the last rejected input (0 = none); UI may toast/flash on it. */
public let REJECT_NONE: Int64 = 0
public let REJECT_PARITY: Int64 = 1
public let REJECT_ONE_WAY: Int64 = 2
public let REJECT_SEALED_GATE: Int64 = 3
public let REJECT_BURDEN_FORBIDDEN: Int64 = 4
public let REJECT_WALL: Int64 = 5
public let REJECT_VISITED: Int64 = 6
public let REJECT_WAYPOINT: Int64 = 7
public let REJECT_BOUNDS: Int64 = 8
public let REJECT_FERRY: Int64 = 9 /* 进甲被拒：乙已在 path 里（或 乙==甲）. */
public let REJECT_START: Int64 = 10 /* 首格必须是 1 号. */

/* Snapshot taken right before one input is applied; one input = one undo unit. */
public class UnitSnap {
    public var startLen: Int64
    public var hasToken: Bool
    public var laden: Bool
    public var down: Bool

    public init(startLen: Int64, hasToken: Bool, laden: Bool, down: Bool) {
        this.startLen = startLen
        this.hasToken = hasToken
        this.laden = laden
        this.down = down
    }
}

/* burden 起始载态：start_laden，无 burden 为 false (tools/solve_levels.py:497). */
func initialLadenOf(level: LevelDef): Bool {
    var l = false
    match (level.burden) {
        case Some(b) => l = b.startLaden
        case None => ()
    }
    return l
}

/* Thin Zip / 「驿路巡点」 rules on top of the reusable grid engine. */
public class PatrolGame {
    public var level: LevelDef
    public var grid: GridMap
    public var path: GridPath = GridPath()
    /* 0 = none, 1 = needs odd step, 2 = needs even step; set on parity reject so UI can toast. */
    public var lastRejectParity: Int64 = 0
    /* Reject reason + rejected edge ends (cell coords; -1 = unknown/start). */
    public var lastReject: Int64 = 0
    public var lastRejectFromX: Int64 = -1
    public var lastRejectFromY: Int64 = -1
    public var lastRejectToX: Int64 = -1
    public var lastRejectToY: Int64 = -1
    /* Mechanic run-state; each UnitSnap restores these on undo. */
    public var hasToken: Bool = false
    public var laden: Bool = false
    public var collapseDown: Bool = false /* TODO(2c): collapse trigger. */
    /* Undo units: one successful tryStep = one entry. */
    var units: ArrayList<UnitSnap> = ArrayList<UnitSnap>()

    public init(level: LevelDef) {
        this.level = level
        this.grid = GridMap(level.cols, level.rows, level.walls)
        this.laden = initialLadenOf(level) /* solve_levels.py:497 */
    }

    public func reset(level: LevelDef): Unit {
        this.level = level
        this.grid = GridMap(level.cols, level.rows, level.walls)
        this.path.clear()
        this.clearUnits()
        this.clearReject()
        this.hasToken = false
        this.laden = initialLadenOf(this.level) /* solve_levels.py:497 initial_state */
        this.collapseDown = false
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

    /* Clear reject bookkeeping; called at the head of every public entry point. */
    func clearReject(): Unit {
        this.lastReject = REJECT_NONE
        this.lastRejectParity = 0
        this.lastRejectFromX = -1
        this.lastRejectFromY = -1
        this.lastRejectToX = -1
        this.lastRejectToY = -1
    }

    /* Record `cell` as the rejected edge head (from = current head, -1 at start) and fail. */
    func rejectEdge(code: Int64, cell: Cell): Option<ArrayList<Cell>> {
        this.lastReject = code
        let lastOpt = this.path.last()
        match (lastOpt) {
            case Some(last) =>
                this.lastRejectFromX = last.x
                this.lastRejectFromY = last.y
            case None => ()
        }
        this.lastRejectToX = cell.x
        this.lastRejectToY = cell.y
        return None
    }

    /* 负重禁入：burden 存在且当前 laden 且 cell 在禁区
       (solve_levels.py:426-427 邻格 / :501-502 首格). */
    func burdenForbids(cell: Cell): Bool {
        var bad = false
        match (this.level.burden) {
            case Some(_) =>
                if (this.laden && this.level.isForbiddenCell(cell.x, cell.y)) {
                    bad = true
                }
            case None => ()
        }
        return bad
    }

    /* 对段的数字约束，一次输入产生的整段一起查：
       ① 段内路标必须按序消耗 (_seg_clue_ok, solve_levels.py:472-484，不符→false→
         REJECT_WAYPOINT)；② 最大号只能是整盘最后一格 (:577-578)，且按 Python 只查
         nxt（=seg[0]，渡口段即甲），不推广到段内其他格。
       need 取 nextRequired()（跨边前、未 push 的路径），单格段与旧实现逐位一致。 */
    func segClueOk(seg: ArrayList<Cell>): Bool {
        var n = this.nextRequired()
        var i: Int64 = 0
        while (i < seg.size) {
            let cv = this.level.numberAt(seg[i].x, seg[i].y)
            if (cv != 0 && cv != n) {
                return false
            }
            if (cv == n) {
                n = n + 1
            }
            i = i + 1
        }
        let head = seg[0]
        let headNum = this.level.numberAt(head.x, head.y)
        if (headNum == this.level.maxNumber() && this.filled() + seg.size != this.grid.cellCount()) {
            return false
        }
        return true
    }

    /* Cells visited by one input `cell`, or None when illegal (sets lastReject*).
       Mirrors Rules.expand in tools/solve_levels.py, keeping the legacy canEnter
       check order (已访 before 奇偶 so lastRejectParity behaves as before). */
    func expandInput(cell: Cell): Option<ArrayList<Cell>> {
        this.clearReject()
        if (!this.grid.inBounds(cell)) {
            return this.rejectEdge(REJECT_BOUNDS, cell)
        }
        if (this.path.contains(cell)) {
            return this.rejectEdge(REJECT_VISITED, cell)
        }
        let lastOpt = this.path.last()
        match (lastOpt) {
            case None =>
                if (this.level.numberAt(cell.x, cell.y) == 1) {
                    // start_laden 时首格不可在禁区 (solve_levels.py:501-502, 在起点效果 :503 之前).
                    if (this.burdenForbids(cell)) {
                        return this.rejectEdge(REJECT_BURDEN_FORBIDDEN, cell)
                    }
                    let seg0 = ArrayList<Cell>()
                    seg0.add(cell)
                    return Some(seg0)
                }
                return this.rejectEdge(REJECT_START, cell)
            case Some(last) =>
                if (this.grid.blocked(last, cell)) {
                    return this.rejectEdge(REJECT_WALL, cell)
                }
                // TODO(2c collapse): collapsed edge closed here, before gates
                //   (solve_levels.py:418-419); not implemented yet.
                // TODO(2c slide): _expand step 6 forced slide segment, :563-568.
                // 闸门：无符不过 (solve_levels.py:420-421)；hasToken 取本次输入入口值.
                if (this.level.gateAt(last, cell) && !this.hasToken) {
                    return this.rejectEdge(REJECT_SEALED_GATE, cell)
                }
                if (!this.checkParity(last, cell)) { /* solve_levels.py:422-423 */
                    return this.rejectEdge(REJECT_PARITY, cell)
                }
                // 单向：边受约束且非 from→to 即拒 (solve_levels.py:424-425).
                if (this.level.oneWayConstrains(last, cell) && !this.level.oneWayAllows(last, cell)) {
                    return this.rejectEdge(REJECT_ONE_WAY, cell)
                }
                // 负重：laden 时不可进禁区格 (solve_levels.py:426-427).
                if (this.burdenForbids(cell)) {
                    return this.rejectEdge(REJECT_BURDEN_FORBIDDEN, cell)
                }
                // 渡口步骤 4（进甲，solve_levels.py:552-560）：墙/闸/奇偶/单向/负重
                // 禁区均是针对「当前头→甲」这条边（filled 取跨边前），已访查在函数头。
                let seg = ArrayList<Cell>()
                match (this.level.ferry) {
                    case Some(f) =>
                        if (cell.x == f.jiaX && cell.y == f.jiaY) {
                            let yi = Cell(f.yiX, f.yiY)
                            // 乙已在 path 里（或 乙==甲）→ 拒绝，端点 to=甲.
                            if (this.path.contains(yi) || (f.yiX == f.jiaX && f.yiY == f.jiaY)) {
                                return this.rejectEdge(REJECT_FERRY, cell)
                            }
                            // burden 存在且 laden 且 乙 在禁区 → 拒绝，端点 to=甲.
                            if (this.burdenForbids(yi)) {
                                return this.rejectEdge(REJECT_BURDEN_FORBIDDEN, cell)
                            }
                            // 跳接甲→乙豁免墙/单向/闸/奇偶/塌桥；一次输入推两格.
                            seg.add(cell)
                            seg.add(yi)
                        }
                    case None => ()
                }
                if (seg.size == 0) {
                    seg.add(cell)
                }
                if (!this.segClueOk(seg)) {
                    return this.rejectEdge(REJECT_WAYPOINT, cell)
                }
                return Some(seg)
        }
    }

    /* Thin wrapper over expandInput: a plain-cell input exists iff it yields Some. */
    func canEnter(cell: Cell): Bool {
        match (this.expandInput(cell)) {
            case Some(_) => return true
            case None => return false
        }
    }

    /* One input = one undo unit. Drag onto the cell the latest unit started
       from (pre-input head), or onto any non-head cell of that unit, rewinds
       the whole unit; other drags fall through to expandInput as before. */
    public func tryStep(cell: Cell): Bool {
        this.clearReject()
        if (this.units.size > 0) {
            let unit = this.units[this.units.size - 1]
            if (unit.startLen > 0 && cell.equals(this.path.at(unit.startLen - 1))) {
                this.undoUnit()
                return true
            }
            // 本单元除头（末格）以外的格（1 格单元该范围为空）→ 撤销整个单元：
            // 2 格渡口单元 [甲,乙] 只查甲（乙是头，落头不撤销，走已访拒绝）.
            var u: Int64 = unit.startLen
            while (u <= this.path.size() - 2) {
                if (cell.equals(this.path.at(u))) {
                    this.undoUnit()
                    return true
                }
                u = u + 1
            }
        }
        match (this.expandInput(cell)) {
            case None => return false
            case Some(seg) =>
                this.units.add(UnitSnap(this.path.size(), this.hasToken, this.laden, this.collapseDown))
                var i: Int64 = 0
                while (i < seg.size) {
                    this.path.push(seg[i])
                    i = i + 1
                }
                this.applyEntryEffects(seg)
                return true
        }
    }

    public func undo(): Bool {
        this.clearReject()
        return this.undoUnit()
    }

    /* Rewind the latest unit: pop the path back to its startLen and restore the
       snapshot (token/laden/down). Undo is pure rewind — never hits one-way gates. */
    func undoUnit(): Bool {
        if (this.units.size == 0) {
            return false
        }
        let unit = this.units[this.units.size - 1]
        while (this.path.size() > unit.startLen) {
            this.path.undo()
        }
        this.hasToken = unit.hasToken
        this.laden = unit.laden
        this.collapseDown = unit.down
        this.units.remove(at: this.units.size - 1)
        return true
    }

    func clearUnits(): Unit {
        while (this.units.size > 0) {
            this.units.remove(at: this.units.size - 1)
        }
    }

    public func clear(): Unit {
        this.path.clear()
        this.clearUnits()
        this.clearReject()
        this.hasToken = false
        this.laden = initialLadenOf(this.level) /* same as reset(): solve_levels.py:497 */
        this.collapseDown = false
    }

    /* State changes caused by landing a whole input: per-cell 装→laden=true、
       卸→laden=false (solve_levels.py:390-399 _cell_effects, applied cell by
       cell in apply() :594-598), then the token pickup only after the whole
       segment (:610) — a gate crossed in the same input still sees the entry
       hasToken. TODO(2c collapse): 踏触发格 → collapseDown (:397-398). */
    func applyEntryEffects(seg: ArrayList<Cell>): Unit {
        var i: Int64 = 0
        while (i < seg.size) {
            let c = seg[i]
            match (this.level.burden) {
                case Some(b) =>
                    if (c.x == b.loadX && c.y == b.loadY) {
                        this.laden = true
                    }
                    if (c.x == b.unloadX && c.y == b.unloadY) {
                        this.laden = false
                    }
                case None => ()
            }
            // TODO(2c collapse): trigger cell → collapseDown (solve_levels.py:397-398).
            i = i + 1
        }
        var tok = this.hasToken
        var j: Int64 = 0
        while (j < seg.size) {
            if (this.level.isTokenCell(seg[j].x, seg[j].y)) {
                tok = true
            }
            j = j + 1
        }
        this.hasToken = tok
    }

    /* 渡口关「必须走甲→乙 才算赢」保持为设计解的有效性条件，不在引擎 isWin 里查：
       甲只能经跳接触发进入，满盘铺满即隐含已用渡口 (对照 solve_levels.py:625-626). */
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
