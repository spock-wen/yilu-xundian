package yilu_zip_test

/* 渡口机制单元测试(不读 levels.json):进甲一次输入推 [甲,乙]。
   坐标 x=列, y=行;lv.ferry 在 LevelDef 构造后直接赋 Some(FerryDef(...))。
   每例独立小棋盘,断言 path 尺寸/末格、lastReject*、undo/拖回与机制快照。 */
import std.collection.ArrayList
import std.unittest.*
import std.unittest.testmacro.*
import yilu_zip.engine.*
import yilu_zip.game.*

/* a) 进甲强制跳接:一次输入推 甲、乙 两格,path 末两格依次是甲乙,filled+2。 */
@Test
func ferryJumpPushesJiaAndYiInOneInput() {
    let lv = mkLevel(3, 1, [(1, 0, 0), (2, 1, 0), (3, 2, 0)])
    lv.ferry = Some(FerryDef(1, 0, 2, 0))
    let g = PatrolGame(lv)
    @Assert(g.tryStep(Cell(0, 0)))
    @Assert(g.filled(), 1)
    @Assert(g.tryStep(Cell(1, 0))) /* 踏甲 → 同时铺乙 */
    @Assert(g.filled(), 3) /* +2 */
    @Assert(g.path.size(), 3)
    @Assert(g.path.at(1).x, 1)
    @Assert(g.path.at(1).y, 0) /* 末两格前一格 = 甲 */
    @Assert(g.path.at(2).x, 2)
    @Assert(g.path.at(2).y, 0) /* 末格 = 乙(落点) */
}

/* b) 乙已先被访问:再进甲 → false,REJECT_FERRY,端点 from=当前头 to=甲,path 不变。 */
@Test
func ferryRejectWhenYiAlreadyVisited() {
    let lv = mkLevel(3, 2, [(1, 0, 0)])
    lv.ferry = Some(FerryDef(1, 0, 1, 1))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (0, 1), (1, 1)])) /* 从别处走进乙 */
    @Assert(g.path.size(), 3)
    @Assert(!g.tryStep(Cell(1, 0))) /* 再进甲 */
    @Assert(g.lastReject, REJECT_FERRY)
    @Assert(g.lastRejectFromX, 1)
    @Assert(g.lastRejectFromY, 1) /* 当前头 = 乙 */
    @Assert(g.lastRejectToX, 1)
    @Assert(g.lastRejectToY, 0) /* to = 甲 */
    @Assert(g.path.size(), 3) /* path 不变 */
    @Assert(g.path.at(2).x, 1)
    @Assert(g.path.at(2).y, 1)
}

/* c) 玩家不经甲直接走进乙:允许(乙已访是进甲时才拒的条件)。 */
@Test
func walkIntoYiWithoutJiaAllowed() {
    let lv = mkLevel(3, 2, [(1, 0, 0)])
    lv.ferry = Some(FerryDef(1, 0, 1, 1))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (0, 1), (1, 1)])) /* 直接走进乙 */
    @Assert(g.filled(), 3)
    @Assert(g.lastReject, REJECT_NONE)
    @Assert(!g.path.contains(Cell(1, 0))) /* 甲 从未进入 */
}

/* d) 跳接豁免:甲乙之间有墙 → 仍成功;甲乙之间单向且方向为乙→甲(跳接方向相反) → 仍成功。 */
@Test
func ferryJumpIgnoresWallAndReverseOneWayBetweenJiaYi() {
    let lv1 = mkLevel(3, 1, [(1, 0, 0), (2, 1, 0), (3, 2, 0)])
    lv1.ferry = Some(FerryDef(1, 0, 2, 0))
    lv1.walls.add(Wall(1, 0, 2, 0)) /* 甲|乙 之间有墙 */
    let g1 = PatrolGame(lv1)
    @Assert(stepAll(g1, [(0, 0)]))
    @Assert(g1.tryStep(Cell(1, 0))) /* 跳接穿墙 */
    @Assert(g1.filled(), 3)
    let lv2 = mkLevel(3, 1, [(1, 0, 0), (2, 1, 0), (3, 2, 0)])
    lv2.ferry = Some(FerryDef(1, 0, 2, 0))
    lv2.oneWays.add(OneWay(2, 0, 1, 0)) /* 只放行 乙→甲,跳接是 甲→乙 */
    let g2 = PatrolGame(lv2)
    @Assert(stepAll(g2, [(0, 0)]))
    @Assert(g2.tryStep(Cell(1, 0))) /* 跳接豁免甲乙间的单向 */
    @Assert(g2.filled(), 3)
    @Assert(g2.lastReject, REJECT_NONE)
}

/* e) 进甲那条边(头→甲)仍受单向约束:反向 → REJECT_ONE_WAY,to=甲,path 不变。 */
@Test
func ferryEntryEdgeReverseOneWayRejected() {
    let lv = mkLevel(3, 1, [(1, 0, 0)])
    lv.ferry = Some(FerryDef(1, 0, 2, 0))
    lv.oneWays.add(OneWay(1, 0, 0, 0)) /* 只放行 甲→头,进甲是反向 */
    let g = PatrolGame(lv)
    @Assert(g.tryStep(Cell(0, 0)))
    @Assert(!g.tryStep(Cell(1, 0)))
    @Assert(g.lastReject, REJECT_ONE_WAY)
    @Assert(g.lastRejectFromX, 0)
    @Assert(g.lastRejectFromY, 0)
    @Assert(g.lastRejectToX, 1)
    @Assert(g.lastRejectToY, 0) /* to = 甲 */
    @Assert(g.filled(), 1) /* path 不变 */
}

/* f) 奇偶:乙的后继边按 filled=N+2 判(跳接后含两格):requireOdd 在 N=4 拒(=1),
   requireEven 放行;N=3 时 requireEven 拒(=2)。进甲那条边按跨边前 filled 判。 */
@Test
func ferryParityJudgedWithBothCellsFilled() {
    /* 后继边 (3,0)→(4,0):跳接后 filled=4 偶,requireOdd → 拒 parity=1。 */
    let lv1 = mkLevel(5, 1, [(1, 0, 0), (2, 1, 0), (3, 2, 0), (4, 3, 0), (5, 4, 0)])
    lv1.ferry = Some(FerryDef(2, 0, 3, 0))
    lv1.parityEdges.add(ParityEdge(3, 0, 4, 0, true, false))
    let g1 = PatrolGame(lv1)
    @Assert(stepAll(g1, [(0, 0), (1, 0), (2, 0)])) /* 跳接 → filled=4,头在乙 */
    @Assert(g1.filled(), 4)
    @Assert(!g1.tryStep(Cell(4, 0)))
    @Assert(g1.lastReject, REJECT_PARITY)
    @Assert(g1.lastRejectParity, 1)
    @Assert(g1.filled(), 4)
    /* 同一条边改 requireEven:filled=4 偶 → 放行。 */
    let lv2 = mkLevel(5, 1, [(1, 0, 0), (2, 1, 0), (3, 2, 0), (4, 3, 0), (5, 4, 0)])
    lv2.ferry = Some(FerryDef(2, 0, 3, 0))
    lv2.parityEdges.add(ParityEdge(3, 0, 4, 0, false, true))
    let g2 = PatrolGame(lv2)
    @Assert(stepAll(g2, [(0, 0), (1, 0), (2, 0)]))
    @Assert(g2.tryStep(Cell(4, 0))) /* filled=4 偶,requireEven 放行 */
    @Assert(g2.filled(), 5)
    /* 跳接后 filled=3 奇:后继边 requireEven → 拒 parity=2。 */
    let lv3 = mkLevel(4, 1, [(1, 0, 0), (2, 1, 0), (3, 2, 0), (4, 3, 0)])
    lv3.ferry = Some(FerryDef(1, 0, 2, 0))
    lv3.parityEdges.add(ParityEdge(2, 0, 3, 0, false, true))
    let g3 = PatrolGame(lv3)
    @Assert(stepAll(g3, [(0, 0), (1, 0)])) /* 跳接 → filled=3 */
    @Assert(!g3.tryStep(Cell(3, 0)))
    @Assert(g3.lastReject, REJECT_PARITY)
    @Assert(g3.lastRejectParity, 2)
    /* 进甲那条边 (0,0)→(1,0):跨边前 filled=1 奇,requireEven → 拒;requireOdd → 放行。 */
    let lv4 = mkLevel(3, 1, [(1, 0, 0), (2, 1, 0), (3, 2, 0)])
    lv4.ferry = Some(FerryDef(1, 0, 2, 0))
    lv4.parityEdges.add(ParityEdge(0, 0, 1, 0, false, true))
    let g4 = PatrolGame(lv4)
    @Assert(g4.tryStep(Cell(0, 0)))
    @Assert(!g4.tryStep(Cell(1, 0))) /* 进甲仍查奇偶 */
    @Assert(g4.lastReject, REJECT_PARITY)
    @Assert(g4.lastRejectParity, 2)
    @Assert(g4.filled(), 1)
    let lv5 = mkLevel(3, 1, [(1, 0, 0), (2, 1, 0), (3, 2, 0)])
    lv5.ferry = Some(FerryDef(1, 0, 2, 0))
    lv5.parityEdges.add(ParityEdge(0, 0, 1, 0, true, false))
    let g5 = PatrolGame(lv5)
    @Assert(stepAll(g5, [(0, 0), (1, 0)])) /* filled=1 奇,requireOdd 放行 */
    @Assert(g5.filled(), 3)
}

/* g) 撤销:undo() 一次移除两格,头回到进甲前;hasToken/laden 按单元快照还原。 */
@Test
func ferryUndoRemovesBothCellsAndRestoresSnapshot() {
    /* 乙是符格:跳接后 hasToken=true,undo 后 false。 */
    let lv1 = mkLevel(3, 1, [(1, 0, 0), (2, 1, 0), (3, 2, 0)])
    lv1.ferry = Some(FerryDef(1, 0, 2, 0))
    lv1.tokenCells.add(Cell(2, 0))
    let g1 = PatrolGame(lv1)
    @Assert(stepAll(g1, [(0, 0), (1, 0)]))
    @Assert(g1.hasToken) /* 跳接段含乙 → 取符 */
    @Assert(g1.filled(), 3)
    @Assert(g1.undo()) /* 一次撤销整个跳接单元 */
    @Assert(g1.filled(), 1)
    @Assert(g1.path.at(0).x, 0)
    @Assert(g1.path.at(0).y, 0) /* 头回到进甲前 */
    @Assert(!g1.hasToken)
    /* 乙是装粮点:跳接后 laden=true,undo 后恢复快照 false。 */
    let lv2 = mkLevel(3, 1, [(1, 0, 0), (2, 1, 0), (3, 2, 0)])
    lv2.ferry = Some(FerryDef(1, 0, 2, 0))
    let forbidden = ArrayList<Cell>()
    lv2.burden = Some(BurdenDef(forbidden, 2, 0, 0, 0, false)) /* load=乙(2,0) */
    let g2 = PatrolGame(lv2)
    @Assert(!g2.laden)
    @Assert(stepAll(g2, [(0, 0), (1, 0)]))
    @Assert(g2.laden) /* 段内踩装粮点 */
    @Assert(g2.undo())
    @Assert(!g2.laden) /* 快照还原 */
    @Assert(g2.filled(), 1)
}

/* h) 拖回:拖进甲前的头格 / 甲 本身 → 撤销整个跳接单元;拖乙(头) → 已访拒绝;
   普通 1 格单元的拖回仍只撤 1 格。 */
@Test
func ferryDragBackRewindsWholeUnit() {
    let lv = mkLevel(4, 1, [(1, 0, 0), (2, 1, 0), (3, 2, 0), (4, 3, 0)])
    lv.ferry = Some(FerryDef(1, 0, 2, 0))
    let g = PatrolGame(lv)
    @Assert(stepAll(g, [(0, 0), (1, 0)])) /* 跳接 → filled=3 */
    @Assert(g.filled(), 3)
    /* 拖乙(当前头)→ 已访拒绝,path 不变。 */
    @Assert(!g.tryStep(Cell(2, 0)))
    @Assert(g.lastReject, REJECT_VISITED)
    @Assert(g.filled(), 3)
    /* 拖进甲前的头格 (0,0) → 撤销整个单元。 */
    @Assert(g.tryStep(Cell(0, 0)))
    @Assert(g.filled(), 1)
    @Assert(g.path.at(0).x, 0)
    /* 重新跳接,再拖 甲(单元内非头格) → 同样撤销整个单元。 */
    @Assert(g.tryStep(Cell(1, 0)))
    @Assert(g.filled(), 3)
    @Assert(g.tryStep(Cell(1, 0))) /* 甲 是本单元第 2 格(非头) */
    @Assert(g.filled(), 1)
    /* 重新跳接,走一格普通单元,再拖那格 → 只撤 1 格。 */
    @Assert(g.tryStep(Cell(1, 0)))
    @Assert(g.filled(), 3)
    @Assert(g.tryStep(Cell(3, 0))) /* 从乙正常走 → 1 格单元 */
    @Assert(g.filled(), 4)
    @Assert(g.tryStep(Cell(2, 0))) /* 拖回 (3,0) 的起始格 (2,0) */
    @Assert(g.filled(), 3) /* 只撤销 1 格,跳接单元仍在 */
}

/* i) burden:laden 且乙在禁区 → 进甲拒 REJECT_BURDEN_FORBIDDEN(path 不变);
   未负重时乙在禁区也允许跳接。 */
@Test
func ferryBurdenForbiddenOnYiBlocksJiaEntry() {
    let forbidden = ArrayList<Cell>()
    forbidden.add(Cell(3, 0)) /* 乙 在禁区 */
    /* 负重:进甲被拒。 */
    let lv1 = mkLevel(4, 2, [(1, 0, 0), (2, 1, 0), (3, 2, 0), (4, 3, 0)])
    lv1.ferry = Some(FerryDef(2, 0, 3, 0))
    lv1.burden = Some(BurdenDef(forbidden, 0, 1, 1, 1, true)) /* start_laden,load/unload 不在路径前段 */
    let g1 = PatrolGame(lv1)
    @Assert(g1.laden)
    @Assert(stepAll(g1, [(0, 0), (1, 0)]))
    @Assert(!g1.tryStep(Cell(2, 0))) /* 进甲,乙在禁区 */
    @Assert(g1.lastReject, REJECT_BURDEN_FORBIDDEN)
    @Assert(g1.lastRejectToX, 2)
    @Assert(g1.lastRejectToY, 0) /* to = 甲 */
    @Assert(g1.filled(), 2) /* path 不变 */
    /* 空载:同一禁区允许跳接。 */
    let lv2 = mkLevel(4, 2, [(1, 0, 0), (2, 1, 0), (3, 2, 0), (4, 3, 0)])
    lv2.ferry = Some(FerryDef(2, 0, 3, 0))
    lv2.burden = Some(BurdenDef(forbidden, 0, 1, 1, 1, false)) /* start 空载 */
    let g2 = PatrolGame(lv2)
    @Assert(!g2.laden)
    @Assert(stepAll(g2, [(0, 0), (1, 0)]))
    @Assert(g2.tryStep(Cell(2, 0))) /* 空载跳进禁区乙 */
    @Assert(g2.filled(), 4)
    @Assert(!g2.laden)
}

/* j) 一次输入进甲后头在乙:后续邻格以乙为头查(甲的邻格被拒);
   含一次跳接走满 4x2 全盘 → 路标 1..8 按序、n 在最后一格,isWin()。 */
@Test
func ferryHeadMovesOnFromYiAndFullBoardWins() {
    let lv = mkLevel(4, 2, [(1, 0, 0), (2, 1, 0), (3, 2, 0), (4, 3, 0),
                            (5, 3, 1), (6, 2, 1), (7, 1, 1), (8, 0, 1)])
    lv.ferry = Some(FerryDef(1, 0, 2, 0))
    let g = PatrolGame(lv)
    @Assert(g.tryStep(Cell(0, 0)))
    @Assert(g.tryStep(Cell(1, 0))) /* 跳接 → 头在乙(2,0) */
    @Assert(g.filled(), 3)
    @Assert(g.path.at(2).x, 2)
    @Assert(g.path.at(2).y, 0)
    /* (1,1) 只邻甲不邻乙(头) → 以乙为头查邻格,拒。 */
    @Assert(!g.tryStep(Cell(1, 1)))
    @Assert(g.lastReject, REJECT_WALL)
    @Assert(g.filled(), 3) /* path 不变 */
    /* 从乙继续正常走,填满全盘。 */
    @Assert(stepAll(g, [(3, 0), (3, 1), (2, 1), (1, 1), (0, 1)]))
    @Assert(g.filled(), 8)
    @Assert(g.path.size(), 8)
    @Assert(g.isWin())
    @Assert(g.numberAt(g.path.at(7).x, g.path.at(7).y), 8) /* n 在最后一格 */
}
