package yilu_zip_test

/* 滑行(泽地)单元测试 C(不读 levels.json):已访格截断、渡口甲/乙前截断。
   坐标 x=列,y=行;参照 mobile/shared/src/game/patrol.cj 的 slideSegment。 */
import std.unittest.*
import std.unittest.testmacro.*
import yilu_zip.engine.*
import yilu_zip.game.*

/* 8) 已访格截断:2×4,泽地 (0,2)(0,1),自 (0,3) 上滑,停已访 (0,0) 前一格。 */
@Test
func sl_c_slideStopsAtVisited() {
    let lv = mkLevel(2, 4, [(1, 0, 0)])
    lv.slideCells.add(Cell(0, 2))
    lv.slideCells.add(Cell(0, 1))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0), (1, 1), (1, 2), (1, 3), (0, 3)]))
    @Assert(g.tryStep(Cell(0, 2))) /* 上滑,停 (0,1),(0,0) 已访 */
    @Assert(g.path.size(), 8)
    @Assert(g.path.at(7).x, 0)
    @Assert(g.path.at(7).y, 1) /* 末格 (0,1) */
}

/* 9) 渡口甲前截断:单行 5,泽地 x=1..3,甲=(3,0) 乙=(4,0);停甲前 x=2。 */
@Test
func sl_c_slideStopsBeforeFerryJia() {
    let lv = mkLevel(5, 1, [(1, 0, 0)])
    lv.slideCells.add(Cell(1, 0))
    lv.slideCells.add(Cell(2, 0))
    lv.slideCells.add(Cell(3, 0))
    lv.ferry = Some(FerryDef(3, 0, 4, 0))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(g.path.size(), 3)
    @Assert(g.path.at(2).x, 2) /* 末格 x=2 */
}

/* 10) 渡口乙前截断:单行 5,泽地 x=1..3,甲=(4,0) 乙=(3,0);停乙前 x=2。 */
@Test
func sl_c_slideStopsBeforeFerryYi() {
    let lv = mkLevel(5, 1, [(1, 0, 0)])
    lv.slideCells.add(Cell(1, 0))
    lv.slideCells.add(Cell(2, 0))
    lv.slideCells.add(Cell(3, 0))
    lv.ferry = Some(FerryDef(4, 0, 3, 0))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(g.path.size(), 3)
    @Assert(g.path.at(2).x, 2) /* 末格 x=2 */
}
