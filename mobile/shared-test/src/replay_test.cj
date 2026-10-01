package yilu_zip_test

/* 引擎重放测试:对 id 0..99 用 boards-locked 归档 path(设计解)逐步重放。
   slide / collapse 尚未实现 → 记 SKIPPED 并逐条打印 SKIP 行(ferry 已实现,须重放);
   其余关必须每步 tryStep 成功、引擎 path 与设计 path 逐格一致且 isWin()。
   所有失败先收集,最后统一打印完整列表再断言(引擎 bug 只报告不修改)。 */
import std.collection.ArrayList
import std.unittest.*
import std.unittest.testmacro.*
import yilu_zip.engine.*
import yilu_zip.game.*

@Test
func replayLockedDesignPaths() {
    let levels = loadAllLevels()
    var replayed = 0
    var skipped = 0
    var oneWayFwd = 0
    var ferryAdjOk = 0 /* 设计路径里 甲→乙 恰好相邻出现一次的 ferry 关数 */
    var failures = ""
    var id: Int64 = 0
    while (id < levels.size) {
        let lv = levels[id]
        var skip = false
        if (lv.slideCells.size > 0) {
            println("SKIP id=${id} reason=slide")
            skip = true
        }
        if (lv.collapse.isSome()) {
            println("SKIP id=${id} reason=collapse")
            skip = true
        }
        if (skip) {
            skipped = skipped + 1
        } else {
            replayed = replayed + 1
            let design = lockedPath(id)
            let game = PatrolGame(lv)
            var i: Int64 = 0
            var stepFail = false
            while (i < design.size) {
                let target = design[i]
                if (!game.tryStep(target)) {
                    failures = failures + "FAIL id=${id} i=${i} tryStep=false lastReject=${game.lastReject} expected=(${target.x},${target.y}) engineSize=${game.path.size()}\n"
                    stepFail = true
                    break
                }
                i = game.path.size()
            }
            if (!stepFail) {
                if (game.path.size() != design.size) {
                    failures = failures + "FAIL id=${id} size engine=${game.path.size()} design=${design.size}\n"
                } else {
                    var j: Int64 = 0
                    while (j < design.size) {
                        let a = game.path.at(j)
                        let b = design[j]
                        if (a.x != b.x || a.y != b.y) {
                            failures = failures + "FAIL id=${id} j=${j} engine=(${a.x},${a.y}) design=(${b.x},${b.y})\n"
                        }
                        j = j + 1
                    }
                    if (!game.isWin()) {
                        failures = failures + "FAIL id=${id} isWin=false after full-path replay\n"
                    }
                }
                /* 单向正向边:设计路径里被约束且按 from→to 走过的边。
                   若重放途中被 REJECT_ONE_WAY 拒绝,上面已记入 stepFail。 */
                var k: Int64 = 1
                while (k < design.size) {
                    let p = design[k - 1]
                    let q = design[k]
                    if (lv.oneWayConstrains(p, q) && lv.oneWayAllows(p, q)) {
                        oneWayFwd = oneWayFwd + 1
                    }
                    k = k + 1
                }
            }
            /* ferry 关:设计路径里 甲 紧邻 乙(甲后紧跟乙)且恰好出现一次。 */
            match (lv.ferry) {
                case Some(f) =>
                    var cnt: Int64 = 0
                    var m: Int64 = 1
                    while (m < design.size) {
                        let p = design[m - 1]
                        let q = design[m]
                        if (p.x == f.jiaX && p.y == f.jiaY && q.x == f.yiX && q.y == f.yiY) {
                            cnt = cnt + 1
                        }
                        m = m + 1
                    }
                    if (cnt == 1) {
                        ferryAdjOk = ferryAdjOk + 1
                    } else {
                        failures = failures + "FAIL id=${id} ferry jia->yi adjacent count=${cnt} expect=1\n"
                    }
                case None => ()
            }
        }
        id = id + 1
    }
    println("ONE-WAY FORWARD edges walked in replay: ${oneWayFwd}")
    println("REPLAY SUMMARY: replayed=${replayed} skipped=${skipped}")
    if (failures == "") {
        println("FERRY REPLAYED: 52,57,59,60,63,87,89 ok")
    }
    if (failures != "") {
        println("REPLAY FAILURES:")
        println(failures)
    }
    @Assert(replayed + skipped, 100)
    /* 仍 SKIP:slide 9 关(40,43,45,47,49,65,67,75,77) + collapse 3 关(95,97,99),
       67 同时 ferry+slide 只计一次 → skipped=12, replayed=88。 */
    @Assert(skipped, 12)
    @Assert(replayed, 88)
    @Assert(ferryAdjOk, 7) /* 7 个重放的 ferry 关 甲→乙 相邻各一次(67 属 slide 跳过) */
    @Assert(failures, "")
}
