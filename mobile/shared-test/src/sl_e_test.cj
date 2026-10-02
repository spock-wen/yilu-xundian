package yilu_zip_test

/* 滑行(泽地)撤销单元测试 E(不读 levels.json):滑行段之后的 Move 序列。
   参照 patrol.cj 的 slideSegment 与 tools/solve_levels.py。坐标 x=列,y=行。 */
import std.unittest.*
import std.unittest.testmacro.*
import yilu_zip.engine.*
import yilu_zip.game.*

/* 6x2 盘,仅 1 号路标 (0,0)(无其他路标 → 不触发最大号规则);
   泽地 y=0 的 x=1..3:(0,0),(1,0) 滑到 x=3(x=4 非泽地 → 停)。 */
func sl_e_mkSlideRow6x2(): LevelDef {
    let lv = mkLevel(6, 2, [(1, 0, 0)])
    lv.slideCells.add(Cell(1, 0))
    lv.slideCells.add(Cell(2, 0))
    lv.slideCells.add(Cell(3, 0))
    return lv
}

/* 15) 滑行段之后的 Move 序列:滑到 x=3 后再走 (4,0) 是正常新输入(size 5);
   拖回 (3,0) 只撤销这 1 格单元(size 4,滑行单元仍在);
   再拖回 (2,0) 撤销整个滑行单元(size 1)。 */
@Test
func sl_e_slideMoveSequenceBeyondHead() {
    let g = PatrolGame(sl_e_mkSlideRow6x2())
    @Assert(stepAll(g, [(0, 0), (1, 0)])) /* 迈入泽地 → 滑到 x=3 */
    @Assert(g.path.size(), 4)
    @Assert(g.tryStep(Cell(4, 0))) /* 滑行头之外的下一格 = 正常新输入 */
    @Assert(g.path.size(), 5)
    @Assert(g.tryStep(Cell(3, 0))) /* 拖回滑行头 = 上一单元的起点前格 */
    @Assert(g.path.size(), 4) /* 只撤销这 1 格单元,滑行单元仍在 */
    @Assert(g.tryStep(Cell(2, 0))) /* 再拖回滑行中间格 */
    @Assert(g.path.size(), 1) /* 撤销整个滑行单元 */
}
