package yilu_zip_test

/* 滑行(泽地)单元测试 A(不读 levels.json):单行盘 6,仅 1 号路标 (0,0),
   泽地 (1,0)-(4,0)。墙/单向边截断滑行段;坐标 x=列,y=行;参照
   mobile/shared/src/game/patrol.cj 的 slideSegment(tools/solve_levels.py)。 */
import std.unittest.*
import std.unittest.testmacro.*
import yilu_zip.engine.*
import yilu_zip.game.*

/* 共用盘:单行 6,泽地 (1,0)-(4,0),无其他机制。 */
func sl_a_mkSlide6(): LevelDef {
    let lv = mkLevel(6, 1, [(1, 0, 0)])
    lv.slideCells.add(Cell(1, 0))
    lv.slideCells.add(Cell(2, 0))
    lv.slideCells.add(Cell(3, 0))
    lv.slideCells.add(Cell(4, 0))
    return lv
}

/* 1) 滑到尽头:无阻挡时一次输入从 (1,0) 滑到 (4,0);path 1→5,末格 x=4。 */
@Test
func sl_a_slideToEnd() {
    let g = PatrolGame(sl_a_mkSlide6())
    @Assert(stepAll(g, [(0, 0)]))
    @Assert(g.tryStep(Cell(1, 0))) /* 踏入泽地 → 滑到 (4,0) 停 */
    @Assert(g.path.size(), 5)
    @Assert(g.path.at(4).x, 4) /* 末格 x=4 */
    @Assert(g.filled(), 5)
}

/* 2) 墙截断:Wall(2,0)-(3,0) 挡住 (2,0)→(3,0),滑行停在 (2,0)。 */
@Test
func sl_a_slideStopsAtWall() {
    let lv = sl_a_mkSlide6()
    lv.walls.add(Wall(2, 0, 3, 0))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(g.path.size(), 3) /* (0,0),(1,0),(2,0) */
    @Assert(g.path.at(2).x, 2) /* 末格 x=2 */
}

/* 3) 单向逆向截断:OneWay(3,0)→(2,0) 使 (2,0)→(3,0) 逆行,滑行停在 (2,0)。 */
@Test
func sl_a_slideStopsAtOneWayReverse() {
    let lv = sl_a_mkSlide6()
    lv.oneWays.add(OneWay(3, 0, 2, 0))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(g.path.size(), 3) /* (0,0),(1,0),(2,0) */
    @Assert(g.path.at(2).x, 2) /* 末格 x=2 */
}
