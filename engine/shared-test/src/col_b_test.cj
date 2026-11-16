package yilu_zip_test
import std.unittest.*
import std.unittest.testmacro.*
import yilu_zip.engine.*
import yilu_zip.game.*
/* 3×2,1 号路标 (0,0),触发 (1,0) 切边 (1,1)-(2,1)。 */
func colb_board(): LevelDef {
    let lv = mkLevel(3, 2, [(1, 0, 0)])
    lv.collapse = Some(CollapseDef(1, 0, 1, 1, 2, 1))
    return lv
}
/* 6) 滑行中触发切 (3,0)-(4,0):停在 x=3,path==4,collapseDown。 */
@Test
func colb_collapseInsideSlideCutsLaterCells() {
    let lv = mkLevel(6, 1, [(1, 0, 0)])
    for (x in 1..5) { lv.slideCells.add(Cell(x, 0)) }
    lv.collapse = Some(CollapseDef(2, 0, 3, 0, 4, 0))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(g.path.size(), 4)
    @Assert(g.collapseDown)
}
@Test /* 7) undo 撤触发格后塌桥复位;撤其后那步仍 true。 */
func colb_collapseUndoRestoresBridge() {
    let g = PatrolGame(colb_board())
    @Assert(stepAll(g, [(0, 0), (1, 0), (1, 1)]))
    @Assert(g.collapseDown)
    @Assert(g.undo()) /* 撤 (1,1) */
    @Assert(g.collapseDown)
    @Assert(g.undo()) /* 撤触发格 (1,0) */
    @Assert(!g.collapseDown)
    @Assert(!g.isEdgeCollapsed(1, 1, 2, 1))
}
@Test /* 8) clear/reset 复位塌桥,reset 后 path 空。 */
func colb_collapseClearAndResetRestore() {
    let lv = colb_board()
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    g.clear()
    @Assert(!g.collapseDown)
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(g.collapseDown)
    g.reset(lv)
    @Assert(!g.collapseDown)
    @Assert(g.path.size(), 0)
}
@Test /* 9) 走/undo/再走/clear 全程 lv 与 grid 的 walls 尺寸不变。 */
func colb_collapseDoesNotMutateSharedWalls() {
    let lv = colb_board()
    lv.walls.add(Wall(2, 0, 2, 1))
    let g = PatrolGame(lv)
    let lvW = lv.walls.size
    let gW = g.grid.walls.size
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(g.undo())
    @Assert(stepAll(g, [(1, 0)]))
    g.clear()
    @Assert(lv.walls.size, lvW)
    @Assert(g.grid.walls.size, gW)
}
