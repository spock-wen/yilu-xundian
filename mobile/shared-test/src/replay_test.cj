package yilu_zip_test

/* 引擎重放测试:对 id 0..99 用 boards-locked 归档 path(设计解)逐步重放。
   ferry / slide / collapse 尚未实现 → 记 SKIPPED 并逐条打印 SKIP 行;
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
    var failures = ""
    var id: Int64 = 0
    while (id < levels.size) {
        let lv = levels[id]
        var skip = false
        if (lv.ferry.isSome()) {
            println("SKIP id=${id} reason=ferry")
            skip = true
        }
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
        }
        id = id + 1
    }
    println("ONE-WAY FORWARD edges walked in replay: ${oneWayFwd}")
    println("REPLAY SUMMARY: replayed=${replayed} skipped=${skipped}")
    if (failures != "") {
        println("REPLAY FAILURES:")
        println(failures)
    }
    @Assert(replayed + skipped, 100)
    @Assert(failures, "")
}
