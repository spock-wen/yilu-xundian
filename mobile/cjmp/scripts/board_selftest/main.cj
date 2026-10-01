package ohos_app_cangjie_entry

import std.fs.*
import std.collection.ArrayList
import std.math.*
import ohos_app_cangjie_entry.engine.*
import ohos_app_cangjie_entry.game.*

/*
 * box-only selftest for board/board_mech builders (task T1). Not a repo artifact.
 * usage: main <levels.json> <inputs.txt>; prints SELFTEST line, exit 0 iff no failure.
 */

class Ctx {
    public let failures = ArrayList<String>()
    public let rej: Array<Int64> = Array<Int64>(11, repeat: 0)
    public var checks: Int64 = 0
    public var steps: Int64 = 0
    public var levels: Int64 = 0

    public init() {}

    public func ck(cond: Bool, msg: String) {
        this.checks = this.checks + 1
        if (!cond) {
            this.failures.add(msg)
        }
    }
}

func absF(v: Float64): Float64 {
    if (v < 0.0) {
        return -v
    }
    return v
}

/* commands 是否以 'M' 起头（String.get 按字节取，同 helpers.cj/digits.cj）。 */
func startsWithM(s: String): Bool {
    if (s.size == 0) {
        return false
    }
    match (s.get(0)) {
        case Some(b) => return b == 77u8
        case None => return false
    }
}

/* 取出 [start,end) 内所有 ASCII 非负整数（分隔符任意）。 */
func lineInts(b: Array<UInt8>, start: Int64, end: Int64): Array<Int64> {
    let out = ArrayList<Int64>()
    var i = start
    var cur: Int64 = 0
    var has = false
    while (i < end) {
        let c = b[i]
        if (c >= 48u8 && c <= 57u8) {
            cur = cur * 10 + (Int64(c) - 48)
            has = true
        } else {
            if (has) {
                out.add(cur)
                cur = 0
                has = false
            }
        }
        i = i + 1
    }
    if (has) {
        out.add(cur)
    }
    return out.toArray()
}

/* 断言 T1 的 1~8 项；违例追加到 ctx.failures（"FAIL id=.. step=.. 说明"）。 */
func checkAll(game: PatrolGame, geom: BoardGeom, lv: LevelDef, id: Int64, step: Int64, ctx: Ctx) {
    let tag = "FAIL id=${id} step=${step}"
    /* 1. cells 数量 + 泽色计数 */
    let cells = buildBoardCells(game, geom)
    ctx.ck(cells.size == lv.cols * lv.rows, "${tag} cells=${cells.size} want=${lv.cols * lv.rows}")
    var ze: Int64 = 0
    for (r in cells) {
        if (r.color == Theme.ze) {
            ze = ze + 1
        }
    }
    ctx.ck(ze == lv.slideCells.size, "${tag} ze=${ze} slideCells=${lv.slideCells.size}")
    /* 2. route 每段 ≈ pitch，条数 ≤ path-1 */
    let route = buildBoardRoute(game, geom)
    let pitch = geom.pitch()
    for (s in route) {
        let dx = s.x2 - s.x1
        let dy = s.y2 - s.y1
        let len = sqrt(dx * dx + dy * dy)
        ctx.ck(absF(len - pitch) < 0.01, "${tag} route len=${len} pitch=${pitch}")
    }
    var maxSegs: Int64 = 0
    if (game.path.size() >= 1) {
        maxSegs = game.path.size() - 1
    }
    ctx.ck(route.size <= maxSegs, "${tag} route segs=${route.size} max=${maxSegs}")
    /* 3. gates */
    let gates = buildBoardGates(game, geom)
    ctx.ck(gates.size == lv.oneWays.size, "${tag} gates=${gates.size} oneWays=${lv.oneWays.size}")
    /* 4. mech dots：渡口 4 个 */
    var hasFerry = false
    match (lv.ferry) {
        case Some(_) => hasFerry = true
        case None => ()
    }
    let dots = buildBoardMechDots(game, geom)
    var wantDots: Int64 = 0
    if (hasFerry) {
        wantDots = 4
    }
    ctx.ck(dots.size == wantDots, "${tag} dots=${dots.size} want=${wantDots}")
    /* 5. mech walls：闸(sealGates×1/2) + 塌桥断边 */
    var sealN: Int64 = 0
    if (game.hasToken) {
        sealN = lv.sealGates.size * 2
    } else {
        sealN = lv.sealGates.size
    }
    var colN: Int64 = 0
    match (lv.collapse) {
        case Some(cd) =>
            if (game.isEdgeCollapsed(cd.x1, cd.y1, cd.x2, cd.y2)) {
                colN = 1
            }
        case None => ()
    }
    let walls = buildBoardMechWalls(game, geom)
    let wantWalls = sealN + colN
    ctx.ck(walls.size == wantWalls, "${tag} walls=${walls.size} want=${wantWalls}")
    /* 6. labels = 渡3 + 开闸 + 符 + 滑 + 停[0..滑数] */
    let labels = buildBoardMechLabels(game, geom)
    var base: Int64 = 0
    if (hasFerry) {
        base = 3
    }
    if (game.hasToken) {
        base = base + lv.sealGates.size
    }
    base = base + lv.tokenCells.size + lv.slideCells.size
    let stopN = labels.size - base
    ctx.ck(stopN >= 0 && stopN <= lv.slideCells.size, "${tag} labels=${labels.size} base=${base} stop=${stopN} slides=${lv.slideCells.size}")
    /* 7. paths：commands 非空且以 M 起头 */
    let paths = buildBoardMechPaths(game, geom, 3.0)
    for (p in paths) {
        ctx.ck(startsWithM(p.commands), "${tag} path cmds not M: '${p.commands}'")
    }
    /* 7b. J13 滑行 chevron：qingDeep 粗折线出现(滑入时)、白色 chevron 不再出现 */
    var wantChev: Int64 = 0
    var ci: Int64 = 1
    while (ci < game.path.size()) {
        let pc = game.path.at(ci)
        if (isSlideCellOf(lv, pc.x, pc.y)) {
            let pr = game.path.at(ci - 1)
            var adx = pc.x - pr.x
            var ady = pc.y - pr.y
            if (adx < 0) {
                adx = -adx
            }
            if (ady < 0) {
                ady = -ady
            }
            if (adx + ady == 1) {
                wantChev = wantChev + 1
            }
        }
        ci = ci + 1
    }
    var hasQing = false
    var qingCmds = ""
    var hasWhiteChev = false
    for (p in paths) {
        if (p.color == Theme.qingDeep) {
            hasQing = true
            qingCmds = p.commands
        }
        /* 旧白色 chevron 特征：color 与 stroke 同为 whitePaper(挂锁 path 的 stroke 是 ink) */
        if (p.color == Theme.whitePaper && p.stroke == Theme.whitePaper) {
            hasWhiteChev = true
        }
    }
    if (wantChev > 0) {
        ctx.ck(hasQing && qingCmds.size > 0, "${tag} chevron qingDeep missing want=${wantChev}")
        ctx.ck(!hasWhiteChev, "${tag} white slide chevron still present")
    } else {
        ctx.ck(!hasQing, "${tag} qingDeep chevron without slide entry")
    }
    /* 7c. J13 滑 标记：墨色、字号 12.2vp 绝对值 */
    for (l in labels) {
        if (l.text == "滑") {
            ctx.ck(l.color == Theme.ink, "${tag} hua label color=${l.color} want=${Theme.ink}")
            ctx.ck(absF(l.size - 12.2) < 0.01, "${tag} hua label size=${l.size} want=12.2")
        }
    }
    /* 8. 无机制关：3~7 长度全 0 */
    if (!lv.hasMechanics()) {
        ctx.ck(gates.size == 0 && dots.size == 0 && walls.size == 0 && labels.size == 0 && paths.size == 0,
            "${tag} no-mech nonzero g=${gates.size} d=${dots.size} w=${walls.size} l=${labels.size} p=${paths.size}")
    }
}

/* 「拒绝闪」模糊测试：对头格 4 邻格逐个 tryStep，校验 flash/toast/状态可恢复。 */
func fuzz(game: PatrolGame, id: Int64, step: Int64, ctx: Ctx) {
    let n = game.path.size()
    if (n < 1) {
        return /* 空盘无头格，无可探测邻格 */
    }
    let head = game.path.at(n - 1)
    let hx = head.x
    let hy = head.y
    let tag = "FAIL id=${id} step=${step} head=${hx},${hy}"
    let snap = ArrayList<Cell>()
    var i: Int64 = 0
    while (i < n) {
        snap.add(game.path.at(i))
        i = i + 1
    }
    var k: Int64 = 0
    while (k < 4) {
        var nx = hx
        var ny = hy
        if (k == 0) {
            ny = hy - 1
        }
        if (k == 1) {
            ny = hy + 1
        }
        if (k == 2) {
            nx = hx - 1
        }
        if (k == 3) {
            nx = hx + 1
        }
        let ok = game.tryStep(Cell(nx, ny))
        let after = game.path.size()
        if (ok) {
            ctx.ck(after != n, "${tag} probe ${nx},${ny} true but size=${after} unchanged")
            if (after > n) {
                game.undo() /* 合法新步：一次输入=一个撤销单元 */
            }
            if (after < n) {
                /* tryStep 把上一输入单元整段回卷（拖拽撤销）：重放该单元的输入格恢复 */
                let again = game.tryStep(snap.get(after).getOrThrow())
                ctx.ck(again, "${tag} probe ${nx},${ny} rewind replay rejected")
            }
            ctx.ck(game.path.size() == n, "${tag} probe ${nx},${ny} size=${game.path.size()} want=${n}")
        } else {
            let code = game.lastReject
            if (code >= 0 && code <= 10) {
                ctx.rej[code] = ctx.rej[code] + 1
            }
            var expect = false
            if (code == 1 || code == 2 || code == 3 || code == 4 || code == 9) {
                let ax = game.lastRejectFromX
                let ay = game.lastRejectFromY
                let bx = game.lastRejectToX
                let by = game.lastRejectToY
                if (ax >= 0 && ay >= 0 && bx >= 0 && by >= 0) {
                    let dx = bx - ax
                    let dy = by - ay
                    var adx = dx
                    var ady = dy
                    if (adx < 0) {
                        adx = -adx
                    }
                    if (ady < 0) {
                        ady = -ady
                    }
                    expect = (adx + ady == 1)
                }
            }
            ctx.ck(rejectShouldFlash(game) == expect, "${tag} code=${code} flash=${rejectShouldFlash(game)} want=${expect}")
            if (rejectShouldFlash(game)) {
                ctx.ck(game.lastRejectFromX == hx && game.lastRejectFromY == hy,
                    "${tag} code=${code} from=${game.lastRejectFromX},${game.lastRejectFromY} head=${hx},${hy}")
            }
            if (rejectShouldFlash(game) && code == 1) {
                ctx.ck(parityToastText(game).size > 0, "${tag} parity toast empty")
            }
        }
        k = k + 1
    }
    ctx.ck(game.path.size() == n, "${tag} fuzz left size=${game.path.size()} want=${n}")
}

/* 一行 "<id> x,y x,y ..."：重放该关全部输入，逐步 checkAll + 拒绝闪模糊测试。 */
func runLine(b: Array<UInt8>, start: Int64, end: Int64, levels: ArrayList<LevelDef>, ctx: Ctx) {
    let nums = lineInts(b, start, end)
    if (nums.size == 0) {
        return
    }
    ctx.levels = ctx.levels + 1
    let id = nums[0]
    if (id < 0 || id >= levels.size) {
        ctx.ck(false, "FAIL id=${id} level out of range 0..${levels.size - 1}")
        return
    }
    let lv = levels.get(id).getOrThrow()
    let geom = BoardGeom(43.0, lv.cols, lv.rows)
    let game = PatrolGame(lv)
    checkAll(game, geom, lv, id, 0, ctx)
    fuzz(game, id, 0, ctx)
    var step: Int64 = 0
    var i: Int64 = 1
    while (i + 1 < nums.size) {
        let x = nums[i]
        let y = nums[i + 1]
        i = i + 2
        step = step + 1
        ctx.steps = ctx.steps + 1
        if (!game.tryStep(Cell(x, y))) {
            ctx.ck(false, "FAIL id=${id} step=${step} tryStep ${x},${y} rejected code=${game.lastReject}")
            return
        }
        checkAll(game, geom, lv, id, step, ctx)
        fuzz(game, id, step, ctx)
    }
    ctx.ck(game.isWin(), "FAIL id=${id} step=${step} isWin false path=${game.path.size()} want=${lv.cols * lv.rows}")
}

/* ===== T2 定向拒绝闪自测 ===== */

/* 计数:directedRejectTests 写入,main 打印 DIRECTED 行。 */
class DStat {
    public var flash: Int64 = 0
    public var noflash: Int64 = 0
    public var fails: Int64 = 0
    public var checks: Int64 = 0

    public init() {}
}

let dStat = DStat()

/* 手工小棋盘(同 shared-test mkLevel 写法):clues=(n,x,y) 即 (编号,列,行)。 */
func mkTiny(cols: Int64, rows: Int64, clues: Array<(Int64, Int64, Int64)>): LevelDef {
    let wps = ArrayList<Waypoint>()
    for (c in clues) {
        wps.add(Waypoint(c[0], c[1], c[2]))
    }
    return LevelDef(0, "t", cols, rows, wps, ArrayList<Wall>(), ArrayList<ParityEdge>(), cols * rows)
}

/* 依次 tryStep 布置前置步骤;任一被拒则记失败并 false。 */
func dirSteps(fails: ArrayList<String>, g: PatrolGame, name: String, cells: Array<(Int64, Int64)>): Bool {
    for (c in cells) {
        dStat.checks = dStat.checks + 1
        if (!g.tryStep(Cell(c[0], c[1]))) {
            fails.add("FAIL directed ${name}: setup ${c[0]},${c[1]} rejected code=${g.lastReject}")
            return false
        }
    }
    return true
}

/* 期望 cell 被拒:校验 code/端点/flash/(奇偶)toast,累计 flash|noflash 计数。 */
func dirExpect(fails: ArrayList<String>, g: PatrolGame, name: String, cell: Cell,
               code: Int64, wantFlash: Bool, fx: Int64, fy: Int64, tx: Int64, ty: Int64, toast: Bool) {
    var bad = ""
    dStat.checks = dStat.checks + 1
    if (g.tryStep(cell)) {
        bad = "step ${cell.x},${cell.y} accepted; "
    }
    dStat.checks = dStat.checks + 1
    if (g.lastReject != code) {
        bad = "${bad}code=${g.lastReject} want=${code}; "
    }
    dStat.checks = dStat.checks + 1
    if (g.lastRejectFromX != fx || g.lastRejectFromY != fy) {
        bad = "${bad}from=${g.lastRejectFromX},${g.lastRejectFromY} want=${fx},${fy}; "
    }
    dStat.checks = dStat.checks + 1
    if (g.lastRejectToX != tx || g.lastRejectToY != ty) {
        bad = "${bad}to=${g.lastRejectToX},${g.lastRejectToY} want=${tx},${ty}; "
    }
    let fl = rejectShouldFlash(g)
    if (fl) {
        dStat.flash = dStat.flash + 1
    } else {
        dStat.noflash = dStat.noflash + 1
    }
    dStat.checks = dStat.checks + 1
    if (fl != wantFlash) {
        bad = "${bad}flash=${fl} want=${wantFlash}; "
    }
    if (toast) {
        dStat.checks = dStat.checks + 1
        if (parityToastText(g).size == 0) {
            bad = "${bad}parity toast empty; "
        }
    }
    if (bad != "") {
        dStat.fails = dStat.fails + 1
        fails.add("FAIL directed ${name}: ${bad}")
    }
}

/* T2 定向拒绝闪:机制类(奇偶/单向/闸/负禁/渡口)拒则闪,其余拒不闪。返回失败拼串(空=通过)。 */
func directedRejectTests(): String {
    let fails = ArrayList<String>()
    dStat.flash = 0
    dStat.noflash = 0
    dStat.fails = 0
    dStat.checks = 0
    /* (1) 单向:号1@(1,0),边只允许 0→1,反向 (1,0)→(0,0) 拒且闪。 */
    let l1 = mkTiny(3, 1, [(1, 1, 0)])
    l1.oneWays.add(OneWay(0, 0, 1, 0))
    let g1 = PatrolGame(l1)
    if (dirSteps(fails, g1, "oneway", [(1, 0)])) {
        dirExpect(fails, g1, "oneway", Cell(0, 0), REJECT_ONE_WAY, true, 1, 0, 0, 0, false)
    }
    /* (2) 闸:无符过闸 (0,0)→(1,0) 拒且闪。 */
    let l2 = mkTiny(3, 1, [(1, 0, 0), (2, 2, 0)])
    l2.sealGates.add(SealGate(0, 0, 1, 0))
    let g2 = PatrolGame(l2)
    if (dirSteps(fails, g2, "seal", [(0, 0)])) {
        dirExpect(fails, g2, "seal", Cell(1, 0), REJECT_SEALED_GATE, true, 0, 0, 1, 0, false)
    }
    /* (3) 负重:踏装粮点 (0,0) → laden,负重进禁区 (1,0) 拒且闪。 */
    let l3 = mkTiny(3, 1, [(1, 0, 0), (2, 2, 0)])
    let forb = ArrayList<Cell>()
    forb.add(Cell(1, 0))
    l3.burden = Some(BurdenDef(forb, 0, 0, 2, 0, false))
    let g3 = PatrolGame(l3)
    if (dirSteps(fails, g3, "burden", [(0, 0)])) {
        dStat.checks = dStat.checks + 1
        if (!g3.laden) {
            fails.add("FAIL directed burden: not laden after load cell (0,0)")
        }
        dirExpect(fails, g3, "burden", Cell(1, 0), REJECT_BURDEN_FORBIDDEN, true, 0, 0, 1, 0, false)
    }
    /* (4) 渡口:乙已访再进甲 → REJECT_FERRY,from=头(乙),to=甲,闪(抄 ferry_test b)。 */
    let l4 = mkTiny(3, 2, [(1, 0, 0)])
    l4.ferry = Some(FerryDef(1, 0, 1, 1))
    let g4 = PatrolGame(l4)
    if (dirSteps(fails, g4, "ferry", [(0, 0), (0, 1), (1, 1)])) {
        dirExpect(fails, g4, "ferry", Cell(1, 0), REJECT_FERRY, true, 1, 1, 1, 0, false)
    }
    /* (5) 奇偶:requireOdd 边在 filled 偶数步拒,闪且 toast 非空。 */
    let l5 = mkTiny(3, 1, [(1, 0, 0), (2, 1, 0), (3, 2, 0)])
    l5.parityEdges.add(ParityEdge(0, 0, 1, 0, true, false)) /* 踩 (1,0) filled=1 奇,放行 */
    l5.parityEdges.add(ParityEdge(1, 0, 2, 0, true, false)) /* 踩 (2,0) filled=2 偶,拒绝 */
    let g5 = PatrolGame(l5)
    if (dirSteps(fails, g5, "parity", [(0, 0), (1, 0)])) {
        dirExpect(fails, g5, "parity", Cell(2, 0), REJECT_PARITY, true, 1, 0, 2, 0, true)
    }
    /* (6) 不闪:墙。 */
    let l6 = mkTiny(3, 1, [(1, 0, 0), (2, 2, 0)])
    l6.walls.add(Wall(0, 0, 1, 0))
    let g6 = PatrolGame(l6)
    if (dirSteps(fails, g6, "wall", [(0, 0)])) {
        dirExpect(fails, g6, "wall", Cell(1, 0), REJECT_WALL, false, 0, 0, 1, 0, false)
    }
    /* 不闪:回踏唯一头格 (path.size==1,起点即头) → VISITED。 */
    let g6b = PatrolGame(mkTiny(3, 1, [(1, 0, 0), (2, 2, 0)]))
    if (dirSteps(fails, g6b, "visited", [(0, 0)])) {
        dirExpect(fails, g6b, "visited", Cell(0, 0), REJECT_VISITED, false, 0, 0, 0, 0, false)
    }
    /* 不闪:越界 (-1,0) 与 (9,9),from 仍是当前头。 */
    let g6c = PatrolGame(mkTiny(3, 1, [(1, 0, 0), (2, 2, 0)]))
    if (dirSteps(fails, g6c, "bounds", [(0, 0)])) {
        dirExpect(fails, g6c, "bounds", Cell(-1, 0), REJECT_BOUNDS, false, 0, 0, -1, 0, false)
        dirExpect(fails, g6c, "bounds", Cell(9, 9), REJECT_BOUNDS, false, 0, 0, 9, 9, false)
    }
    /* 不闪:跳号 (next=2 却踩 3 号格) → WAYPOINT。 */
    let l7 = mkTiny(3, 1, [(1, 0, 0), (2, 2, 0), (3, 1, 0)])
    let g7 = PatrolGame(l7)
    if (dirSteps(fails, g7, "waypoint", [(0, 0)])) {
        dirExpect(fails, g7, "waypoint", Cell(1, 0), REJECT_WAYPOINT, false, 0, 0, 1, 0, false)
    }
    /* 不闪:首格非 1 号 → START,from 无效 (-1,-1)。 */
    let g8 = PatrolGame(mkTiny(3, 1, [(1, 0, 0), (2, 1, 0)]))
    dirExpect(fails, g8, "start", Cell(1, 0), REJECT_START, false, -1, -1, 1, 0, false)
    /* 返回失败拼串,空串=通过。 */
    let sb = StringBuilder()
    var i: Int64 = 0
    while (i < fails.size) {
        if (i > 0) {
            sb.append("\n")
        }
        sb.append(fails.get(i).getOrThrow())
        i = i + 1
    }
    return sb.toString()
}

/* ===== J13 定向纯函数检查：rejectGateImg 几何 + 与 buildBoardGates 一致 ===== */
func j13RejectGateTests(levels: ArrayList<LevelDef>, ctx: Ctx): Unit {
    let geom = BoardGeom(43.0, 5, 5)
    /* (3) 竖缝(左右相邻)→ vertical=true、h=0.72c、w=h*27/60；横缝 → vertical=false */
    let rv = rejectGateImg(geom, 1, 1, 2, 1)
    ctx.ck(rv.vertical == true, "J13 rv.vertical=${rv.vertical} want=true")
    ctx.ck(absF(rv.h - 0.72 * 43.0) < 1e-9, "J13 rv.h=${rv.h} want=${0.72 * 43.0}")
    ctx.ck(absF(rv.w - rv.h * 27.0 / 60.0) < 1e-9, "J13 rv.w=${rv.w} want=${rv.h * 27.0 / 60.0}")
    let rh = rejectGateImg(geom, 1, 1, 1, 2)
    ctx.ck(rh.vertical == false, "J13 rh.vertical=${rh.vertical} want=false")
    ctx.ck(absF(rh.h - rh.w * 27.0 / 60.0) < 1e-9, "J13 rh aspect w=${rh.w} h=${rh.h}")
    /* (4) 与 buildBoardGates 对同一 one_way 关同一逐边一致(x/y/w/h 差<1e-9) */
    var li: Int64 = 0
    var found = false
    while (li < levels.size && !found) {
        let lv = levels.get(li).getOrThrow()
        if (lv.oneWays.size > 0) {
            found = true
            let g = PatrolGame(lv)
            let gates = buildBoardGates(g, geom)
            ctx.ck(gates.size == lv.oneWays.size, "J13 gates=${gates.size} oneWays=${lv.oneWays.size}")
            var k: Int64 = 0
            while (k < gates.size) {
                let ow = lv.oneWays.get(k).getOrThrow()
                let gi = rejectGateImg(geom, ow.fromX, ow.fromY, ow.toX, ow.toY)
                let gt = gates.get(k).getOrThrow()
                ctx.ck(absF(gi.x - gt.x) < 1e-9 && absF(gi.y - gt.y) < 1e-9
                    && absF(gi.w - gt.w) < 1e-9 && absF(gi.h - gt.h) < 1e-9
                    && gi.vertical == gt.vertical,
                    "J13 gate[${k}] mismatch gi=(${gi.x},${gi.y},${gi.w},${gi.h},${gi.vertical}) gt=(${gt.x},${gt.y},${gt.w},${gt.h},${gt.vertical})")
                k = k + 1
            }
        }
        li = li + 1
    }
    ctx.ck(found, "J13 no one_way level in catalog")
}

main(args: Array<String>): Int64 {
    if (args.size < 2) {
        println("usage: main <levels.json> <inputs.txt>")
        return 2
    }
    let lvText = unsafe { String.fromUtf8Unchecked(File.readFrom(args[0])) }
    let loaded = levelsFromJson(lvText)
    if (loaded.error != "") {
        println("SELFTEST levels-parse-error: ${loaded.error}")
        return 2
    }
    let levels = loaded.levels
    let bytes = File.readFrom(args[1])
    let ctx = Ctx()
    var start: Int64 = 0
    var pos: Int64 = 0
    while (pos < bytes.size) {
        if (bytes[pos] == 10u8) {
            runLine(bytes, start, pos, levels, ctx)
            start = pos + 1
        }
        pos = pos + 1
    }
    if (start < bytes.size) {
        runLine(bytes, start, bytes.size, levels, ctx)
    }
    let sb = StringBuilder()
    var r: Int64 = 0
    while (r < 11) {
        if (r > 0) {
            sb.append(" ")
        }
        sb.append("${ctx.rej[r]}")
        r = r + 1
    }
    /* T2 定向拒绝闪:失败并入总 failures,断言并入 checks。 */
    let dirMsg = directedRejectTests()
    if (dirMsg != "") {
        ctx.failures.add(dirMsg)
    }
    /* J13 定向纯函数检查。 */
    j13RejectGateTests(levels, ctx)
    ctx.checks = ctx.checks + dStat.checks
    println("SELFTEST levels=${ctx.levels} steps=${ctx.steps} checks=${ctx.checks} rejects=[${sb.toString()}] failures=${ctx.failures.size}")
    println("DIRECTED flash=${dStat.flash} noflash=${dStat.noflash} failures=${dStat.fails}")
    var f: Int64 = 0
    while (f < ctx.failures.size && f < 40) {
        println(ctx.failures.get(f).getOrThrow())
        f = f + 1
    }
    if (ctx.failures.size == 0) {
        return 0
    }
    return 1
}

