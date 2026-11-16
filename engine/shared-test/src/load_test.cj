package yilu_zip_test

import std.unittest.*
import std.unittest.testmacro.*
import yilu_zip.engine.*
import yilu_zip.game.*

/* (a) 100 关全部加载无错,且 id 依次为 0..99。 */
@Test
func loads100LevelsInOrder() {
    let levels = loadAllLevels()
    @Assert(levels.size, 100)
    var i: Int64 = 0
    while (i < levels.size) {
        @Assert(levels[i].id, i)
        i = i + 1
    }
}

/* (b) 各机制关卡计数(与 build_levels 源数据一致)。 */
@Test
func mechanicCounts() {
    let levels = loadAllLevels()
    var ferry = 0
    var oneWays = 0
    var slide = 0
    var seal = 0
    var token = 0
    var collapse = 0
    var burden = 0
    for (lv in levels) {
        if (lv.ferry.isSome()) {
            ferry = ferry + 1
        }
        if (lv.oneWays.size > 0) {
            oneWays = oneWays + 1
        }
        if (lv.slideCells.size > 0) {
            slide = slide + 1
        }
        if (lv.sealGates.size > 0) {
            seal = seal + 1
        }
        if (lv.tokenCells.size > 0) {
            token = token + 1
        }
        if (lv.collapse.isSome()) {
            collapse = collapse + 1
        }
        if (lv.burden.isSome()) {
            burden = burden + 1
        }
    }
    @Assert(ferry, 8)
    @Assert(oneWays, 19)
    @Assert(slide, 9)
    @Assert(seal, 6)
    @Assert(token, 6)
    @Assert(collapse, 3)
    @Assert(burden, 2)
}

/* (c) 无机制键的关卡数 = 67,且这些关卡 hasMechanics() == false(反之亦然)。 */
@Test
func levelsWithoutMechanics() {
    let levels = loadAllLevels()
    var plain = 0
    for (lv in levels) {
        var hasKey = false
        if (lv.ferry.isSome() || lv.collapse.isSome() || lv.burden.isSome()) {
            hasKey = true
        }
        if (lv.oneWays.size > 0 || lv.slideCells.size > 0) {
            hasKey = true
        }
        if (lv.sealGates.size > 0 || lv.tokenCells.size > 0) {
            hasKey = true
        }
        if (!hasKey) {
            plain = plain + 1
            @Assert(!lv.hasMechanics())
        } else {
            @Assert(lv.hasMechanics())
        }
    }
    @Assert(plain, 67)
}

/* (d) 抽样:id 90 的 burden 与 id 95 的 collapse。 */
@Test
func sampleBurdenId90() {
    let levels = loadAllLevels()
    match (levels[90].burden) {
        case None => @Assert(false)
        case Some(b) =>
            @Assert(b.forbidden.size, 2)
            var has30 = false
            var has41 = false
            for (c in b.forbidden) {
                if (c.x == 3 && c.y == 0) {
                    has30 = true
                }
                if (c.x == 4 && c.y == 1) {
                    has41 = true
                }
            }
            @Assert(has30)
            @Assert(has41)
            @Assert(b.loadX, 4)
            @Assert(b.loadY, 5)
            @Assert(b.startLaden, false)
    }
}

@Test
func sampleCollapseId95() {
    let levels = loadAllLevels()
    match (levels[95].collapse) {
        case None => @Assert(false)
        case Some(cd) =>
            @Assert(cd.triggerX, 0)
            @Assert(cd.triggerY, 0)
            @Assert(cd.x1, 1)
            @Assert(cd.y1, 1)
            @Assert(cd.x2, 2)
            @Assert(cd.y2, 1)
    }
}
