package yilu_zip_test

/* 手工小棋盘上的机制单元测试(不读 levels.json):每例一 @Test。
   坐标 x=列, y=行;机制字段在 LevelDef 构造后直接赋 public var。 */
import std.collection.ArrayList
import std.unittest.*
import std.unittest.testmacro.*
import yilu_zip.engine.*
import yilu_zip.game.*

/* 3x3 蛇形 1..9 全走 → isWin。 */
@Test
func plainSnake3x3IsWin() {
    let lv = mkLevel(3, 3, [(1, 0, 0), (2, 1, 0), (3, 2, 0),
                            (4, 2, 1), (5, 1, 1), (6, 0, 1),
                            (7, 0, 2), (8, 1, 2), (9, 2, 2)])
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0), (2, 0), (2, 1), (1, 1), (0, 1),
                        (0, 2), (1, 2), (2, 2)]))
    @Assert(g.isWin())
    @Assert(g.filled(), 9)
}

/* 拖回上一格 = 撤销最近一次输入,path 缩短 1。 */
@Test
func dragBackOneCellUndoesLastStep() {
    let lv = mkLevel(3, 3, [(1, 0, 0)])
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(g.filled(), 2)
    @Assert(g.tryStep(Cell(0, 0))) /* 拖回首格 = 撤销第 2 次输入 */
    @Assert(g.filled(), 1)
}

/* undo 到空后 undo()==false;clear 后 path 为空。 */
@Test
func undoToEmptyThenFalseAndClearEmptiesPath() {
    let lv = mkLevel(3, 3, [(1, 0, 0)])
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0), (1, 1)]))
    @Assert(g.undo())
    @Assert(g.undo())
    @Assert(g.undo())
    @Assert(g.filled(), 0)
    @Assert(!g.undo())
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    g.clear()
    @Assert(g.filled(), 0)
}

/* 首格非 1 号 → REJECT_START;无机制关 hasMechanics()==false。 */
@Test
func rejectStartWhenFirstCellNotNumber1() {
    let lv = mkLevel(3, 3, [(1, 0, 0)])
    let g = PatrolGame(lv)
    @Assert(!g.tryStep(Cell(1, 0)))
    @Assert(g.lastReject, REJECT_START)
    @Assert(!lv.hasMechanics())
}

/* 墙边:被拒 REJECT_WALL,且 lastReject 边两端 = 该墙两端。 */
@Test
func wallEdgeRejectsWithBothEnds() {
    let lv = mkLevel(3, 1, [(1, 0, 0)])
    lv.walls.add(Wall(0, 0, 1, 0))
    let g = PatrolGame(lv)
    @Assert(g.tryStep(Cell(0, 0)))
    @Assert(!g.tryStep(Cell(1, 0)))
    @Assert(g.lastReject, REJECT_WALL)
    @Assert(g.lastRejectFromX, 0)
    @Assert(g.lastRejectFromY, 0)
    @Assert(g.lastRejectToX, 1)
    @Assert(g.lastRejectToY, 0)
}

/* 奇偶:requireOdd 在 filled 为偶时拒(lastRejectParity==1);requireEven 反之 ==2。 */
@Test
func parityRequireOddRejectsOnEvenFilled() {
    let lv = mkLevel(3, 1, [(1, 0, 0), (2, 1, 0), (3, 2, 0)])
    lv.parityEdges.add(ParityEdge(0, 0, 1, 0, true, false)) /* 踩 (1,0) 时 filled=1 奇,放行 */
    lv.parityEdges.add(ParityEdge(1, 0, 2, 0, true, false)) /* 踩 (2,0) 时 filled=2 偶,拒绝 */
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0)]))
    @Assert(!g.tryStep(Cell(2, 0)))
    @Assert(g.lastReject, REJECT_PARITY)
    @Assert(g.lastRejectParity, 1)
    @Assert(g.filled(), 2)
}

@Test
func parityRequireEvenRejectsOnOddFilled() {
    let lv = mkLevel(3, 1, [(1, 0, 0), (2, 1, 0)])
    lv.parityEdges.add(ParityEdge(0, 0, 1, 0, false, true)) /* 踩 (1,0) 时 filled=1 奇,拒绝 */
    let g = PatrolGame(lv)
    @Assert(g.tryStep(Cell(0, 0)))
    @Assert(!g.tryStep(Cell(1, 0)))
    @Assert(g.lastReject, REJECT_PARITY)
    @Assert(g.lastRejectParity, 2)
}

/* one_way:3x2,单向 (0,1)→(1,1)。正向走成功;反向走被拒(B 格未访问)。 */
@Test
func oneWayForwardAllowed() {
    let lv = mkLevel(3, 2, [(1, 0, 0)])
    lv.oneWays.add(OneWay(0, 1, 1, 1))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (0, 1), (1, 1)]))
    @Assert(g.lastReject, REJECT_NONE)
}

/* 反向:走到 (1,1) 后退回 (0,1),(0,1) 尚未访问 → REJECT_ONE_WAY。 */
@Test
func oneWayReverseRejected() {
    let lv = mkLevel(3, 2, [(1, 0, 0)])
    lv.oneWays.add(OneWay(0, 1, 1, 1))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0), (1, 1)])) /* 经上方走到 (1,1) */
    @Assert(!g.tryStep(Cell(0, 1))) /* 反向过单向边,(0,1) 未访问 */
    @Assert(g.lastReject, REJECT_ONE_WAY)
    @Assert(g.filled(), 3)
}

/* 撤销不受单向约束:正向过 (0,1)→(1,1) 后 undo() 成功,再走一次仍成功。 */
@Test
func oneWayUndoNotConstrained() {
    let lv = mkLevel(3, 2, [(1, 0, 0)])
    lv.oneWays.add(OneWay(0, 1, 1, 1))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (0, 1), (1, 1)]))
    @Assert(g.undo()) /* 撤销 (1,1),回到 (0,1) —— 撤销不查单向 */
    @Assert(g.filled(), 2)
    @Assert(g.tryStep(Cell(1, 1))) /* 再次正向过闸仍成功 */
    @Assert(g.filled(), 3)
}

/* burden 4x2:S(0,0) L(1,0) F(2,0) / (0,1)(1,1) U(2,1)(3,1)。
   未负重时可进 F(绕下方,不经 L)。 */
@Test
func burdenForbiddenAllowedWhenNotLaden() {
    let lv = mkLevel(4, 2, [(1, 0, 0)])
    let forbidden = ArrayList<Cell>()
    forbidden.add(Cell(2, 0))
    lv.burden = Some(BurdenDef(forbidden, 1, 0, 2, 1, false))
    let g = PatrolGame(lv)
    @Assert(!g.laden)
    @Assert(stepAll(g, [(0, 0), (0, 1), (1, 1), (2, 1), (2, 0)]))
}

/* 装粮后 laden → 进 F 拒;卸粮后 → 进 F 成功。 */
@Test
func burdenForbiddenRejectedWhenLadenThenAllowedAfterUnload() {
    let lv = mkLevel(4, 2, [(1, 0, 0)])
    let forbidden = ArrayList<Cell>()
    forbidden.add(Cell(2, 0))
    lv.burden = Some(BurdenDef(forbidden, 1, 0, 2, 1, false))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0)])) /* 踩 L → laden */
    @Assert(g.laden)
    @Assert(!g.tryStep(Cell(2, 0))) /* 负重进禁区 */
    @Assert(g.lastReject, REJECT_BURDEN_FORBIDDEN)
    @Assert(stepAll(g, [(1, 1), (2, 1)])) /* 绕到 U 卸粮 */
    @Assert(!g.laden)
    @Assert(g.tryStep(Cell(2, 0))) /* 空载进 F */
    @Assert(g.filled(), 5)
}

/* start_laden=true:构造后即 laden,clear()/reset 后仍是 true。 */
@Test
func burdenStartLadenStickyAcrossClearAndReset() {
    let lv = mkLevel(2, 1, [(1, 0, 0)])
    let forbidden = ArrayList<Cell>()
    forbidden.add(Cell(1, 0))
    lv.burden = Some(BurdenDef(forbidden, 0, 0, 1, 0, true))
    let g = PatrolGame(lv)
    @Assert(g.laden)
    g.clear()
    @Assert(g.laden)
    g.reset(lv)
    @Assert(g.laden)
}

/* start_laden 且起点在禁区:首格 tryStep 被拒 REJECT_BURDEN_FORBIDDEN。 */
@Test
func burdenStartLadenOnForbiddenCellRejected() {
    let lv = mkLevel(2, 1, [(1, 0, 0)])
    let forbidden = ArrayList<Cell>()
    forbidden.add(Cell(0, 0))
    lv.burden = Some(BurdenDef(forbidden, 1, 0, 1, 0, true))
    let g = PatrolGame(lv)
    @Assert(g.laden)
    @Assert(!g.tryStep(Cell(0, 0)))
    @Assert(g.lastReject, REJECT_BURDEN_FORBIDDEN)
}

/* 撤销越过装/卸粮点 → laden 按快照还原(false / true)。 */
@Test
func burdenUndoRestoresLadenFromSnapshot() {
    let lv = mkLevel(4, 2, [(1, 0, 0)])
    let forbidden = ArrayList<Cell>()
    forbidden.add(Cell(2, 0))
    lv.burden = Some(BurdenDef(forbidden, 1, 0, 2, 1, false))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0), (1, 1), (2, 1)])) /* L 装、U 卸 */
    @Assert(!g.laden)
    @Assert(g.undo()) /* 越过 U → 还原为装粮态 */
    @Assert(g.laden)
    @Assert(g.undo())
    @Assert(g.undo()) /* 越过 L → 还原为空载 */
    @Assert(!g.laden)
    @Assert(g.filled(), 1)
}

/* seal 3x2:S(0,0) A(1,0) B(2,0) / T(0,1) C(1,1) D(2,1);
   闸边 C-D,符格 T。未取符过闸 → REJECT_SEALED_GATE。 */
@Test
func sealGateRejectsWithoutToken() {
    let lv = mkLevel(3, 2, [(1, 0, 0)])
    lv.sealGates.add(SealGate(1, 1, 2, 1))
    lv.tokenCells.add(Cell(0, 1))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0), (1, 1)]))
    @Assert(!g.hasToken)
    @Assert(!g.tryStep(Cell(2, 1)))
    @Assert(g.lastReject, REJECT_SEALED_GATE)
}

/* 取符后下一次输入起可过闸;撤销越过取符步 → hasToken 复位,再过闸被拒。 */
@Test
func sealGateOpensAfterTokenAndUndoReseals() {
    let lv = mkLevel(3, 2, [(1, 0, 0)])
    lv.sealGates.add(SealGate(1, 1, 2, 1))
    lv.tokenCells.add(Cell(0, 1))
    let g = PatrolGame(lv)
    @Assert(g.tryStep(Cell(0, 0)))
    @Assert(g.tryStep(Cell(0, 1))) /* 踩上符格的这次输入之后 */
    @Assert(g.hasToken)
    @Assert(g.tryStep(Cell(1, 1)))
    @Assert(g.tryStep(Cell(2, 1))) /* 有符,过闸成功 */
    @Assert(g.filled(), 4)
    @Assert(g.undo()) /* 逐格撤回,越过取符步后 hasToken 复位 */
    @Assert(g.undo())
    @Assert(g.undo())
    @Assert(!g.hasToken)
    @Assert(g.filled(), 1)
    @Assert(stepAll(g, [(1, 0), (1, 1)])) /* 重新走到闸前 */
    @Assert(!g.tryStep(Cell(2, 1))) /* 无符再过闸 → 拒 */
    @Assert(g.lastReject, REJECT_SEALED_GATE)
}

/* 起点即符格:构造后第一次 tryStep 落在起点 → hasToken==true。 */
@Test
func tokenAtStartCellAfterFirstStep() {
    let lv = mkLevel(2, 1, [(1, 0, 0)])
    lv.tokenCells.add(Cell(0, 0))
    let g = PatrolGame(lv)
    @Assert(!g.hasToken)
    @Assert(g.tryStep(Cell(0, 0)))
    @Assert(g.hasToken)
}

/* 撤销单元基础:N 次成功输入 → 恰 N 次 undo()==true,之后 false。 */
@Test
func undoUnitCountMatchesSuccessfulSteps() {
    let lv = mkLevel(4, 1, [(1, 0, 0), (2, 1, 0), (3, 2, 0), (4, 3, 0)])
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0), (2, 0), (3, 0)]))
    @Assert(g.filled(), 4)
    @Assert(g.undo())
    @Assert(g.undo())
    @Assert(g.undo())
    @Assert(g.undo())
    @Assert(g.filled(), 0)
    @Assert(!g.undo())
}

/* 占位: ferry 尚未实现(2b/2c)。带 ferry 的关按普通关走不崩溃即过;
   2b 实现 ferry 展开后须替换本例为真实渡口断言。 */
@Test
func todo_2b_ferry_not_implemented_yet() {
    let lv = mkLevel(3, 1, [(1, 0, 0), (2, 1, 0), (3, 2, 0)])
    lv.ferry = Some(FerryDef(0, 0, 2, 0)) /* 占位数据,当前被引擎忽略 */
    let g = PatrolGame(lv)
    @Assert(lv.hasMechanics())
    @Assert(g.tryStep(Cell(0, 0))) /* 普通走法仍可进行,不崩溃 */
    @Assert(g.tryStep(Cell(1, 0)))
}
