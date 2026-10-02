package yilu_zip_test

/* 引擎重放测试:对 id 0..99 全部用 boards-locked 归档 path(设计解)逐步重放,零跳过
   (slide / collapse 关同样重放)。每关必须每步 tryStep 成功、引擎 path 与设计 path
   逐格一致、size 相等且 isWin();滑行/渡口一次推多格,步进用 i = game.path.size()。
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
    var ferryPassIds = "" /* ferry 关里 甲→乙 相邻恰一次的 id 列表(逗号分隔) */
    var slideTotal = 0
    var slidePassIds = "" /* slide 关里重放通过的 id 列表(逗号分隔) */
    var collapseTotal = 0
    var collapsePassIds = "" /* collapse 关里重放通过的 id 列表(逗号分隔) */
    var id: Int64 = 0
    while (id < levels.size) {
        let lv = levels[id]
        replayed = replayed + 1
        let isSlide = lv.slideCells.size > 0
        let isCollapse = lv.collapse.isSome()
        if (isSlide) {
            slideTotal = slideTotal + 1
        }
        if (isCollapse) {
            collapseTotal = collapseTotal + 1
        }
        let design = lockedPath(id)
        let game = PatrolGame(lv)
        var passed = true
        var i: Int64 = 0
        while (i < design.size) {
            let target = design[i]
            if (!game.tryStep(target)) {
                failures = failures + "FAIL id=${id} i=${i} tryStep=false lastReject=${game.lastReject} expected=(${target.x},${target.y}) engineSize=${game.path.size()}\n"
                passed = false
                break
            }
            i = game.path.size()
        }
        if (passed) {
            if (game.path.size() != design.size) {
                failures = failures + "FAIL id=${id} size engine=${game.path.size()} design=${design.size}\n"
                passed = false
            } else {
                var j: Int64 = 0
                while (j < design.size) {
                    let a = game.path.at(j)
                    let b = design[j]
                    if (a.x != b.x || a.y != b.y) {
                        failures = failures + "FAIL id=${id} j=${j} engine=(${a.x},${a.y}) design=(${b.x},${b.y})\n"
                        passed = false
                    }
                    j = j + 1
                }
                if (!game.isWin()) {
                    failures = failures + "FAIL id=${id} isWin=false after full-path replay\n"
                    passed = false
                }
            }
        }
        if (passed) {
            /* 单向正向边:设计路径里被约束且按 from→to 走过的边。
               若重放途中被 REJECT_ONE_WAY 拒绝,上面已记入失败。 */
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
                    if (ferryPassIds == "") {
                        ferryPassIds = "${id}"
                    } else {
                        ferryPassIds = ferryPassIds + ",${id}"
                    }
                } else {
                    failures = failures + "FAIL id=${id} ferry jia->yi adjacent count=${cnt} expect=1\n"
                }
            case None => ()
        }
        if (passed) {
            if (isSlide) {
                if (slidePassIds == "") {
                    slidePassIds = "${id}"
                } else {
                    slidePassIds = slidePassIds + ",${id}"
                }
            }
            if (isCollapse) {
                if (collapsePassIds == "") {
                    collapsePassIds = "${id}"
                } else {
                    collapsePassIds = collapsePassIds + ",${id}"
                }
            }
        }
        id = id + 1
    }
    println("ONE-WAY FORWARD edges walked in replay: ${oneWayFwd}")
    println("REPLAY SUMMARY: replayed=${replayed} skipped=${skipped}")
    println("SLIDE replayed ok: total=${slideTotal} ids=${slidePassIds}")
    println("COLLAPSE replayed ok: total=${collapseTotal} ids=${collapsePassIds}")
    if (failures == "") {
        println("FERRY REPLAYED: ${ferryPassIds} ok")
    }
    if (failures != "") {
        println("REPLAY FAILURES:")
        println(failures)
    }
    @Assert(replayed, 100)
    @Assert(skipped, 0)
    @Assert(ferryAdjOk, 8) /* 8 个 ferry 关(52,57,59,60,63,67,87,89)甲→乙 相邻各一次 */
    @Assert(failures, "")
}
