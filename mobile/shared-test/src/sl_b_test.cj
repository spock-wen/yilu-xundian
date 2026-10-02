package yilu_zip_test

/* 滑行(泽地)单元测试 B(不读 levels.json):数字格前截断、非泽地截断、
   边界截断;起点格本身不滑。坐标 x=列,y=行;参照
   mobile/shared/src/game/patrol.cj 的 slideSegment(tools/solve_levels.py)。 */
import std.unittest.*
import std.unittest.testmacro.*
import yilu_zip.engine.*
import yilu_zip.game.*

/* 4) 数字格前截断:泽地 (1,0)-(4,0),2 号路标在 (3,0);滑行停其前一格 x=2。 */
@Test
func sl_b_slideStopsAtNumbered() {
    let lv = mkLevel(6, 1, [(1, 0, 0), (2, 3, 0)])
    lv.slideCells.add(Cell(1, 0))
    lv.slideCells.add(Cell(2, 0))
    lv.slideCells.add(Cell(3, 0))
    lv.slideCells.add(Cell(4, 0))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(g.path.size(), 3)
    @Assert(g.path.at(2).x, 2) /* 末格 = 数字格前一格 */
}

/* 5) 非泽地截断:泽地只 (1,0)(2,0),(3,0) 非泽地 → 滑行停 (2,0),末格 x=2。 */
@Test
func sl_b_slideStopsAtNonSlide() {
    let lv = mkLevel(6, 1, [(1, 0, 0)])
    lv.slideCells.add(Cell(1, 0))
    lv.slideCells.add(Cell(2, 0))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(g.path.size(), 3)
    @Assert(g.path.at(2).x, 2)
}

/* 6) 边界截断:单行 4,泽地 (1,0)-(3,0),滑到右缘 (3,0),path 4,末格 x=3。 */
@Test
func sl_b_slideStopsAtBounds() {
    let lv = mkLevel(4, 1, [(1, 0, 0)])
    lv.slideCells.add(Cell(1, 0))
    lv.slideCells.add(Cell(2, 0))
    lv.slideCells.add(Cell(3, 0))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(g.path.size(), 4)
    @Assert(g.path.at(3).x, 3)
}

/* 7) 起点格本身不滑:单行 3,泽地 (0,0)(1,0),tryStep(0,0) 只进起点,path 1。 */
@Test
func sl_b_slideStartCellIsNotSlid() {
    let lv = mkLevel(3, 1, [(1, 0, 0)])
    lv.slideCells.add(Cell(0, 0))
    lv.slideCells.add(Cell(1, 0))
    let g = PatrolGame(lv)
    @Assert(g.tryStep(Cell(0, 0)))
    @Assert(g.path.size(), 1)
}
