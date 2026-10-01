package yilu_zip_test

import std.unittest.*
import std.unittest.testmacro.*
import yilu_zip.engine.*
import yilu_zip.game.*

func colAGame(cols: Int64, rows: Int64, c: Option<CollapseDef>): PatrolGame {
    let lv = mkLevel(cols, rows, [(1, 0, 0)])
    lv.collapse = c
    return PatrolGame(lv)
}

@Test
func colACollapseCutsAfterTriggerInput() {
    let g = colAGame(3, 2, Some(CollapseDef(1, 0, 1, 1, 2, 1)))
    @Assert(g.tryStep(Cell(0, 0)))
    @Assert(!g.isEdgeCollapsed(1, 1, 2, 1))
    @Assert(g.tryStep(Cell(1, 0)))
    @Assert(g.isEdgeCollapsed(1, 1, 2, 1))
    @Assert(g.collapseDown)
    @Assert(g.tryStep(Cell(1, 1)))
    @Assert(!g.tryStep(Cell(2, 1)))
    @Assert(g.lastReject, REJECT_WALL)
    @Assert(g.path.size(), 3)
}

@Test
func colBCollapseControlEdgeUsableWithoutTrigger() {
    let g = colAGame(3, 2, Some(CollapseDef(1, 0, 1, 1, 2, 1)))
    @Assert(stepAll(g, [(0, 0), (0, 1), (1, 1), (2, 1)]))
    @Assert(!g.collapseDown)
}

@Test
func colCEdgeAtTriggerCellCutsNextInput() {
    let g = colAGame(3, 1, Some(CollapseDef(1, 0, 1, 0, 2, 0)))
    @Assert(g.tryStep(Cell(0, 0)))
    @Assert(g.tryStep(Cell(1, 0)))
    @Assert(!g.tryStep(Cell(2, 0)))
    @Assert(g.lastReject, REJECT_WALL)
}

@Test
func colDStartCellTrigger() {
    let g = colAGame(3, 1, Some(CollapseDef(0, 0, 1, 0, 2, 0)))
    @Assert(g.tryStep(Cell(0, 0)))
    @Assert(g.collapseDown)
}

@Test
func colEIsEdgeCollapsedUndirectedAndPlain() {
    let g = colAGame(3, 2, Some(CollapseDef(1, 0, 1, 1, 2, 1)))
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(g.isEdgeCollapsed(2, 1, 1, 1))
    @Assert(!g.isEdgeCollapsed(0, 0, 0, 1))
    let g2 = PatrolGame(mkLevel(3, 2, [(1, 0, 0)]))
    @Assert(g2.tryStep(Cell(0, 0)))
    @Assert(!g2.isEdgeCollapsed(1, 1, 2, 1))
}
