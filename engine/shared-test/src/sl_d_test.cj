package yilu_zip_test

/* 滑行(泽地)撤销单元测试 D(不读 levels.json):一输入的滑行段=一个撤销单元;
   拖回单元中间/入口前头格撤销整段,拖滑行头格拒绝。参照 patrol.cj 的 slideSegment。 */
import std.unittest.*
import std.unittest.testmacro.*
import yilu_zip.engine.*
import yilu_zip.game.*

/* 单行盘6 + 泽地 x=1..4:(0,0) 迈入 (1,0) 沿 +x 滑至 (4,0),path size=5。 */
func sl_d_mkSlideRow6(): LevelDef {
    let lv = mkLevel(6, 1, [(1, 0, 0)])
    lv.slideCells.add(Cell(1, 0))
    lv.slideCells.add(Cell(2, 0))
    lv.slideCells.add(Cell(3, 0))
    lv.slideCells.add(Cell(4, 0))
    return lv
}

/* 11) 一输入=一个撤销单元:走 (0,0),(1,0) → size 5;undo 一次回 size 1,
   再 undo 回 size 0,第三次 undo 为 false。 */
@Test
func sl_d_slideUndoIsOneUnit() {
    let g = PatrolGame(sl_d_mkSlideRow6())
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(g.path.size(), 5)
    @Assert(g.undo())
    @Assert(g.path.size(), 1)
    @Assert(g.undo())
    @Assert(g.path.size(), 0)
    @Assert(!g.undo())
}

/* 12) 拖回滑行中间格 (2,0):true 且撤销整个滑行单元,size 回 1。 */
@Test
func sl_d_slideDragBackMiddleUndoesUnit() {
    let g = PatrolGame(sl_d_mkSlideRow6())
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(g.tryStep(Cell(2, 0)))
    @Assert(g.path.size(), 1)
}

/* 13) 拖回滑行入口前头格 (0,0):true 且撤销整个滑行单元,size 回 1。 */
@Test
func sl_d_slideDragBackToEntryHeadUndoesUnit() {
    let g = PatrolGame(sl_d_mkSlideRow6())
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(g.tryStep(Cell(0, 0)))
    @Assert(g.path.size(), 1)
}

/* 14) 拖到滑行头格 (4,0):false,REJECT_VISITED,path 不变 size 5。 */
@Test
func sl_d_slideDragOntoHeadRejected() {
    let g = PatrolGame(sl_d_mkSlideRow6())
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(!g.tryStep(Cell(4, 0)))
    @Assert(g.path.size(), 5)
    @Assert(g.lastReject, REJECT_VISITED)
}
