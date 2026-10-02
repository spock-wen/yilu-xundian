package yilu_zip_test

/* 滑行(泽地)单元测试 F:符闸/奇偶/负重与滑行段;坐标 x=列,y=行;
   参照 mobile/shared/src/game/patrol.cj 的 slideSegment。 */
import std.collection.ArrayList
import std.unittest.*
import std.unittest.testmacro.*
import yilu_zip.engine.*
import yilu_zip.game.*

/* 单行6 + 泽地 x=1..4。 */
func sl_f_mkSlide6(): LevelDef {
    let lv = mkLevel(6, 1, [(1, 0, 0)])
    lv.slideCells.add(Cell(1, 0))
    lv.slideCells.add(Cell(2, 0))
    lv.slideCells.add(Cell(3, 0))
    lv.slideCells.add(Cell(4, 0))
    return lv
}

/* 16) 符闸:闸前一格 x=3 停(size 4,不整段拒绝),段后 hasToken,再走可过闸。 */
@Test
func sl_f_slideTokenGateStopsBeforeGate() {
    let lv = sl_f_mkSlide6()
    lv.tokenCells.add(Cell(2, 0))
    lv.sealGates.add(SealGate(3, 0, 4, 0))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(g.path.size(), 4)
    @Assert(g.hasToken)
    @Assert(g.tryStep(Cell(4, 0)))
    @Assert(g.path.size(), 5)
}

/* 17) 起点即符:入口已有符,整段通过闸。 */
@Test
func sl_f_slideStartTokenPassesGate() {
    let lv = sl_f_mkSlide6()
    lv.tokenCells.add(Cell(0, 0))
    lv.sealGates.add(SealGate(1, 0, 2, 0))
    let g = PatrolGame(lv)
    @Assert(g.tryStep(Cell(0, 0)))
    @Assert(g.hasToken)
    @Assert(g.tryStep(Cell(1, 0)))
    @Assert(g.path.size(), 5)
}

/* 18a) 奇偶边 requireOdd:经 x=2→3 时 filled=3 奇,通过,size 5。 */
@Test
func sl_f_slideParityPerCellOdd() {
    let lv = sl_f_mkSlide6()
    lv.parityEdges.add(ParityEdge(2, 0, 3, 0, true, false))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(g.path.size(), 5)
}

/* 18b) 奇偶边 requireEven:filled=3 奇不满足,停 x=2,size 3。 */
@Test
func sl_f_slideParityPerCellEven() {
    let lv = sl_f_mkSlide6()
    lv.parityEdges.add(ParityEdge(2, 0, 3, 0, false, true))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(g.path.size(), 3)
}

/* 6x2 盘 + 泽地 y=0 的 x=1..4。 */
func sl_f_mkSlide6x2(): LevelDef {
    let lv = mkLevel(6, 2, [(1, 0, 0)])
    lv.slideCells.add(Cell(1, 0))
    lv.slideCells.add(Cell(2, 0))
    lv.slideCells.add(Cell(3, 0))
    lv.slideCells.add(Cell(4, 0))
    return lv
}

/* 19a) 负重禁区:装粮后禁 x=3 前停,size 3,laden。 */
@Test
func sl_f_slideBurdenForbiddenStops() {
    let lv = sl_f_mkSlide6x2()
    let forbidden = ArrayList<Cell>()
    forbidden.add(Cell(3, 0))
    lv.burden = Some(BurdenDef(forbidden, 2, 0, 4, 1, false))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(g.path.size(), 3)
    @Assert(g.laden)
}

/* 19b) 滑行不装粮:load 不在滑段 → 无负重,可滑入禁 x=3,size 5,非 laden。 */
@Test
func sl_f_slideBurdenNoLoadPassesForbidden() {
    let lv = sl_f_mkSlide6x2()
    let forbidden = ArrayList<Cell>()
    forbidden.add(Cell(3, 0))
    lv.burden = Some(BurdenDef(forbidden, 5, 1, 4, 1, false))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(g.path.size(), 5)
    @Assert(!g.laden)
}
