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

/* 点到线段距离 ≤ r(用于 chevron 胶囊体采样,J14 3b)。 */
func segDistLE(px: Float64, py: Float64, ax: Float64, ay: Float64, bx: Float64, by: Float64, r: Float64): Bool {
    let vx = bx - ax
    let vy = by - ay
    let l2 = vx * vx + vy * vy
    var t = 0.0
    if (l2 > 0.0) {
        t = ((px - ax) * vx + (py - ay) * vy) / l2
        if (t < 0.0) {
            t = 0.0
        }
        if (t > 1.0) {
            t = 1.0
        }
    }
    let qx = ax + t * vx
    let qy = ay + t * vy
    let ddx = px - qx
    let ddy = py - qy
    return ddx * ddx + ddy * ddy <= r * r
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
    /* 4. mech dots:渡口 4 个(J17:停环挪到 paths 层,dots 不再含环) */
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
    /* 4b. 头点:头格是「停」末格时空(由环代替),否则 1 个 */
    let headDots = buildBoardHeadDot(game, geom)
    var wantHead: Int64 = 0
    if (game.path.size() >= 1 && !isSlideStopIndex(game, game.path.size() - 1)) {
        wantHead = 1
    }
    ctx.ck(headDots.size == wantHead, "${tag} headDots=${headDots.size} want=${wantHead}")
    /* 5. mech walls：闸(sealGates×1/2)；P4 塌桥不再画墨墙(断桩/板条挪到 under 层) */
    var sealN: Int64 = 0
    if (game.hasToken) {
        sealN = lv.sealGates.size * 2
    } else {
        sealN = lv.sealGates.size
    }
    let walls = buildBoardMechWalls(game, geom)
    ctx.ck(walls.size == sealN, "${tag} walls=${walls.size} want=${sealN}")
    /* 5b. P4 塌桥 under 层：缺角标(inkMuted fill)常驻 1 个；未断=板条+板缝各 1，
       已断=恰好 2 断桩；非 collapse 关无板条/断桩/缺角。 */
    let under = buildBoardMechUnder(game, geom, 3.0)
    var plankN: Int64 = 0
    var seamN: Int64 = 0
    var mutedFillN: Int64 = 0
    for (p in under) {
        if (p.color == Theme.qing && p.fillOp == 1.0) {
            plankN = plankN + 1
        }
        if (p.color == Theme.qingDeep && p.fillOp == 0.0) {
            seamN = seamN + 1
        }
        if (p.color == Theme.inkMuted && p.strokeW == 0.0 && p.fillOp == 1.0) {
            mutedFillN = mutedFillN + 1
        }
    }
    var wantPlank: Int64 = 0
    var wantStump: Int64 = 0
    var wantMuted: Int64 = 0
    match (lv.collapse) {
        case Some(cd) =>
            wantMuted = 1 /* 缺角标常驻 */
            if (game.isEdgeCollapsed(cd.x1, cd.y1, cd.x2, cd.y2)) {
                wantStump = 2
            } else {
                wantPlank = 1
            }
        case None => ()
    }
    ctx.ck(plankN == wantPlank, "${tag} plank=${plankN} want=${wantPlank}")
    ctx.ck(seamN == wantPlank, "${tag} seam=${seamN} want=${wantPlank}")
    ctx.ck(mutedFillN == wantMuted + wantStump, "${tag} mutedFill=${mutedFillN} want=${wantMuted + wantStump} (notch+stumps)")
    /* 6. labels = 渡3 + 开闸 + 符(J14:滑/停不再出 Text) */
    let labels = buildBoardMechLabels(game, geom)
    var base: Int64 = 0
    if (hasFerry) {
        base = 3
    }
    if (game.hasToken) {
        base = base + lv.sealGates.size
    }
    base = base + lv.tokenCells.size
    ctx.ck(labels.size == base, "${tag} labels=${labels.size} base=${base}")
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
        /* 旧白色 chevron 特征：线画(fillOp=0)且 color 与 stroke 同为 whitePaper
           (挂锁 path 的 stroke 是 ink;J17 停环孔是 fill-only,不算)。 */
        if (p.color == Theme.whitePaper && p.stroke == Theme.whitePaper && p.fillOp == 0.0) {
            hasWhiteChev = true
        }
    }
    if (wantChev > 0) {
        ctx.ck(hasQing && qingCmds.size > 0, "${tag} chevron qingDeep missing want=${wantChev}")
        ctx.ck(!hasWhiteChev, "${tag} white slide chevron still present")
        /* J14:chevron 笔画 sw = max(3, 4k),k=c/36.3(本测试 c=43) */
        var wantSw = 4.0 * (43.0 / 36.3)
        if (wantSw < 3.0) {
            wantSw = 3.0
        }
        for (p in paths) {
            if (p.color == Theme.qingDeep) {
                ctx.ck(absF(p.strokeW - wantSw) < 1e-9, "${tag} chevron sw=${p.strokeW} want=${wantSw}")
            }
        }
    } else {
        ctx.ck(!hasQing, "${tag} qingDeep chevron without slide entry")
    }
    /* 7c. J14:滑/停 不再是 Text;「滑」= 墨色 fill-only BoardPath(仅当有滑行格) */
    for (l in labels) {
        ctx.ck(l.text != "滑" && l.text != "停", "${tag} stray slide label '${l.text}'")
    }
    var inkFillN: Int64 = 0
    for (p in paths) {
        if (p.color == Theme.ink && p.strokeW == 0.0 && p.fillOp == 1.0) {
            inkFillN = inkFillN + 1
        }
    }
    var wantHua: Int64 = 0
    if (lv.slideCells.size > 0) {
        wantHua = 1
    }
    /* J17:头格为停末格时,停环外圈也是墨色 fill-only path */
    if (game.path.size() >= 2 && isSlideStopIndex(game, game.path.size() - 1)) {
        wantHua = wantHua + 1
    }
    ctx.ck(inkFillN == wantHua, "${tag} ink fill-only paths=${inkFillN} want=${wantHua}")
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
            /* P4:WALL 里塌桥断边(isCollapseReject)同样按 from/to 相邻判定期望闪 */
            if (code == 1 || code == 2 || code == 3 || code == 4 || code == 9
                || (code == 5 && isCollapseReject(game))) {
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
            /* P4 toast 文案:塌桥断边「此路不通」,负重禁区「粮重不可进」 */
            if (rejectShouldFlash(game) && code == 5) {
                ctx.ck(mechToastText(game) == "此路不通", "${tag} code=5 toast='${mechToastText(game)}' want=此路不通")
            }
            if (rejectShouldFlash(game) && code == 4) {
                ctx.ck(mechToastText(game) == "粮重不可进", "${tag} code=4 toast='${mechToastText(game)}' want=粮重不可进")
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
        /* P4:负重 toast 文案与宽度(4 字=86、5 字=100、空=86)。 */
        dStat.checks = dStat.checks + 1
        if (mechToastText(g3) != "粮重不可进") {
            fails.add("FAIL directed burden: toast='${mechToastText(g3)}' want=粮重不可进")
        }
        dStat.checks = dStat.checks + 1
        if (mechToastWidth("粮重不可进") != 100.0) {
            fails.add("FAIL directed burden: w5=${mechToastWidth("粮重不可进")} want=100")
        }
        dStat.checks = dStat.checks + 1
        if (mechToastWidth("此路不通") != 86.0) {
            fails.add("FAIL directed burden: w4=${mechToastWidth("此路不通")} want=86")
        }
        dStat.checks = dStat.checks + 1
        if (mechToastWidth("") != 86.0) {
            fails.add("FAIL directed burden: w0=${mechToastWidth("")} want=86")
        }
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
        /* P4:普通墙不算塌桥断边,也无机制 toast。 */
        dStat.checks = dStat.checks + 1
        if (isCollapseReject(g6)) {
            fails.add("FAIL directed wall: isCollapseReject true for plain wall")
        }
        dStat.checks = dStat.checks + 1
        if (mechToastText(g6) != "") {
            fails.add("FAIL directed wall: toast='${mechToastText(g6)}' want empty")
        }
    }
    /* (6b) 塌桥:踏触发格 (0,0) 后断边 (1,0)-(2,0),(1,0)→(2,0) 拒 REJECT_WALL 且闪,toast=此路不通。 */
    let lc = mkTiny(3, 1, [(1, 0, 0), (2, 2, 0)])
    lc.collapse = Some(CollapseDef(0, 0, 1, 0, 2, 0))
    let gc = PatrolGame(lc)
    if (dirSteps(fails, gc, "collapse", [(0, 0), (1, 0)])) {
        dirExpect(fails, gc, "collapse", Cell(2, 0), REJECT_WALL, true, 1, 0, 2, 0, false)
        dStat.checks = dStat.checks + 1
        if (!isCollapseReject(gc)) {
            fails.add("FAIL directed collapse: isCollapseReject false after broken-edge reject")
        }
        dStat.checks = dStat.checks + 1
        if (mechToastText(gc) != "此路不通") {
            fails.add("FAIL directed collapse: toast='${mechToastText(gc)}' want=此路不通")
        }
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

/* ===== J14 定向检查：boardGeomFor 比例 + 滑行 chevron/hua 几何 + 停环 ===== */
func j14SlideGeomTests(levels: ArrayList<LevelDef>, ctx: Ctx): Unit {
    /* (1) boardGeomFor:cols=7 → c=32/38/40/43/43,托盘宽=7c+36+16(即 7c+6*6+2*8) */
    let ws = [320.0, 360.0, 375.0, 393.0, 430.0]
    let wantC = [32.0, 38.0, 40.0, 43.0, 43.0]
    let wantTw = [276.0, 318.0, 332.0, 353.0, 353.0]
    var i: Int64 = 0
    while (i < 5) {
        let g7 = boardGeomFor(7, 7, ws[i])
        ctx.ck(absF(g7.c - wantC[i]) < 1e-9, "J14 7col W=${ws[i]} c=${g7.c} want=${wantC[i]}")
        ctx.ck(absF(g7.trayW() - wantTw[i]) < 1e-9, "J14 7col W=${ws[i]} trayW=${g7.trayW()} want=${wantTw[i]}")
        i = i + 1
    }
    /* cols=6:同一 c 公式 → W=320 得 c=39、托盘 6c+46=280 */
    let g6 = boardGeomFor(6, 6, 320.0)
    ctx.ck(absF(g6.c - 39.0) < 1e-9, "J14 6col W=320 c=${g6.c} want=39")
    ctx.ck(absF(g6.trayW() - 280.0) < 1e-9, "J14 6col W=320 trayW=${g6.trayW()} want=280")
    /* (2) 滑行 chevron 几何 helper:入向左/上时中心相对格心偏 0.18c,其余居中 */
    let c = 43.0
    let k = c / 36.3
    let ccx = 100.0
    let ccy = 90.0
    var dirs: Array<(Int64, Int64)> = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    for (d in dirs) {
        let pts = slideChevronPts(ccx, ccy, c, d[0], d[1])
        /* base = 两臂中点,chevron 中心 = (tip+base)/2 */
        let basex = (pts[0] + pts[4]) * 0.5
        let basey = (pts[1] + pts[5]) * 0.5
        let cenx = (pts[2] + basex) * 0.5
        let ceny = (pts[3] + basey) * 0.5
        let shift = if (d[0] < 0 || d[1] < 0) { 0.18 * c } else { 0.0 }
        ctx.ck(absF(cenx - (ccx + Float64(d[0]) * shift)) < 1e-9 && absF(ceny - (ccy + Float64(d[1]) * shift)) < 1e-9,
            "J14 chev cen=(${cenx},${ceny}) dir=${d[0]},${d[1]} shift=${shift}")
        /* 深度 dep=18k:tip 与 base 距离 */
        let dep = sqrt((pts[2] - basex) * (pts[2] - basex) + (pts[3] - basey) * (pts[3] - basey))
        ctx.ck(absF(dep - 18.0 * k) < 1e-9, "J14 chev dep=${dep} want=${18.0 * k}")
        /* 臂展 h=25k:两臂距离 */
        let h = sqrt((pts[0] - pts[4]) * (pts[0] - pts[4]) + (pts[1] - pts[5]) * (pts[1] - pts[5]))
        ctx.ck(absF(h - 25.0 * k) < 1e-9, "J14 chev h=${h} want=${25.0 * k}")
    }
    /* (3) hua 角标:墨迹包围盒定位(FOLLOWUP §1)——全体矩形最大 x1 = 格右-2k,
       最大 y1(含下探的三短横)= 格下-1k;ink 宽 = x1max-x0min = 11k,
       ink 高 = y1max-y0min = 12.76k(s=3.4k 时,c=43/32 均如此)。 */
    var ci: Int64 = 0
    let cs = [43.0, 32.0]
    while (ci < 2) {
        let hc = cs[ci]
        let hk = hc / 36.3
        let rects = slideHuaRects(hc)
        var maxX = 0.0
        var maxY = 0.0
        var minX = rects[0]
        var minY = rects[1]
        var r: Int64 = 0
        while (r + 3 < rects.size) {
            if (rects[r + 2] > maxX) {
                maxX = rects[r + 2]
            }
            if (rects[r + 3] > maxY) {
                maxY = rects[r + 3]
            }
            if (rects[r] < minX) {
                minX = rects[r]
            }
            if (rects[r + 1] < minY) {
                minY = rects[r + 1]
            }
            r = r + 4
        }
        ctx.ck(rects.size == 28, "J14 hua rects=${rects.size} want=28 (7*4)")
        ctx.ck(absF(maxX - (hc - 2.0 * hk)) < 1e-9, "J14 hua c=${hc} right=${maxX} want=${hc - 2.0 * hk}")
        ctx.ck(absF(maxY - (hc - 1.0 * hk)) < 1e-9, "J14 hua c=${hc} ink bottom=${maxY} want=${hc - 1.0 * hk}")
        ctx.ck(absF((maxX - minX) - 11.0 * hk) < 1e-9, "J14 hua c=${hc} ink w=${maxX - minX} want=${11.0 * hk}")
        ctx.ck(absF((maxY - minY) - 12.76 * hk) < 1e-9, "J14 hua c=${hc} ink h=${maxY - minY} want=${12.76 * hk}")
        /* 右钩 = 第 7 个矩形:右缘锚在墨迹右缘 */
        ctx.ck(absF(rects[26] - (hc - 2.0 * hk)) < 1e-9, "J14 hua c=${hc} hook right=${rects[26]} want=${hc - 2.0 * hk}")
        ci = ci + 1
    }
    /* (3b) FOLLOWUP §1:chevron 折线(含圆头半径 sw/2,胶囊体)与 hua 墨迹包围盒
       的重叠面积 ≤ 0.8 u²(设计栅格实测最大 0.67u²);chevron 折线包围盒(含 sw/2
       外扩)须留在 [0,c] 内。胶囊体用 0.05u 网格中点采样近似(含圆头)。 */
    var oc: Int64 = 0
    let ocs = [32.0, 38.0, 43.0]
    while (oc < 3) {
        let cc = ocs[oc]
        let ok = cc / 36.3
        var sw = 4.0 * ok
        if (sw < 3.0) {
            sw = 3.0
        }
        var ohs = 3.4 * ok
        if (ohs < 2.0) {
            ohs = 2.0
        }
        var oinkH = 0.78 * 12.0 * ok + ohs
        if (oinkH < 12.0 * ok) {
            oinkH = 12.0 * ok
        }
        let huaX0 = cc - 13.0 * ok
        let huaY0 = cc - 1.0 * ok - oinkH
        for (d in dirs) {
            let pts = slideChevronPts(cc / 2.0, cc / 2.0, cc, d[0], d[1])
            /* 包围盒(含 sw/2 外扩)在 [0,c] 内 */
            var bx0 = pts[0]
            var bx1 = pts[0]
            var by0 = pts[1]
            var by1 = pts[1]
            var pi: Int64 = 0
            while (pi < 3) {
                if (pts[pi * 2] < bx0) {
                    bx0 = pts[pi * 2]
                }
                if (pts[pi * 2] > bx1) {
                    bx1 = pts[pi * 2]
                }
                if (pts[pi * 2 + 1] < by0) {
                    by0 = pts[pi * 2 + 1]
                }
                if (pts[pi * 2 + 1] > by1) {
                    by1 = pts[pi * 2 + 1]
                }
                pi = pi + 1
            }
            ctx.ck(bx0 - sw / 2.0 >= 0.0 && by0 - sw / 2.0 >= 0.0 && bx1 + sw / 2.0 <= cc && by1 + sw / 2.0 <= cc,
                "J14 chev bbox out of cell c=${cc} dir=${d[0]},${d[1]} bbox=(${bx0},${by0},${bx1},${by1})")
            /* 胶囊体 ∩ hua 墨迹包围盒:0.05u 网格中点采样 */
            let stp = 0.05
            let nx = Int64((cc - 2.0 * ok - huaX0) / stp)
            let ny = Int64((cc - 1.0 * ok - huaY0) / stp)
            var hit: Int64 = 0
            var gy: Int64 = 0
            while (gy < ny) {
                let py = huaY0 + (Float64(gy) + 0.5) * stp
                var gx: Int64 = 0
                while (gx < nx) {
                    let px = huaX0 + (Float64(gx) + 0.5) * stp
                    if (segDistLE(px, py, pts[0], pts[1], pts[2], pts[3], sw / 2.0) ||
                        segDistLE(px, py, pts[2], pts[3], pts[4], pts[5], sw / 2.0)) {
                        hit = hit + 1
                    }
                    gx = gx + 1
                }
                gy = gy + 1
            }
            let area = Float64(hit) * stp * stp
            ctx.ck(area <= 0.8, "J14 chev/hua overlap c=${cc} dir=${d[0]},${d[1]} area=${area} want<=0.8")
        }
        oc = oc + 1
    }
    /* (4) 手工构造滑行关:从 (0,0) 入 (1,0) 滑到 (2,0) → 2 chevron、hua Z 数 = 滑格数*7;
       J17:头格=停末格 → chevron 之后两个 fill-only 圆 path(外圈 ink 7k + 孔 whitePaper 3k,
       圆心=格心,与 circlePathCmds 一致)、头点为空;
       继续走 (2,1) 离开滑行段后 → 圆 path 数 0(不留历史环)、头点恢复 1 个 */
    let lvs = mkTiny(7, 7, [(1, 0, 0), (2, 0, 3)])
    lvs.slideCells.add(Cell(1, 0))
    lvs.slideCells.add(Cell(2, 0))
    let g = PatrolGame(lvs)
    ctx.ck(g.tryStep(Cell(0, 0)), "J14 slide setup start rejected")
    ctx.ck(g.tryStep(Cell(1, 0)), "J14 slide setup tryStep rejected")
    if (g.path.size() == 3) {
        ctx.ck(g.path.at(1).x == 1 && g.path.at(2).x == 2, "J14 slide path unexpected")
        let geom = BoardGeom(43.0, 7, 7)
        let paths = buildBoardMechPaths(g, geom, 3.0)
        var huaCmds = ""
        var chevN: Int64 = 0
        /* J17:停环外圈也是 ink fill-only,按命令串排除,只捕获 hua */
        let ringOuterCmds = circlePathCmds(geom.centerX(2), geom.centerY(0), 7.0 * k, 3.0)
        for (p in paths) {
            if (p.color == Theme.ink && p.fillOp == 1.0 && p.commands != ringOuterCmds) {
                huaCmds = p.commands
            }
            if (p.color == Theme.qingDeep) {
                /* 数 M 次数 = chevron 个数 */
                var q: Int64 = 0
                chevN = 0
                while (q < p.commands.size) {
                    match (p.commands.get(q)) {
                        case Some(b) => if (b == 77u8) { chevN = chevN + 1 }
                        case None => ()
                    }
                    q = q + 1
                }
            }
        }
        ctx.ck(chevN == 2, "J14 chevron count=${chevN} want=2")
        var zN: Int64 = 0
        var q2: Int64 = 0
        while (q2 < huaCmds.size) {
            match (huaCmds.get(q2)) {
                case Some(b) => if (b == 90u8) { zN = zN + 1 }
                case None => ()
            }
            q2 = q2 + 1
        }
        ctx.ck(zN == 14, "J14 hua Z count=${zN} want=14 (2 cells * 7 rects)")
        /* J17:停在末格 → dots 层无环,chevron 之后追加两个 fill-only 圆 path:
           外圈 r=7k ink 先于孔 r=3k whitePaper,命令串与 circlePathCmds(格心,r,f) 一致 */
        let sd = buildBoardMechDots(g, geom)
        let scx = geom.centerX(2)
        let scy = geom.centerY(0)
        ctx.ck(sd.size == 0, "J17 stop mech dots=${sd.size} want=0")
        var chevIdx: Int64 = -1
        var ringInk: Int64 = -1
        var ringHole: Int64 = -1
        var pi: Int64 = 0
        while (pi < paths.size) {
            let p = paths.get(pi).getOrThrow()
            if (p.color == Theme.qingDeep) {
                chevIdx = pi
            }
            if (p.color == Theme.ink && p.strokeW == 0.0 && p.fillOp == 1.0
                && p.commands == circlePathCmds(scx, scy, 7.0 * k, 3.0)) {
                ringInk = pi
            }
            if (p.color == Theme.whitePaper && p.strokeW == 0.0 && p.fillOp == 1.0
                && p.commands == circlePathCmds(scx, scy, 3.0 * k, 3.0)) {
                ringHole = pi
            }
            pi = pi + 1
        }
        ctx.ck(ringInk >= 0 && ringHole >= 0, "J17 stop ring paths missing ink=${ringInk} hole=${ringHole}")
        ctx.ck(chevIdx >= 0 && ringInk > chevIdx && ringHole > chevIdx,
            "J17 stop ring not after chevron ink=${ringInk} hole=${ringHole} chev=${chevIdx}")
        ctx.ck(ringInk < ringHole, "J17 stop ring order ink=${ringInk} hole=${ringHole} want ink first")
        ctx.ck(buildBoardHeadDot(g, geom).size == 0, "J14 head dot should be empty at slide stop")
        /* J17:走出滑行段 → 圆 path 数 0(只剩 hua 一个 ink fill-only)、头点恢复 1 个 */
        ctx.ck(g.tryStep(Cell(2, 1)), "J14 slide leave tryStep rejected")
        let leftDots = buildBoardMechDots(g, geom)
        let leftPaths = buildBoardMechPaths(g, geom, 3.0)
        var leftRingN: Int64 = 0
        var lp: Int64 = 0
        while (lp < leftPaths.size) {
            let p = leftPaths.get(lp).getOrThrow()
            if (p.strokeW == 0.0 && p.fillOp == 1.0
                && (p.color == Theme.ink || p.color == Theme.whitePaper)) {
                leftRingN = leftRingN + 1
            }
            lp = lp + 1
        }
        ctx.ck(leftDots.size == 0, "J16 rings after leaving slide=${leftDots.size} want=0")
        ctx.ck(leftRingN == 1, "J17 fill-only paths after leaving=${leftRingN} want=1 (hua only)")
        let leftHead = buildBoardHeadDot(g, geom)
        ctx.ck(leftHead.size == 1, "J16 head dot after leaving=${leftHead.size} want=1")
    } else {
        ctx.ck(false, "J14 slide path size=${g.path.size()} want=3")
    }
    /* (5) 目录里确实有 slide 关(防止 (4) 之外全部走空) */
    var found = false
    var li: Int64 = 0
    while (li < levels.size && !found) {
        if (levels.get(li).getOrThrow().slideCells.size > 0) {
            found = true
        }
        li = li + 1
    }
    ctx.ck(found, "J14 no slide level in catalog")
}

/* J20:粮袋路径包围盒(袋口梯形 + 袋身椭圆 ±rx/±ry + 系口线)。 */
func j20BagBox(cx: Float64, cy: Float64, k: Float64): (Float64, Float64, Float64, Float64) {
    let nk = bagNeckPts(cx, cy, k)
    let e = bagBodyEllipse(cx, cy, k)
    let t = bagTiePts(cx, cy, k)
    var mnx = nk[0]
    var mxx = nk[0]
    var mny = nk[1]
    var mxy = nk[1]
    var q: Int64 = 0
    while (q < 8) {
        if (nk[q] < mnx) {
            mnx = nk[q]
        }
        if (nk[q] > mxx) {
            mxx = nk[q]
        }
        if (nk[q + 1] < mny) {
            mny = nk[q + 1]
        }
        if (nk[q + 1] > mxy) {
            mxy = nk[q + 1]
        }
        q = q + 2
    }
    if (e[0] - e[2] < mnx) {
        mnx = e[0] - e[2]
    }
    if (e[0] + e[2] > mxx) {
        mxx = e[0] + e[2]
    }
    if (e[1] - e[3] < mny) {
        mny = e[1] - e[3]
    }
    if (e[1] + e[3] > mxy) {
        mxy = e[1] + e[3]
    }
    if (t[0] < mnx) {
        mnx = t[0]
    }
    if (t[2] > mxx) {
        mxx = t[2]
    }
    if (t[1] < mny) {
        mny = t[1]
    }
    if (t[3] > mxy) {
        mxy = t[3]
    }
    return (mnx, mny, mxx, mxy)
}

/* J20:断桩检查(bridgeStumpPolys):28 数、两截各 7 顶点、锯齿侧=下标 1..5、
   边缘侧=下标 0/6、每截最窄宽 >=1.4、单截沿通行方向宽 (0,5)、两截之间有缺口。
   返回实测最窄宽度。 */
func j20StumpChecks(geom: BoardGeom, ax: Int64, ay: Int64, bx: Int64, by: Int64, ctx: Ctx): Float64 {
    let horiz = (ay == by)
    let sp = bridgeStumpPolys(geom, ax, ay, bx, by)
    ctx.ck(sp.size == 28, "J20 stump size=${sp.size} want=28 c=${geom.c}")
    var leftJagMax = 0.0
    var rightJagMin = 0.0
    var narrowest = 1e9
    var side: Int64 = 0
    while (side < 2) {
        let cross = ArrayList<Float64>()
        var j: Int64 = 0
        while (j < 7) {
            let px = sp[side * 14 + j * 2]
            let py = sp[side * 14 + j * 2 + 1]
            if (horiz) {
                cross.add(px)
            } else {
                cross.add(py)
            }
            j = j + 1
        }
        let edgeA = cross.get(0).getOrThrow()
        ctx.ck(absF(edgeA - cross.get(6).getOrThrow()) < 1e-6,
            "J20 stump edge verts differ c=${geom.c} side=${side} ${edgeA} vs ${cross.get(6).getOrThrow()}")
        var jagMin = cross.get(1).getOrThrow()
        var jagMax = jagMin
        var minW = absF(jagMin - edgeA)
        var q: Int64 = 2
        while (q <= 5) {
            let v = cross.get(q).getOrThrow()
            if (v < jagMin) {
                jagMin = v
            }
            if (v > jagMax) {
                jagMax = v
            }
            let d = absF(v - edgeA)
            if (d < minW) {
                minW = d
            }
            q = q + 1
        }
        ctx.ck(minW >= 1.4, "J20 stump narrowest=${minW} want>=1.4 c=${geom.c} side=${side}")
        if (minW < narrowest) {
            narrowest = minW
        }
        let w = if (side == 0) {
            jagMax - edgeA
        } else {
            edgeA - jagMin
        }
        ctx.ck(w > 0.0 && w < 5.0, "J20 stump cut width=${w} want (0,5) c=${geom.c} side=${side}")
        if (side == 0) {
            leftJagMax = jagMax
        } else {
            rightJagMin = jagMin
        }
        side = side + 1
    }
    ctx.ck(leftJagMax < rightJagMin,
        "J20 stump gap missing c=${geom.c} leftJagMax=${leftJagMax} rightJagMin=${rightJagMin}")
    return narrowest
}

/* ===== J20 定向检查:塌桥/负重皮肤几何(BRIDGE_BURDEN_SKIN_20261003) ===== */
func j20SkinGeomTests(levels: ArrayList<LevelDef>, ctx: Ctx): Unit {
    let cs = [32.0, 38.0, 41.0, 43.0]
    /* (a) 断桩:两个方向 + 目录塌桥关(95/97/99)的边,实测最窄宽度全程 >=1.4。 */
    var gMin = 1e9
    var i: Int64 = 0
    while (i < 4) {
        let geom = BoardGeom(cs[i], 7, 7)
        let m1 = j20StumpChecks(geom, 1, 1, 2, 1, ctx)
        let m2 = j20StumpChecks(geom, 1, 1, 1, 2, ctx)
        if (m1 < gMin) {
            gMin = m1
        }
        if (m2 < gMin) {
            gMin = m2
        }
        i = i + 1
    }
    var colN: Int64 = 0
    var li: Int64 = 0
    let g43 = BoardGeom(43.0, 7, 7)
    while (li < levels.size) {
        let lv = levels.get(li).getOrThrow()
        match (lv.collapse) {
            case Some(cd) =>
                let m = j20StumpChecks(g43, cd.x1, cd.y1, cd.x2, cd.y2, ctx)
                if (m < gMin) {
                    gMin = m
                }
                if (lv.id == 95 || lv.id == 97 || lv.id == 99) {
                    colN = colN + 1
                }
            case None => ()
        }
        li = li + 1
    }
    ctx.ck(colN == 3, "J20 collapse catalog levels=${colN} want=3 (95/97/99)")
    println("J20 stump narrowest=${gMin}")
    /* (b) 板条:长 = gap+4=10、横向宽 = 16k、中心 = seamMid;板缝 x±1.7、长 16k-2。 */
    i = 0
    while (i < 4) {
        let c = cs[i]
        let k = skinK(c)
        let geom = BoardGeom(c, 7, 7)
        let (mx, my) = geom.seamMid(1, 1, 2, 1)
        let pr = bridgePlankRect(geom, 1, 1, 2, 1)
        ctx.ck(absF((pr[2] - pr[0]) - (geom.gap + 4.0)) < 1e-6,
            "J20 plank len=${pr[2] - pr[0]} want=${geom.gap + 4.0} c=${c}")
        ctx.ck(absF((pr[3] - pr[1]) - 16.0 * k) < 1e-6, "J20 plank w=${pr[3] - pr[1]} want=${16.0 * k} c=${c}")
        ctx.ck(absF((pr[0] + pr[2]) * 0.5 - mx) < 1e-6 && absF((pr[1] + pr[3]) * 0.5 - my) < 1e-6,
            "J20 plank center=(${(pr[0] + pr[2]) * 0.5},${(pr[1] + pr[3]) * 0.5}) want=(${mx},${my}) c=${c}")
        let ss = bridgeSeamSegs(geom, 1, 1, 2, 1)
        ctx.ck(ss.size == 8, "J20 seam segs=${ss.size} want=8 c=${c}")
        ctx.ck(absF(ss[0] - (mx - 1.7)) < 1e-6 && absF(ss[4] - (mx + 1.7)) < 1e-6,
            "J20 seam x=${ss[0]},${ss[4]} want=${mx - 1.7},${mx + 1.7} c=${c}")
        ctx.ck(absF((ss[3] - ss[1]) - (16.0 * k - 2.0)) < 1e-6,
            "J20 seam len=${ss[3] - ss[1]} want=${16.0 * k - 2.0} c=${c}")
        let (mx2, my2) = geom.seamMid(1, 1, 1, 2)
        let pv = bridgePlankRect(geom, 1, 1, 1, 2)
        ctx.ck(absF((pv[3] - pv[1]) - (geom.gap + 4.0)) < 1e-6 && absF((pv[2] - pv[0]) - 16.0 * k) < 1e-6,
            "J20 plank vert len/w=(${pv[3] - pv[1]},${pv[2] - pv[0]}) want=(${geom.gap + 4.0},${16.0 * k}) c=${c}")
        ctx.ck(absF((pv[0] + pv[2]) * 0.5 - mx2) < 1e-6 && absF((pv[1] + pv[3]) * 0.5 - my2) < 1e-6,
            "J20 plank vert center mismatch c=${c}")
        i = i + 1
    }
    ctx.ck(gMin >= 1.4, "J20 stump narrowest=${gMin} want>=1.4")
    /* (c) 粮袋:宽 16k、高 19.5k(1e-9);加描边半宽 0.7k 后 17.4k×20.9k(0.01k)。
       bagPaths 3 个,前两个 hollow=false→gold / hollow=true→whitePaper,描边 ink;
       装卸点不落在带数字(waypoint)格,禁区不含装卸点。 */
    let k41 = skinK(41.0)
    let bks = [k41, 0.62, 0.5]
    var bi: Int64 = 0
    while (bi < 3) {
        let bk = bks[bi]
        let (mnx, mny, mxx, mxy) = j20BagBox(0.0, 0.0, bk)
        ctx.ck(absF((mxx - mnx) - 16.0 * bk) < 1e-9, "J20 bag w=${mxx - mnx} want=${16.0 * bk} k=${bk}")
        ctx.ck(absF((mxy - mny) - 19.5 * bk) < 1e-9, "J20 bag h=${mxy - mny} want=${19.5 * bk} k=${bk}")
        ctx.ck(absF((mxx - mnx + 1.4 * bk) - 17.4 * bk) < 0.01 * bk,
            "J20 bag ink w=${mxx - mnx + 1.4 * bk} want=${17.4 * bk} k=${bk}")
        ctx.ck(absF((mxy - mny + 1.4 * bk) - 20.9 * bk) < 0.01 * bk,
            "J20 bag ink h=${mxy - mny + 1.4 * bk} want=${20.9 * bk} k=${bk}")
        if (bi == 0) {
            println("J20 bag ink box=${17.4 * bk}x${20.9 * bk} k=${bk}")
        }
        bi = bi + 1
    }
    let solid = bagPaths(0.0, 0.0, k41, false, 3.0)
    let hollow = bagPaths(0.0, 0.0, k41, true, 3.0)
    ctx.ck(solid.size == 3 && hollow.size == 3, "J20 bagPaths n=${solid.size},${hollow.size} want=3,3")
    ctx.ck(solid[0].color == Theme.gold && solid[1].color == Theme.gold, "J20 solid bag fill!=gold")
    ctx.ck(hollow[0].color == Theme.whitePaper && hollow[1].color == Theme.whitePaper,
        "J20 hollow bag fill!=whitePaper")
    ctx.ck(solid[0].stroke == Theme.ink && solid[1].stroke == Theme.ink
        && hollow[0].stroke == Theme.ink && hollow[1].stroke == Theme.ink, "J20 bag stroke!=ink")
    var burdenN: Int64 = 0
    li = 0
    while (li < levels.size) {
        let lv = levels.get(li).getOrThrow()
        match (lv.burden) {
            case Some(b) =>
                burdenN = burdenN + 1
                var onWp = false
                for (wp in lv.waypoints) {
                    if (wp.x == b.loadX && wp.y == b.loadY) {
                        onWp = true
                    }
                    if (wp.x == b.unloadX && wp.y == b.unloadY) {
                        onWp = true
                    }
                }
                ctx.ck(!onWp, "J20 id=${lv.id} load/unload on waypoint cell")
                var inForb = false
                for (fc in b.forbidden) {
                    if (fc.x == b.loadX && fc.y == b.loadY) {
                        inForb = true
                    }
                    if (fc.x == b.unloadX && fc.y == b.unloadY) {
                        inForb = true
                    }
                }
                ctx.ck(!inForb, "J20 id=${lv.id} load/unload in forbidden")
            case None => ()
        }
        li = li + 1
    }
    ctx.ck(burdenN >= 1, "J20 no burden level in catalog")
    /* (d) 斜纹:段在格内(1e-9)、45°、a 左下;底部起完整相邻线 ax 差 ==pitch(1e-6)。 */
    var lv90: Option<LevelDef> = None
    var have90 = false
    li = 0
    while (li < levels.size) {
        let lv = levels.get(li).getOrThrow()
        if (lv.id == 90) {
            lv90 = Some(lv)
            have90 = true
        }
        li = li + 1
    }
    ctx.ck(have90, "J20 level 90 missing from catalog")
    var hi: Int64 = 0
    let pitches = [6.0, 5.0]
    let insets = [0.5, 0.75]
    while (hi < 2) {
        let pitch = pitches[hi]
        let inset = insets[hi]
        var ci: Int64 = 0
        while (ci < 4) {
            let c = cs[ci]
            let (x0, y0) = (8.0, 8.0)
            let segs = hatchSegs(x0, y0, c, pitch, inset)
            ctx.ck(segs.size > 0 && segs.size % 4 == 0,
                "J20 hatch segs=${segs.size} c=${c} pitch=${pitch}")
            var fullAx = ArrayList<Float64>()
            var s: Int64 = 0
            while (s + 3 < segs.size) {
                let ax = segs[s]
                let ay = segs[s + 1]
                let bx = segs[s + 2]
                let by = segs[s + 3]
                ctx.ck(ax >= x0 + inset - 1e-9 && bx <= x0 + c - inset + 1e-9
                    && ay >= y0 + inset - 1e-9 && ay <= y0 + c - inset + 1e-9
                    && by >= y0 + inset - 1e-9 && by <= y0 + c - inset + 1e-9,
                    "J20 hatch out of cell c=${c} seg=(${ax},${ay})-(${bx},${by})")
                ctx.ck(absF(absF(bx - ax) - absF(by - ay)) < 1e-9,
                    "J20 hatch not 45deg c=${c} dx=${bx - ax} dy=${by - ay}")
                ctx.ck(ax < bx && ay > by, "J20 hatch a not lower-left c=${c} seg=(${ax},${ay})-(${bx},${by})")
                if (absF(ay - (y0 + c - inset)) < 1e-9) {
                    fullAx.add(ax)
                }
                s = s + 4
            }
            ctx.ck(fullAx.size >= 2, "J20 hatch full lines=${fullAx.size} want>=2 c=${c} pitch=${pitch}")
            var f: Int64 = 1
            while (f < fullAx.size) {
                ctx.ck(absF(fullAx.get(f).getOrThrow() - fullAx.get(f - 1).getOrThrow() - pitch) < 1e-6,
                    "J20 hatch pitch=${fullAx.get(f).getOrThrow() - fullAx.get(f - 1).getOrThrow()} want=${pitch} c=${c}")
                f = f + 1
            }
            ci = ci + 1
        }
        hi = hi + 1
    }
    match (lv90) {
        case Some(lv) =>
            /* (d 续) level 90 空载/负重斜纹色与宽;under 层全部 M 开头;
               禁区格填色/边随载态切换,非禁区格不变。 */
            let g = PatrolGame(lv)
            /* 禁区格取自 lv.burden.forbidden(JSON rc=[行,列] → Cell(x=列,y=行)) */
            var fb0 = Cell(0, 0)
            var fb1 = Cell(0, 0)
            match (lv.burden) {
                case Some(b) =>
                    if (b.forbidden.size >= 1) {
                        fb0 = b.forbidden.get(0).getOrThrow()
                    }
                    if (b.forbidden.size >= 2) {
                        fb1 = b.forbidden.get(1).getOrThrow()
                    }
                case None => ()
            }
            let under0 = buildBoardMechUnder(g, g43, 3.0)
            var hatch0 = false
            for (p in under0) {
                ctx.ck(startsWithM(p.commands), "J20 under cmds not M: '${p.commands}'")
                if (p.color == Theme.paperLine && absF(p.strokeW - 1.0) < 1e-9) {
                    hatch0 = true
                }
            }
            ctx.ck(hatch0, "J20 unladen hatch(paperLine,1.0) missing")
            ctx.ck(mechCellFill(g, fb0.x, fb0.y, Theme.whitePaper) == Theme.whitePaper
                && mechCellFill(g, fb1.x, fb1.y, Theme.whitePaper) == Theme.whitePaper,
                "J20 unladen forbidden fill!=base")
            ctx.ck(mechCellStroke(g, fb0.x, fb0.y) == Theme.paperLine, "J20 unladen forbidden stroke!=paperLine")
            ctx.ck(absF(mechCellStrokeW(g, fb0.x, fb0.y) - 1.0) < 1e-9, "J20 unladen forbidden strokeW!=1")
            ctx.ck(mechCellFill(g, 0, 0, Theme.whitePaper) == Theme.whitePaper,
                "J20 unladen normal fill changed")
            g.laden = true
            let under1 = buildBoardMechUnder(g, g43, 3.0)
            var hatch1 = false
            for (p in under1) {
                ctx.ck(startsWithM(p.commands), "J20 laden under cmds not M")
                if (p.color == Theme.inkMuted && absF(p.strokeW - 1.5) < 1e-9) {
                    hatch1 = true
                }
            }
            ctx.ck(hatch1, "J20 laden hatch(inkMuted,1.5) missing")
            ctx.ck(mechCellFill(g, fb0.x, fb0.y, Theme.whitePaper) == Theme.paperShade
                && mechCellFill(g, fb1.x, fb1.y, Theme.whitePaper) == Theme.paperShade,
                "J20 laden forbidden fill!=paperShade")
            ctx.ck(mechCellStroke(g, fb0.x, fb0.y) == Theme.inkMuted, "J20 laden forbidden stroke!=inkMuted")
            ctx.ck(absF(mechCellStrokeW(g, fb0.x, fb0.y) - 1.0) < 1e-9, "J20 laden forbidden strokeW!=1")
            ctx.ck(mechCellFill(g, 0, 0, Theme.whitePaper) == Theme.whitePaper,
                "J20 laden normal fill changed")
            /* (f) 徽章:负重态比空载多 4 个 path,末 4 个=[圆(whitePaper/ink/1.0),袋×3],
               末个 strokeW==0.5*1.4;圆心=头格 (+10,-10)。 */
            let gb = PatrolGame(lv)
            ctx.ck(gb.tryStep(Cell(6, 6)), "J20 id=90 tryStep(6,6) start rejected")
            let p0 = buildBoardMechPaths(gb, g43, 3.0)
            gb.laden = true
            let p1 = buildBoardMechPaths(gb, g43, 3.0)
            ctx.ck(p1.size - p0.size == 4, "J20 badge delta=${p1.size - p0.size} want=4 (n0=${p0.size})")
            if (p1.size >= 4) {
                let circ = p1.get(p1.size - 4).getOrThrow()
                ctx.ck(circ.color == Theme.whitePaper && circ.stroke == Theme.ink
                    && absF(circ.strokeW - 1.0) < 1e-9,
                    "J20 badge circle color/stroke/w=${circ.color}/${circ.stroke}/${circ.strokeW}")
                ctx.ck(circ.commands == circlePathCmds(g43.centerX(6) + 10.0, g43.centerY(6) - 10.0, 7.5, 3.0),
                    "J20 badge circle center cmds mismatch")
                let last = p1.get(p1.size - 1).getOrThrow()
                ctx.ck(last.stroke == Theme.ink && absF(last.strokeW - 0.5 * 1.4) < 1e-9,
                    "J20 badge bag stroke/w=${last.stroke}/${last.strokeW} want ink/${0.5 * 1.4}")
            }
            /* (e) 触发格缺角:x/y 最大偏移 ==8k(1e-9),顶点在 [0,c] 内,斜边不共线。 */
            var ei: Int64 = 0
            while (ei < 4) {
                let c = cs[ei]
                let kk = skinK(c)
                let np = collapseNotchPts(0.0, 0.0, c)
                ctx.ck(np.size == 14, "J20 notch size=${np.size} want=14 (7 verts)")
                var mAx = 0.0
                var mAy = 0.0
                var ok = true
                var vi: Int64 = 0
                while (vi < 7) {
                    if (np[vi * 2] > mAx) {
                        mAx = np[vi * 2]
                    }
                    if (np[vi * 2 + 1] > mAy) {
                        mAy = np[vi * 2 + 1]
                    }
                    if (np[vi * 2] < 0.0 || np[vi * 2] > c || np[vi * 2 + 1] < 0.0 || np[vi * 2 + 1] > c) {
                        ok = false
                    }
                    vi = vi + 1
                }
                ctx.ck(absF(mAx - 8.0 * kk) < 1e-9, "J20 notch maxX=${mAx} want=${8.0 * kk} c=${c}")
                ctx.ck(absF(mAy - 8.0 * kk) < 1e-9, "J20 notch maxY=${mAy} want=${8.0 * kk} c=${c}")
                ctx.ck(ok, "J20 notch verts out of [0,${c}] c=${c}")
                /* 斜边第 2..6 点(p1,p2,p3)叉积 */
                let v1x = np[2] - np[4]
                let v1y = np[3] - np[5]
                let v2x = np[6] - np[4]
                let v2y = np[7] - np[5]
                ctx.ck(absF(v1x * v2y - v1y * v2x) > 1e-6, "J20 notch hypotenuse collinear c=${c}")
                ei = ei + 1
            }
        case None => ()
    }
    /* (g) 顶栏 chip 排居中:左右边距相等(1e-9)、相邻间距 ==8、加第三 chip 后左移
       重新居中;「负重」chip 宽 = 32+15*2+12 == 74。 */
    let w2 = [84.0, 90.0]
    let o2 = chipRowOffsets(320.0, w2, 8.0)
    ctx.ck(o2.size == 2, "J20 chips2 n=${o2.size} want=2")
    let lm2 = o2.get(0).getOrThrow()
    let rm2 = 320.0 - (o2.get(1).getOrThrow() + w2[1])
    ctx.ck(absF(lm2 - rm2) < 1e-9, "J20 chips2 margins l=${lm2} r=${rm2}")
    ctx.ck(absF((o2.get(1).getOrThrow() - o2.get(0).getOrThrow()) - (w2[0] + 8.0)) < 1e-9,
        "J20 chips2 gap=${o2.get(1).getOrThrow() - o2.get(0).getOrThrow() - w2[0]} want=8")
    let w3 = [84.0, 90.0, 74.0]
    let o3 = chipRowOffsets(320.0, w3, 8.0)
    ctx.ck(o3.size == 3, "J20 chips3 n=${o3.size} want=3")
    let lm3 = o3.get(0).getOrThrow()
    let rm3 = 320.0 - (o3.get(2).getOrThrow() + w3[2])
    ctx.ck(absF(lm3 - rm3) < 1e-9, "J20 chips3 margins l=${lm3} r=${rm3}")
    ctx.ck(lm3 < lm2, "J20 chips3 left margin ${lm3} not smaller than ${lm2}")
    ctx.ck(absF((o3.get(1).getOrThrow() - o3.get(0).getOrThrow()) - (w3[0] + 8.0)) < 1e-9
        && absF((o3.get(2).getOrThrow() - o3.get(1).getOrThrow()) - (w3[1] + 8.0)) < 1e-9,
        "J20 chips3 gaps !=8")
    ctx.ck(absF((32.0 + 15.0 * 2.0 + 12.0) - 74.0) < 1e-9, "J20 burden chip w=${32.0 + 15.0 * 2.0 + 12.0} want=74")
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
    /* J14 定向几何/滑行检查。 */
    j14SlideGeomTests(levels, ctx)
    /* J20 塌桥/负重皮肤几何检查。 */
    j20SkinGeomTests(levels, ctx)
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

