package ohos_app_cangjie_entry

internal import cjmp.net.connection.*
internal import ohos.base.LengthProp
internal import ohos.arkui.component.*
internal import ohos.arkui.state_management.SubscriberManager
internal import ohos.arkui.state_management.ObservedProperty
internal import ohos.arkui.state_management.LocalStorage
import ohos.arkui.state_macro_manage.Entry
import ohos.arkui.state_macro_manage.Component
import ohos.arkui.state_macro_manage.State
import ohos.arkui.state_macro_manage.Builder
import ohos_app_cangjie_entry.logic.logicTest
import ohos.arkui.component.circle.*
import ohos.arkui.component.rect.*
import ohos.arkui.component.line.*
import ohos.arkui.component.path.*
import ohos.arkui.component.stack.*
import ohos.arkui.component.common.*
import ohos.base.*
import ohos.arkui.component.list.*
import ohos.arkui.component.list_item.*
import ohos.arkui.component.for_each.*
import ohos.arkui.component.scroll.*
import std.collection.ArrayList
import ohos_app_cangjie_entry.engine.*
import ohos_app_cangjie_entry.game.*
import std.time.MonoTime

@Entry
@Component
class EntryView {
    var levels: ArrayList<LevelDef> = LevelCatalog.load()
    var game: PatrolGame = PatrolGame(if (this.levels.size > 0) { this.levels[0] } else { blankLevel() })

    @State var screen: Int64 = 0
    @State var levelIndex: Int64 = 0
    @State var chapterIndex: Int64 = 0
    @State var boardBack: Int64 = 0
    @State var tick: Int64 = 0
    @State var cleared: Int64 = 0
    @State var stepFilled: Int64 = 0
    // M2: parity toast
    @State var parityRejectText: String = ""
    @State var parityRejectFlash: Bool = false
    @State var parityRejectGen: Int64 = 0
    @State var rejectFromX: Int64 = 0
    @State var rejectFromY: Int64 = 0
    @State var rejectToX: Int64 = 0
    @State var rejectToY: Int64 = 0
    @State var winW: Float64 = 360.0
    // A2: back button pressed ripple opacity
    @State var backPressedOpacity: Float64 = 0.0

    // Board shape renderer state (Keels 0.2.2)
    @State var boardGen: Int64 = 0
    var lastBuildUs: Int64 = 0
    var lastAssignUs: Int64 = 0
    @State var boardCells: Array<BoardRect> = Array<BoardRect>()
    @State var boardWalls: Array<BoardSeg> = Array<BoardSeg>()
    @State var boardParityLabels: Array<BoardLabel> = Array<BoardLabel>()
    @State var boardRoute: Array<BoardSeg> = Array<BoardSeg>()
    @State var boardDots: Array<BoardDot> = Array<BoardDot>()
    @State var boardStationCircles: Array<BoardDot> = Array<BoardDot>()
    @State var boardNextLabels: Array<BoardLabel> = Array<BoardLabel>()
    @State var boardDigits: Array<BoardPath> = Array<BoardPath>()

    func homeMarkFontVp(): Float64 { return 12.0 / this.getPxFactor() }
    func homeMarkTop(baseline: Float64): Float64 { return baseline - 0.88 * this.homeMarkFontVp() }

    var fontsDone: Bool = false
    var fontHandle: Int64 = 0
    var pxFactor: Float64 = 0.0

    func serifFamily(): String {
        if (!this.fontsDone) {
            this.fontsDone = true
            this.fontHandle = registerYiluFonts()
        }
        return Theme.serif
    }

    func serifBoldFamily(): String {
        if (!this.fontsDone) {
            this.fontsDone = true
            this.fontHandle = registerYiluFonts()
        }
        return Theme.serifBold
    }

    // D-03: sans helpers — register fonts once via fontsDone flag
    func sansFamily(): String {
        if (!this.fontsDone) {
            this.fontsDone = true
            this.fontHandle = registerYiluFonts()
        }
        return Theme.sans
    }

    func sansMediumFamily(): String {
        if (!this.fontsDone) {
            this.fontsDone = true
            this.fontHandle = registerYiluFonts()
        }
        return Theme.sansMedium
    }

    // A2: back button — device-pixel path commands for the chevron icon
    func getPxFactor(): Float64 {
        if (this.pxFactor > 0.0) {
            return this.pxFactor
        }
        /* Cache device px factor once via UIContext.vp2px.
           iOS sim is 3.0 px/vp, Android is 2.625 px/vp.
           If vp2px fails at runtime, fall back to 3.0. */
        match (this.getUIContext().vp2px(1.0.vp)) {
            case Some(len) =>
                this.pxFactor = len.value
                println("UIContext.vp2px factor: ${this.pxFactor}")
            case None =>
                // Fallback factor if vp2px returns None at runtime (unlikely on Keels)
                println("UIContext.vp2px returned None, fallback factor: 3.0")
                this.pxFactor = 3.0
        }
        return this.pxFactor
    }

    func backIconCommands(): String {
        let f = this.getPxFactor()
        return "M ${27.0 * f} ${16.5 * f} L ${20.0 * f} ${24.0 * f} L ${27.0 * f} ${31.5 * f}"
    }

    // SPEC cjmp-gaps-v1 A2 (not locked yet — may change)
    @Builder func backButton(action: () -> Unit, isBoardOrWin: Bool) {
        Stack {
            // Pressed state: 40vp Circle filled Theme.paperShade centred on icon
            Circle(width: 40.0, height: 40.0)
                .fill(Theme.paperShade)
                .opacity(this.backPressedOpacity)
                .position(x: 4.0, y: 4.0)

            // Icon: 24vp box (left=12, top=12), Path commands device pixels, stroke Theme.ink width 1.5vp
            Path(width: 48.0, height: 48.0, commands: this.backIconCommands())
                .stroke(Theme.ink)
                .strokeWidth(1.5)
                .strokeLineCap(LineCapStyle.Round)
                .strokeLineJoin(LineJoinStyle.Round)
                .fillOpacity(0.0)
                .antiAlias(true)
                .position(x: 0.0, y: 0.0)
        }
        .width(48)
        .height(48)
        .margin(left: 4, top: if (isBoardOrWin) { 0 } else { 4 }, bottom: if (isBoardOrWin) { 0 } else { 4 })
        .onTouch({ evt =>
            match (evt.eventType) {
                case TouchType.Down =>
                    this.backPressedOpacity = 1.0
                case TouchType.Up | TouchType.Cancel =>
                    this.getUIContext().animateTo(
                        AnimateParam(duration: 160, curve: Curve.EaseOut),
                        { => this.backPressedOpacity = 0.0 }
                    )
                case _ => ()
            }
        })
        .onClick({ evt =>
            this.backPressedOpacity = 0.0
            action()
        })
    }

    // Android system back override (Keels CustomView page-level back)
    protected override func onBackPress(): Bool {
        if (this.screen == 0) {
            return false
        } else if (this.screen == 1 || this.screen == 2) {
            this.leaveBoard()
            return true
        } else if (this.screen == 3 || this.screen == 4) {
            this.screen = 0
            return true
        } else if (this.screen == 5 || this.screen == 6) {
            this.screen = 4
            return true
        }
        return false
    }

    func clearParityReject(): Unit {
        this.parityRejectGen = this.parityRejectGen + 1
        this.parityRejectText = ""
        this.parityRejectFlash = false
        if (PERF_LOG) { perfLog("toast clear gen=${this.parityRejectGen}") }
    }

    func showParityReject(): Unit {
        let r = this.game.lastRejectParity
        if (r == 1) {
            this.parityRejectText = "此步须奇"
        } else if (r == 2) {
            this.parityRejectText = "此步须偶"
        } else {
            return
        }
        this.parityRejectFlash = true
        let p = this.rejectPlacement()
        if (!p.shown) {
            println("TOAST_NOT_PLACED level=${this.curLevel().id} edge=(${this.rejectFromX},${this.rejectFromY})-(${this.rejectToX},${this.rejectToY})")
        }
        if (PERF_LOG) {
            perfLog("toast place step=${p.step} lift=${p.lift} x=${p.x} y=${p.y}")
        }
        this.parityRejectGen = this.parityRejectGen + 1
        let gen = this.parityRejectGen
        if (PERF_LOG) { perfLog("toast show text=${this.parityRejectText} gen=${this.parityRejectGen}") }
        /* UI-thread delayed clear: animateTo's onFinish runs on the
           UI thread, so @State writes repaint immediately.  The 180ms
           duration drives a no-op animation; onFinish clears the toast. */
        this.getUIContext().animateTo(
            AnimateParam(duration: 180, onFinish: Some({ =>
                if (PERF_LOG) { perfLog("toast onFinish gen=${gen}") }
                if (gen == this.parityRejectGen) {
                    this.clearParityReject()
                }
            })),
            { => }
        )
    }

    func curLevel(): LevelDef {
        if (this.levelIndex >= 0 && this.levelIndex < this.levels.size) {
            return this.levels[this.levelIndex]
        }
        return blankLevel()
    }

    func remainingSteps(): Int64 {
        let lim = this.curLevel().stepLimit
        if (lim <= 0) { return 0 }
        let left = lim - this.stepFilled
        if (left < 0) { return 0 }
        return left
    }

    func stepChipBorder(): Int64 {
        return Theme.paperLine
    }

    func stepLeftBorderColor(): Int64 {
        if (this.remainingSteps() <= Theme.stepWarnAt) {
            return Theme.gold
        }
        return Theme.paperLine
    }

    func stepLeftBorderW(): Int64 {
        if (this.remainingSteps() <= Theme.stepWarnAt) {
            return 2
        }
        return 1
    }

    func rejectEdgeMid(): (Float64, Float64) {
        return this.boardGeom().seamMid(this.rejectFromX, this.rejectFromY, this.rejectToX, this.rejectToY)
    }

    func rejectEdgeStartPoint(): (Float64, Float64) {
        let (midX, midY) = this.rejectEdgeMid()
        if (this.rejectFromX != this.rejectToX) {
            return (midX, midY - 12.0)
        }
        return (midX - 12.0, midY)
    }

    func rejectEdgeEndPoint(): (Float64, Float64) {
        let (midX, midY) = this.rejectEdgeMid()
        if (this.rejectFromX != this.rejectToX) {
            return (midX, midY + 12.0)
        }
        return (midX + 12.0, midY)
    }

    // U3: Collect board obstacles for toast avoidance (designer ruling)
    func collectToastObstacles(): Array<ToastBox> {
        let list = ArrayList<ToastBox>()

        // 1. Flash line: bounding box of start/end points inflated by 1.5 (3 vp stroke, round cap)
        let (sx, sy) = this.rejectEdgeStartPoint()
        let (ex, ey) = this.rejectEdgeEndPoint()
        let minX = if (sx <= ex) { sx } else { ex }
        let maxX = if (sx >= ex) { sx } else { ex }
        let minY = if (sy <= ey) { sy } else { ey }
        let maxY = if (sy >= ey) { sy } else { ey }
        list.add(ToastBox(minX - 1.5, minY - 1.5, maxX + 1.5, maxY + 1.5))

        // 2. Head dot: cx±(r+0.5), cy±(r+0.5)
        for (dot in this.boardDots) {
            let rEff = dot.r + 0.5
            list.add(ToastBox(dot.cx - rEff, dot.cy - rEff, dot.cx + rEff, dot.cy + rEff))
        }

        // 3. Station circles: cx±(r+strokeW/2) (gold ring already has a bigger r entry)
        for (circle in this.boardStationCircles) {
            let extra = if (circle.hasStroke) { circle.strokeW * 0.5 } else { 0.0 }
            let rEff = circle.r + extra
            list.add(ToastBox(circle.cx - rEff, circle.cy - rEff, circle.cx + rEff, circle.cy + rEff))
        }

        // 4. 下一驿 labels: anchored at left edge and baseline (cy+r+12)
        for (lbl in this.boardNextLabels) {
            let baseline = lbl.y + 0.88 * lbl.size
            list.add(ToastBox(lbl.x - 0.5, baseline - 10.0, lbl.x + 35.0, baseline + 3.5))
        }

        // 5. Parity labels: glyph centred on seam midpoint (mx, my)
        for (lbl in this.boardParityLabels) {
            let mx = lbl.x + 5.5
            let my = lbl.y - 4.0 + 0.88 * lbl.size
            list.add(ToastBox(mx - 6.5, my - 8.5, mx + 6.5, my + 5.0))
        }


        // 6. Walls: width/2 padding, clear = 2.0
        for (wall in this.boardWalls) {
            let hw = wall.width * 0.5
            let minX = (if (wall.x1 <= wall.x2) { wall.x1 } else { wall.x2 }) - hw
            let maxX = (if (wall.x1 >= wall.x2) { wall.x1 } else { wall.x2 }) + hw
            let minY = (if (wall.y1 <= wall.y2) { wall.y1 } else { wall.y2 }) - hw
            let maxY = (if (wall.y1 >= wall.y2) { wall.y1 } else { wall.y2 }) + hw
            list.add(ToastBox(minX, minY, maxX, maxY, 2.0))
        }

        // 7. Route: width/2 padding, clear = 2.0
        for (route in this.boardRoute) {
            let hw = route.width * 0.5
            let minX = (if (route.x1 <= route.x2) { route.x1 } else { route.x2 }) - hw
            let maxX = (if (route.x1 >= route.x2) { route.x1 } else { route.x2 }) + hw
            let minY = (if (route.y1 <= route.y2) { route.y1 } else { route.y2 }) - hw
            let maxY = (if (route.y1 >= route.y2) { route.y1 } else { route.y2 }) + hw
            list.add(ToastBox(minX, minY, maxX, maxY, 2.0))
        }

        return list.toArray()
    }

    func rejectPlacement(): ToastPlacement {
        let (midX, midY) = this.rejectEdgeMid()
        return toastPlace(Float64(this.boardW()), Float64(this.boardH()), midX, midY, this.collectToastObstacles())
    }

    func rejectToastX(): Float64 {
        return this.rejectPlacement().x
    }

    func rejectToastY(): Float64 {
        return this.rejectPlacement().y
    }

    func hasParityBoard(): Bool {
        return this.curLevel().parityEdges.size > 0
    }

    func stepChipLabel(): String {
        return "第 ${this.stepFilled} 步"
    }

    func boardGeom(): BoardGeom {
        return boardGeomFor(this.curLevel().cols, this.curLevel().rows, this.winW)
    }

    func cellVp(): Int64 {
        return Int64(this.boardGeom().c)
    }

    func boardW(): Int64 {
        return Int64(this.boardGeom().trayW())
    }

    func boardH(): Int64 {
        return Int64(this.boardGeom().trayH())
    }

    func currentLayout(): GridLayout {
        return GridLayout(0.0, 0.0, this.boardGeom().c, this.curLevel().cols, this.curLevel().rows)
    }

    func roadTitle(): String {
        return this.curLevel().name
    }

    func currentName(): String {
        if (this.cleared >= this.levels.size) {
            return "已通"
        }
        return this.levels[this.cleared].name
    }

    func stationState(n: Int64): Int64 {
        return stationStateOf(this.game, n)
    }

    func rebuildBoard(): Unit {
        this.boardGen = this.boardGen + 1
        let geom = this.boardGeom()
        let factor = this.getPxFactor()

        let tBuild0 = MonoTime.now()
        let tmpCells = buildBoardCells(this.game, geom)
        let tmpWalls = buildBoardWalls(this.game, geom)
        let tmpParityLabels = buildBoardParityLabels(this.game, geom, factor)
        let tmpRoute = buildBoardRoute(this.game, geom)
        let tmpDots = buildBoardHeadDot(this.game, geom)
        let tmpStationCircles = buildBoardStationCircles(this.game, geom)
        let tmpNextLabels = buildBoardNextLabels(this.game, geom, factor)
        let tmpDigits = buildBoardDigits(this.game, geom, factor)
        this.lastBuildUs = (MonoTime.now() - tBuild0).toMicroseconds()

        let tAssign0 = MonoTime.now()
        this.boardCells = tmpCells
        this.boardWalls = tmpWalls
        this.boardParityLabels = tmpParityLabels
        this.boardRoute = tmpRoute
        this.boardDots = tmpDots
        this.boardStationCircles = tmpStationCircles
        this.boardNextLabels = tmpNextLabels
        this.boardDigits = tmpDigits
        this.lastAssignUs = (MonoTime.now() - tAssign0).toMicroseconds()
    }

    func refresh(): Unit {
        this.tick = this.tick + 1
        this.stepFilled = this.game.filled()
        this.rebuildBoard()
    }

    protected override func aboutToAppear(): Unit {
        this.rebuildBoard()
    }


    func openLevel(index: Int64): Unit {
        this.levelIndex = index
        this.chapterIndex = ChapterCatalog.chapterIdForLevel(index)
        if (index >= 0 && index < this.levels.size) {
            this.game.reset(this.levels[index])
        }
        this.screen = 1
        this.refresh()
        if (PERF_LOG) {
            perfLog("open lvl=${index} build_us=${this.lastBuildUs} assign_us=${this.lastAssignUs}")
        }
    }

    func startPlay(): Unit {
        this.boardBack = 0
        if (this.levels.size == 0) {
            return
        }
        if (this.cleared >= this.levels.size) {
            this.openLevel(this.levels.size - 1)
            return
        }
        this.openLevel(this.cleared)
    }

    func openFromList(index: Int64): Unit {
        if (index > this.cleared) {
            return
        }
        if (this.screen == 5) {
            this.boardBack = 5
        } else if (this.screen == 3) {
            this.boardBack = 3
        } else {
            this.boardBack = 0
        }
        this.openLevel(index)
    }

    func chapterOpen(id: Int64): Bool {
        return ChapterCatalog.isOpen(id, this.cleared)
    }

    func openChapter(id: Int64): Unit {
        if (!ChapterCatalog.isOpen(id, this.cleared)) {
            if (ChapterCatalog.hasSkinPreview(id)) {
                this.chapterIndex = id
                this.screen = 6
            }
            return
        }
        this.chapterIndex = id
        this.screen = 5
    }

    func currentChapter(): ChapterDef {
        return ChapterCatalog.byIndex(this.chapterIndex)
    }

    func playPaper(): Int64 {
        if (this.screen == 6) {
            return Theme.paperOf(this.chapterIndex)
        }
        if (this.screen == 1 || this.screen == 2) {
            return Theme.paperOf(this.chapterIndex)
        }
        return Theme.paper
    }

    /* BANDS.md: band is full-bleed at x=0. Skin preview is also full-bleed.
       Other screens keep Theme.inset. */
    func playInset(): Int64 {
        if (this.screen == 1 || this.screen == 6) {
            return 0
        }
        return Theme.inset
    }

    func chromeLine(): String {
        let ch = this.currentChapter()
        return "友：${ch.friendLine} · 张力：${ch.tensionLine} · 城：${ch.cityLine}"
    }

    func boardSubtitle(): String {
        return this.currentChapter().boardSubtitle
    }

    func chapterListTitle(): String {
        return "${this.currentChapter().name}·驿程"
    }

    func chapterCurrentName(): String {
        let ch = this.currentChapter()
        if (!ChapterCatalog.isOpen(ch.id, this.cleared)) {
            return "未开"
        }
        if (this.cleared >= ch.levelStart + ch.levelCount) {
            return "已通"
        }
        if (this.cleared < ch.levelStart) {
            if (ch.levelStart < this.levels.size) {
                return this.levels[ch.levelStart].name
            }
            return ""
        }
        if (this.cleared < this.levels.size) {
            return this.levels[this.cleared].name
        }
        return ""
    }

    func chapterListFooter(): String {
        let ch = this.currentChapter()
        let n = ChapterCatalog.clearedCount(this.chapterIndex, this.cleared)
        /* 本章尺寸取自 LevelCatalog 首驿（ch1–3 6×6，ch4–10 7×7）。 */
        if (ch.levelStart < this.levels.size) {
            let board = this.levels[ch.levelStart]
            return "已通 ${n} · 当前${this.chapterCurrentName()} · 共10驿 · ${board.cols}×${board.rows}"
        }
        return "已通 ${n} · 当前${this.chapterCurrentName()} · 共10驿"
    }

    func chapterOpenFooter(): String {
        let opened = ChapterCatalog.openCount(this.cleared)
        let locked = ChapterCatalog.count() - opened
        return "已开 ${opened} · 未启 ${locked} · 点开章入驿程"
    }

    func leaveBoard(): Unit {
        this.clearParityReject()
        this.screen = this.boardBack
    }

    func cardTitleColor(open: Bool): Int64 {
        if (open) {
            return Theme.ink
        }
        return Theme.locked
    }

    func cardMutedColor(open: Bool): Int64 {
        if (open) {
            return Theme.inkMuted
        }
        return Theme.locked
    }

    func enterFill(index: Int64): Int64 {
        if (index == 0) {
            return Theme.qingDeep
        }
        return Theme.whitePaper
    }

    func enterInk(index: Int64): Int64 {
        if (index == 0) {
            return Theme.whitePaper
        }
        return Theme.ink
    }

    func cardBorder(open: Bool): Int64 {
        if (open) {
            return Theme.paperLine
        }
        return Theme.locked
    }

    func nextLevel(): Unit {
        let nxt = this.levelIndex + 1
        if (nxt >= this.levels.size) {
            this.screen = 0
            return
        }
        this.openLevel(nxt)
    }

    func doUndo(): Unit {
        this.clearParityReject()
        if (this.game.undo()) {
            this.refresh()
        }
    }

    func doClear(): Unit {
        this.clearParityReject()
        this.game.clear()
        this.refresh()
    }

    func handleDrag(event: TouchEvent, isDown: Bool): Unit {
        /* Win sets screen=2 then refresh(); a trailing Move can still
           hit the Canvas and drag-back-undo the last cell. */
        if (this.screen != 1) {
            return
        }
        if (event.touches.size == 0) {
            return
        }
        let px = event.touches[0].x
        let py = event.touches[0].y
        let hit = this.boardGeom().hitTest(px, py)
        match (hit) {
            case None => ()
            case Some(cell) =>
                let t0 = MonoTime.now()
                var ok = 0
                if (this.game.tryStep(cell)) {
                    ok = 1
                    this.clearParityReject()
                    if (this.game.isWin()) {
                        if (this.levelIndex + 1 > this.cleared) {
                            this.cleared = this.levelIndex + 1
                        }
                        this.screen = 2
                        if (PERF_LOG) {
                            perfLog("win lvl=${this.levelIndex}")
                        }
                    }
                    this.refresh()
                } else {
                    if (this.game.lastRejectParity != 0) {
                        if (this.game.path.size() > 0) {
                            let lastCell = this.game.path.at(this.game.path.size() - 1)
                            this.rejectFromX = lastCell.x
                            this.rejectFromY = lastCell.y
                            this.rejectToX = cell.x
                            this.rejectToY = cell.y
                        }
                        this.showParityReject()
                        this.refresh()
                    }
                }
                if (PERF_LOG) {
                    let evStr = if (isDown) { "down" } else { "move" }
                    let us = (MonoTime.now() - t0).toMicroseconds()
                    perfLog("touch ev=${evStr} lvl=${this.levelIndex} ok=${ok} filled=${this.game.filled()} handler_us=${us} cells=${this.boardCells.size} grid=0 route=${this.boardRoute.size} digits=${this.boardDigits.size} gen=${this.boardGen} rebuild_us=${this.lastBuildUs + this.lastAssignUs} build_us=${this.lastBuildUs} assign_us=${this.lastAssignUs} tick=${this.tick}")
                }
        }
    }

    func rowBorder(index: Int64): Int64 {
        if (index == this.cleared) {
            return Theme.ink
        }
        return Theme.whitePaper
    }
    func build() {
        Column {
            if (this.screen == 0) {
                /* Home seal copy: 关防 (vermillion only). */
                Row {
                    Blank()
                    Column {
                        Text("关")
                            .fontSize(14)
                            .fontColor(Theme.whitePaper)
                            .fontFamily(this.serifFamily())
                        Text("防")
                            .fontSize(14)
                            .fontColor(Theme.whitePaper)
                            .fontFamily(this.serifFamily())
                    }
                    .width(44)
                    .height(44)
                    .backgroundColor(Theme.vermillion)
                    .justifyContent(FlexAlign.Center)
                    .alignItems(HorizontalAlign.Center)
                    .rotate(angle: 12.0)
                }
                .width(100.percent)
                .padding(top: 8, right: 4)
                Column {
                    Text("驿")
                        .fontSize(18)
                        .fontColor(Theme.ink)
                        .fontFamily(this.serifFamily())
                }
                .width(44)
                .height(44)
                .borderRadius(22)
                .border(width: 1, color: Theme.gold)
                .backgroundColor(Theme.whitePaper)
                .justifyContent(FlexAlign.Center)
                .alignItems(HorizontalAlign.Center)
                .margin(top: 12)
                Text("驿路巡点")
                    .fontSize(34)
                    .fontColor(Theme.ink)
                    .fontFamily(this.serifBoldFamily())
                    .fontWeight(FontWeight.Bold)
                    .margin(top: 8)
                // Divider not in OpenSDK 0.2.2: 1vp hairline Column, same color/width as HarmonyOS
                Column() {}.width(168).height(1).backgroundColor(Theme.gold).margin(top: 6, bottom: 8)
                Text("传书过驿")
                    .fontSize(16)
                    .lineHeight(24)
                    .fontColor(Theme.inkMuted)
                    .fontFamily(this.serifFamily())
                if (this.levels.size == 0) {
                    Text(LevelCatalog.loadError())
                        .fontSize(11)
                        .lineHeight(15)
                        .fontColor(Theme.vermillion)
                        .fontFamily(this.sansFamily())
                }
                Stack(alignContent: Alignment.TopStart) {
                    Line(width: 360, height: 140)
                        .startPoint((40.0, 24.0))
                        .endPoint((130.0, 56.0))
                        .stroke(Theme.paperLine)
                        .strokeWidth(Theme.hairline)
                    Line(width: 360, height: 140)
                        .startPoint((130.0, 56.0))
                        .endPoint((78.0, 96.0))
                        .stroke(Theme.paperLine)
                        .strokeWidth(Theme.hairline)
                    Line(width: 360, height: 140)
                        .startPoint((78.0, 96.0))
                        .endPoint((200.0, 118.0))
                        .stroke(Theme.paperLine)
                        .strokeWidth(Theme.hairline)
                    /* HarmonyOS parity: Canvas font 12px = 12 device px; top = baseline - 0.88*fontVp */
                    Text("涿郡")
                        .fontSize(this.homeMarkFontVp())
                        .fontColor(Theme.inkMuted)
                        .fontFamily(Theme.sans)
                        .position(x: 28.0, y: this.homeMarkTop(20.0))
                    Text("平原")
                        .fontSize(this.homeMarkFontVp())
                        .fontColor(Theme.inkMuted)
                        .fontFamily(Theme.sans)
                        .position(x: 126.0, y: this.homeMarkTop(52.0))
                    Text("安喜")
                        .fontSize(this.homeMarkFontVp())
                        .fontColor(Theme.inkMuted)
                        .fontFamily(Theme.sans)
                        .position(x: 64.0, y: this.homeMarkTop(108.0))
                    Text("郡治")
                        .fontSize(this.homeMarkFontVp())
                        .fontColor(Theme.inkMuted)
                        .fontFamily(Theme.sans)
                        .position(x: 190.0, y: this.homeMarkTop(124.0))
                }
                .width(100.percent)
                .height(140)
                .opacity(0.18)
                Blank()
                Button("开始传书")
                    .width(100.percent)
                    .height(Theme.primaryH)
                    .backgroundColor(Theme.qingDeep)
                    .fontColor(Theme.whitePaper)
                    .fontSize(16)
                    .fontFamily(this.sansMediumFamily())
                    .onClick({event => this.startPlay()})
                Row {
                    Text("章节")
                        .fontSize(16)
                        .fontColor(Theme.ink)
                        .fontFamily(this.sansFamily())
                }
                .width(100.percent)
                .height(44)
                .margin(top: 12)
                .justifyContent(FlexAlign.Center)
                .alignItems(VerticalAlign.Center)
                .backgroundColor(Theme.whitePaper)
                .borderRadius(8)
                .border(width: 1, color: Theme.ink)
                .onClick({event => this.screen = 4})
                Text("驿程")
                    .fontSize(16)
                    .fontColor(Theme.inkMuted)
                    .fontFamily(this.sansFamily())
                    .margin(top: 16, bottom: 12)
                    .onClick({event => this.screen = 3})
            } else if (this.screen == 3) {
                Stack {
                    Row {
                        this.backButton({ => this.screen = 0 }, false)
                        Blank()
                    }
                    .width(100.percent)
                    .height(Theme.topBar)
                    Text("驿程")
                        .fontSize(20)
                        .fontColor(Theme.ink)
                        .fontFamily(this.serifBoldFamily())
                        .fontWeight(FontWeight.Bold)
                }
                .width(100.percent)
                .height(Theme.topBar)
                // Divider not in OpenSDK 0.2.2: 1vp hairline Column, same color/width as HarmonyOS
                Column() {}.width(100.percent).height(1).backgroundColor(Theme.paperLine)
                Scroll {
                    Column(space: 10) {
                        ForEach(
                            this.levels,
                            itemGenerator: {item: LevelDef, index: Int64 =>
                                Row {
                                    if (index < this.cleared) {
                                        Text("通")
                                            .fontSize(14)
                                            .fontColor(Theme.success)
                                            .fontFamily(this.serifFamily())
                                            .width(36)
                                            .height(36)
                                            .border(width: 1, color: Theme.success)
                                            .borderRadius(18)
                                            .textAlign(TextAlign.Center)
                                        Text(item.name)
                                            .fontSize(18)
                                            .fontColor(Theme.ink)
                                            .fontFamily(this.serifBoldFamily())
                                            .fontWeight(FontWeight.Bold)
                                            .margin(left: 12)
                                        Blank()
                                        Text("已通")
                                            .fontSize(14)
                                            .fontColor(Theme.success)
                                            .fontFamily(this.sansFamily())
                                    } else if (index == this.cleared) {
                                        Text("${index + 1}")
                                            .fontSize(16)
                                            .fontColor(Theme.whitePaper)
                                            .fontFamily(this.serifFamily())
                                            .width(36)
                                            .height(36)
                                            .backgroundColor(Theme.ink)
                                            .borderRadius(18)
                                            .textAlign(TextAlign.Center)
                                        Text(item.name)
                                            .fontSize(18)
                                            .fontColor(Theme.ink)
                                            .fontFamily(this.serifBoldFamily())
                                            .fontWeight(FontWeight.Bold)
                                            .margin(left: 12)
                                        Blank()
                                        Text("当前")
                                            .fontSize(14)
                                            .fontColor(Theme.ink)
                                            .fontFamily(this.sansFamily())
                                    } else {
                                        Text("${index + 1}")
                                            .fontSize(16)
                                            .fontColor(Theme.locked)
                                            .fontFamily(this.serifFamily())
                                            .width(36)
                                            .height(36)
                                            .border(width: 1, color: Theme.locked)
                                            .borderRadius(18)
                                            .textAlign(TextAlign.Center)
                                        Text(item.name)
                                            .fontSize(18)
                                            .fontColor(Theme.locked)
                                            .fontFamily(this.serifBoldFamily())
                                            .fontWeight(FontWeight.Bold)
                                            .margin(left: 12)
                                        Blank()
                                        Text("锁")
                                            .fontSize(14)
                                            .fontColor(Theme.locked)
                                            .fontFamily(this.sansFamily())
                                    }
                                }
                                .width(100.percent)
                                .height(64)
                                .padding(left: 14, right: 14)
                                .backgroundColor(Theme.whitePaper)
                                .borderRadius(10)
                                .border(width: 1, color: this.rowBorder(index))
                                .onClick({event => this.openFromList(index)})
                            }
                        )
                    }
                    .width(100.percent)
                }
                .width(100.percent)
                .layoutWeight(1)
                Text("已通 ${this.cleared} · 当前 ${this.currentName()}")
                    .fontSize(12)
                    .fontColor(Theme.inkMuted)
                    .fontFamily(this.sansFamily())
                    .margin(top: 12, bottom: 8)
                    .width(100.percent)
            } else if (this.screen == 4) {
                Stack {
                    Row {
                        this.backButton({ => this.screen = 0 }, false)
                        Blank()
                    }
                    .width(100.percent)
                    .height(Theme.topBar)
                    Text("章节")
                        .fontSize(20)
                        .fontColor(Theme.ink)
                        .fontFamily(this.serifBoldFamily())
                        .fontWeight(FontWeight.Bold)
                }
                .width(100.percent)
                .height(Theme.topBar)
                Text("选章入驿 · 开章可入 · 灰章未启")
                    .fontSize(12)
                    .fontColor(Theme.inkMuted)
                    .fontFamily(this.sansFamily())
                    .margin(top: 2, bottom: 8)
                    .width(100.percent)
                Scroll {
                    Column(space: 8) {
                        ForEach(
                            ChapterCatalog.all(),
                            itemGenerator: {item: ChapterDef, index: Int64 =>
                                Column {
                                if (item.id == 4) {
                                    Image(rawImg("card_05_touyuan_v91"))
                                        .width(100.percent)
                                        .height(Theme.chapterSkinCardH)
                                        .objectFit(ImageFit.Contain)
                                } else if (item.id == 5) {
                                    Image(rawImg("card_06_jingzhou_v91"))
                                        .width(100.percent)
                                        .height(Theme.chapterSkinCardH)
                                        .objectFit(ImageFit.Contain)
                                } else if (item.id == 6) {
                                    Image(rawImg("card_07_chibi_v91"))
                                        .width(100.percent)
                                        .height(Theme.chapterSkinCardH)
                                        .objectFit(ImageFit.Contain)
                                } else if (item.id == 7) {
                                    Image(rawImg("card_08_rushu_v91"))
                                        .width(100.percent)
                                        .height(Theme.chapterSkinCardH)
                                        .objectFit(ImageFit.Contain)
                                } else if (item.id == 8) {
                                    Image(rawImg("card_09_hanzhong_v91"))
                                        .width(100.percent)
                                        .height(Theme.chapterSkinCardH)
                                        .objectFit(ImageFit.Contain)
                                } else if (item.id == 9) {
                                    Image(rawImg("card_10_beifa_v91"))
                                        .width(100.percent)
                                        .height(Theme.chapterSkinCardH)
                                        .objectFit(ImageFit.Contain)
                                }
                                Row(space: 8) {
                                    Row(space: 2) {
                                        if (item.id == 0) {
                                            Image(rawImg("bust_p01_cangguan"))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                            Image(rawImg("flag_p01_han"))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(rawImg("flag_p02_huang"))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(rawImg("bust_p02_huangjin"))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                        } else if (item.id == 1) {
                                            Image(rawImg("bust_p03_gongsun"))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                            Image(rawImg("flag_p03_gongsun"))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(rawImg("flag_p04_yuan"))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(rawImg("bust_p04_yuanshao"))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                        } else if (item.id == 2) {
                                            Image(rawImg("bust_p05_liubei"))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                            Image(rawImg("flag_p05_liu"))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(rawImg("flag_p06_cao"))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(rawImg("bust_p06_caocao"))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                        } else if (item.id == 3) {
                                            Image(rawImg("bust_p07_lvbu"))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                            Image(rawImg("flag_p07_lv"))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(rawImg("flag_p06_cao"))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(rawImg("bust_p06_caocao"))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                        } else if (item.id == 4) {
                                            Image(rawImg("bust_p04_yuanshao"))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                            Image(rawImg("flag_p04_yuan"))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(rawImg("flag_p06_cao"))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(rawImg("bust_p06_caocao"))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                        } else if (item.id == 5) {
                                            Image(rawImg("bust_p05_liubei"))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                            Image(rawImg("flag_p05_liu"))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(rawImg("flag_p06_cao"))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(rawImg("bust_p06_caocao"))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                        } else if (item.id == 6) {
                                            Image(rawImg("bust_p08_sunquan"))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                            Image(rawImg("flag_p08_sun"))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(rawImg("flag_p06_cao"))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(rawImg("bust_p06_caocao"))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                        } else if (item.id == 7) {
                                            Image(rawImg("bust_p05_liubei"))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                            Image(rawImg("flag_p05_liu"))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(rawImg("flag_gate_pattern"))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(rawImg("bust_s01_guanai"))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                        } else if (item.id == 8) {
                                            Image(rawImg("bust_p09_zhugeliang"))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                            Image(rawImg("flag_p09_zhuge"))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(rawImg("flag_p06_cao"))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(rawImg("bust_p06_caocao"))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                        } else {
                                            Image(rawImg("bust_p09_zhugeliang"))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                            Image(rawImg("flag_p09_zhuge"))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(rawImg("flag_p10_sima"))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(rawImg("bust_p10_simayi"))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                        }
                                    }
                                    .width(Theme.chapterThumbRowW)
                                    .height(Theme.bustThumbH)
                                    .alignItems(VerticalAlign.Center)
                                    Column {
                                        Text(item.label)
                                            .fontSize(11)
                                            .lineHeight(15)
                                            .fontColor(this.cardMutedColor(this.chapterOpen(item.id)))
                                            .fontFamily(this.sansFamily())
                                        Text(item.title)
                                            .fontSize(17)
                                            .fontColor(this.cardTitleColor(this.chapterOpen(item.id)))
                                            .fontFamily(this.serifBoldFamily())
                                            .fontWeight(FontWeight.Bold)
                                            .margin(top: 2)
                                        Text(item.subtitle)
                                            .fontSize(11)
                                            .lineHeight(15)
                                            .fontColor(this.cardMutedColor(this.chapterOpen(item.id)))
                                            .fontFamily(this.sansFamily())
                                            .margin(top: 2)
                                    }
                                    .layoutWeight(1)
                                    .alignItems(HorizontalAlign.Start)
                                    if (this.chapterOpen(item.id)) {
                                        Text("可入")
                                            .fontSize(12)
                                            .fontColor(this.enterInk(index))
                                            .fontFamily(this.sansFamily())
                                            .width(48)
                                            .height(28)
                                            .textAlign(TextAlign.Center)
                                            .backgroundColor(this.enterFill(index))
                                            .borderRadius(6)
                                            .border(width: 1, color: Theme.ink)
                                    } else {
                                        Text("未开")
                                            .fontSize(12)
                                            .fontColor(Theme.locked)
                                            .fontFamily(this.sansFamily())
                                            .width(48)
                                            .textAlign(TextAlign.Center)
                                    }
                                }
                                .width(100.percent)
                                .height(Theme.chapterCardH)
                                .padding(left: 10, right: 10)
                                }
                                .width(100.percent)
                                .backgroundColor(Theme.whitePaper)
                                .borderRadius(10)
                                .border(width: 1, color: this.cardBorder(this.chapterOpen(item.id)))
                                .clip(true)
                                .onClick({event => this.openChapter(item.id)})
                            }
                        )
                    }
                    .width(100.percent)
                }
                .width(100.percent)
                .layoutWeight(1)
                Text(this.chapterOpenFooter())
                    .fontSize(12)
                    .fontColor(Theme.inkMuted)
                    .fontFamily(this.sansFamily())
                    .margin(top: 8, bottom: 8)
                    .width(100.percent)
            } else if (this.screen == 5) {
                Stack {
                    Row {
                        this.backButton({ => this.screen = 4 }, false)
                        Blank()
                    }
                    .width(100.percent)
                    .height(Theme.topBar)
                    Text(this.chapterListTitle())
                        .fontSize(20)
                        .fontColor(Theme.ink)
                        .fontFamily(this.serifBoldFamily())
                        .fontWeight(FontWeight.Bold)
                }
                .width(100.percent)
                .height(Theme.topBar)
                // FIX(M1-polish): On Android Keels, Text without an explicit height measures taller due to default font metrics,
                // and Column inside a layoutWeight(1) Scroll can vertically center when total item height (632vp) is shorter than
                // the Android viewport (~738vp), introducing an extra ~20-25vp gap above row 1.
                // Specifying explicit height(16) and margin(bottom: 6) on listSubtitle, and justifyContent(FlexAlign.Start)
                // on the Column aligns the list to hairline + 22vp, exactly matching HarmonyOS and iOS design baselines.
                Text(this.currentChapter().listSubtitle)
                    .fontSize(12)
                    .height(16)
                    .fontColor(Theme.inkMuted)
                    .fontFamily(this.sansFamily())
                    .margin(bottom: 6)
                    .width(100.percent)
                Scroll {
                    Column(space: 8) {
                        ForEach(
                            ChapterCatalog.levelsOf(this.chapterIndex, this.levels),
                            itemGenerator: {item: LevelDef, index: Int64 =>
                                Row {
                                    if (item.id < this.cleared) {
                                        Text("通")
                                            .fontSize(14)
                                            .fontColor(Theme.success)
                                            .fontFamily(this.serifFamily())
                                            .width(32)
                                            .height(32)
                                            .border(width: 1, color: Theme.success)
                                            .borderRadius(16)
                                            .textAlign(TextAlign.Center)
                                        Column {
                                            Row(space: 6) {
                                                Text(item.name)
                                                    .fontSize(16)
                                                    .fontColor(Theme.ink)
                                                    .fontFamily(this.serifBoldFamily())
                                                    .fontWeight(FontWeight.Bold)
                                                if (ChapterCatalog.isDessert(item.id)) {
                                                    Text("点心")
                                                        .fontSize(11)
                                                        .lineHeight(15)
                                                        .fontColor(Theme.inkMuted)
                                                        .fontFamily(this.sansFamily())
                                                        .padding(left: 4, right: 4)
                                                        .border(width: 1, color: Theme.paperLine)
                                                        .borderRadius(4)
                                                }
                                            }
                                            Text("${item.cols}×${item.rows}")
                                                .fontSize(12)
                                                .fontColor(Theme.inkMuted)
                                                .fontFamily(this.sansFamily())
                                        }
                                        .margin(left: 10)
                                        .alignItems(HorizontalAlign.Start)
                                        Blank()
                                        Text("已通")
                                            .fontSize(12)
                                            .fontColor(Theme.success)
                                            .fontFamily(this.sansFamily())
                                    } else if (item.id == this.cleared) {
                                        Text("${index + 1}")
                                            .fontSize(14)
                                            .fontColor(Theme.whitePaper)
                                            .fontFamily(this.serifFamily())
                                            .width(32)
                                            .height(32)
                                            .backgroundColor(Theme.ink)
                                            .borderRadius(16)
                                            .textAlign(TextAlign.Center)
                                        Column {
                                            Row(space: 6) {
                                                Text(item.name)
                                                    .fontSize(16)
                                                    .fontColor(Theme.ink)
                                                    .fontFamily(this.serifBoldFamily())
                                                    .fontWeight(FontWeight.Bold)
                                                if (ChapterCatalog.isDessert(item.id)) {
                                                    Text("点心")
                                                        .fontSize(11)
                                                        .lineHeight(15)
                                                        .fontColor(Theme.ink)
                                                        .fontFamily(this.sansFamily())
                                                        .padding(left: 4, right: 4)
                                                        .border(width: 1, color: Theme.ink)
                                                        .borderRadius(4)
                                                }
                                            }
                                            Text("${item.cols}×${item.rows}")
                                                .fontSize(12)
                                                .fontColor(Theme.inkMuted)
                                                .fontFamily(this.sansFamily())
                                        }
                                        .margin(left: 10)
                                        .alignItems(HorizontalAlign.Start)
                                        Blank()
                                        Text("当前")
                                            .fontSize(12)
                                            .fontColor(Theme.ink)
                                            .fontFamily(this.sansFamily())
                                    } else {
                                        Text("${index + 1}")
                                            .fontSize(14)
                                            .fontColor(Theme.locked)
                                            .fontFamily(this.serifFamily())
                                            .width(32)
                                            .height(32)
                                            .border(width: 1, color: Theme.locked)
                                            .borderRadius(16)
                                            .textAlign(TextAlign.Center)
                                        Column {
                                            Row(space: 6) {
                                                Text(item.name)
                                                    .fontSize(16)
                                                    .fontColor(Theme.locked)
                                                    .fontFamily(this.serifBoldFamily())
                                                    .fontWeight(FontWeight.Bold)
                                                if (ChapterCatalog.isDessert(item.id)) {
                                                    Text("点心")
                                                        .fontSize(11)
                                                        .lineHeight(15)
                                                        .fontColor(Theme.locked)
                                                        .fontFamily(this.sansFamily())
                                                        .padding(left: 4, right: 4)
                                                        .border(width: 1, color: Theme.locked)
                                                        .borderRadius(4)
                                                }
                                            }
                                            Text("${item.cols}×${item.rows}")
                                                .fontSize(12)
                                                .fontColor(Theme.locked)
                                                .fontFamily(this.sansFamily())
                                        }
                                        .margin(left: 10)
                                        .alignItems(HorizontalAlign.Start)
                                        Blank()
                                        Text("锁")
                                            .fontSize(12)
                                            .fontColor(Theme.locked)
                                            .fontFamily(this.sansFamily())
                                    }
                                }
                                .width(100.percent)
                                .height(56)
                                .padding(left: 12, right: 12)
                                .backgroundColor(Theme.whitePaper)
                                .borderRadius(10)
                                .border(width: 1, color: this.rowBorder(item.id))
                                .onClick({event => this.openFromList(item.id)})
                            }
                        )
                    }
                    .width(100.percent)
                    .justifyContent(FlexAlign.Start)
                }
                .width(100.percent)
                .layoutWeight(1)
                /* 共10驿 — sizes stay ${item.cols}×${item.rows} from levels.json */
                Text(this.chapterListFooter())
                    .fontSize(12)
                    .fontColor(Theme.inkMuted)
                    .fontFamily(this.sansFamily())
                    .margin(top: 8, bottom: 8)
                    .width(100.percent)
            } else if (this.screen == 6) {
                /* Skin-only preview for locked 05–10. No boards, no gameplay. */
                Stack {
                    Row {
                        this.backButton({ => this.screen = 4 }, false)
                        Blank()
                    }
                    .width(100.percent)
                    .height(Theme.topBar)
                    .padding(left: Theme.inset, right: Theme.inset)
                    Text(this.currentChapter().title)
                        .fontSize(20)
                        .fontColor(Theme.ink)
                        .fontFamily(this.serifBoldFamily())
                        .fontWeight(FontWeight.Bold)
                }
                .width(100.percent)
                .height(Theme.topBar)
                Text(this.currentChapter().listSubtitle)
                    .fontSize(12)
                    .fontColor(Theme.inkMuted)
                    .fontFamily(this.sansFamily())
                    .padding(left: Theme.inset, right: Theme.inset)
                    .margin(bottom: 4)
                    .width(100.percent)
                if (this.chapterIndex == 4) {
                    Image(rawImg("skin_05_touyuan_v91"))
                        .width(100.percent)
                        .layoutWeight(1)
                        .objectFit(ImageFit.Contain)
                } else if (this.chapterIndex == 5) {
                    Image(rawImg("skin_06_jingzhou_v91"))
                        .width(100.percent)
                        .layoutWeight(1)
                        .objectFit(ImageFit.Contain)
                } else if (this.chapterIndex == 6) {
                    Image(rawImg("skin_07_chibi_v91"))
                        .width(100.percent)
                        .layoutWeight(1)
                        .objectFit(ImageFit.Contain)
                } else if (this.chapterIndex == 7) {
                    Image(rawImg("skin_08_rushu_v91"))
                        .width(100.percent)
                        .layoutWeight(1)
                        .objectFit(ImageFit.Contain)
                } else if (this.chapterIndex == 8) {
                    Image(rawImg("skin_09_hanzhong_v91"))
                        .width(100.percent)
                        .layoutWeight(1)
                        .objectFit(ImageFit.Contain)
                } else {
                    Image(rawImg("skin_10_beifa_v91"))
                        .width(100.percent)
                        .layoutWeight(1)
                        .objectFit(ImageFit.Contain)
                }
            } else if (this.screen == 2) {
                // in-page back: iOS edge swipe does not pop on Keels 0.2.2
                Row {
                    // A2: 48vp hit area
                    this.backButton({ => this.leaveBoard() }, true)
                    Blank()
                }
                .width(100.percent)
                .height(48)
                .padding(left: Theme.inset, right: Theme.inset)
                Blank()
                Column {
                    Text("通关")
                        .fontSize(14)
                        .fontColor(Theme.inkMuted)
                        .fontFamily(this.sansFamily())
                        .margin(bottom: 8)
                    Text(this.roadTitle())
                        .fontSize(26)
                        .fontColor(Theme.ink)
                        .fontFamily(this.serifBoldFamily())
                        .fontWeight(FontWeight.Bold)
                        .margin(bottom: 16)
                    Row {
                        Column {
                            Text("驿道已通")
                                .fontSize(14)
                                .fontColor(Theme.inkMuted)
                                .fontFamily(this.sansFamily())
                            Text("文书递达本驿")
                                .fontSize(14)
                                .fontColor(Theme.inkMuted)
                                .fontFamily(this.sansFamily())
                                .margin(top: 4)
                        }
                        .alignItems(HorizontalAlign.Start)
                        Blank()
                        /* Win seal copy: 文书到 (vermillion only). */
                        Column {
                            Text("文")
                                .fontSize(13)
                                .fontColor(Theme.whitePaper)
                                .fontFamily(this.serifFamily())
                            Text("书")
                                .fontSize(13)
                                .fontColor(Theme.whitePaper)
                                .fontFamily(this.serifFamily())
                            Text("到")
                                .fontSize(13)
                                .fontColor(Theme.whitePaper)
                                .fontFamily(this.serifFamily())
                        }
                        .width(52)
                        .height(52)
                        .backgroundColor(Theme.vermillion)
                        .justifyContent(FlexAlign.Center)
                        .alignItems(HorizontalAlign.Center)
                        .rotate(angle: 10.0)
                    }
                    .width(100.percent)
                    .margin(bottom: 24)
                    Button("下一驿")
                        .width(100.percent)
                        .height(Theme.primaryH)
                        .backgroundColor(Theme.qingDeep)
                        .fontColor(Theme.whitePaper)
                        .fontSize(16)
                        .fontFamily(this.sansMediumFamily())
                        .onClick({event => this.nextLevel()})
                }
                .width(86.percent)
                .padding(20)
                .backgroundColor(Theme.whitePaper)
                .borderRadius(12)
                Blank()
            }
            // Keels 0.2.2 leaks @State subscriptions of destroyed subtrees; keep board mounted
            Column {
                Stack {
                    Text(this.roadTitle())
                        .fontSize(18)
                        .fontColor(Theme.ink)
                        .fontFamily(this.serifBoldFamily())
                        .fontWeight(FontWeight.Bold)
                        .width(100.percent)
                        .height(48)
                        .textAlign(TextAlign.Center)
                        .padding(left: 64, right: 64)
                        .position(x: 0, y: 0)

                    Text(this.boardSubtitle())
                        .fontSize(12)
                        .fontColor(Theme.inkMuted)
                        .fontFamily(this.sansFamily())
                        .maxLines(1)
                        .textOverflow(TextOverflow.Ellipsis)
                        .textAlign(TextAlign.Center)
                        .width(100.percent)
                        .height(16)
                        .padding(left: 64, right: 64)
                        .position(x: 0, y: 37)

                    Row {
                        // A2: 48vp hit area — in-page back: iOS edge swipe does not pop on Keels 0.2.2
                        this.backButton({ => this.leaveBoard() }, true)
                        Blank()
                    }
                    .width(100.percent)
                    .height(48)
                    .padding(left: Theme.inset, right: Theme.inset)
                    .position(x: 0, y: 0)
                }
                .width(100.percent)
                .height(56)

                Column() {}
                    .width(100.percent)
                    .height(1)
                    .backgroundColor(Theme.paperLine)
                    .margin(left: 20, right: 20)

                if (this.hasParityBoard() || this.curLevel().stepLimit > 0) {
                    Row(space: 8) {
                        if (this.hasParityBoard()) {
                            Text(this.stepChipLabel())
                                .fontSize(15)
                                .fontWeight(FontWeight.Bold)
                                .fontColor(Theme.ink)
                                .fontFamily(this.serifBoldFamily())
                                .padding(left: 12, right: 12)
                                .height(28)
                                .borderRadius(4)
                                .border(width: 1, color: this.stepChipBorder())
                                .backgroundColor(Theme.whitePaper)
                        }
                        if (this.curLevel().stepLimit > 0) {
                            Text("余步 · ${this.remainingSteps()}")
                                .fontSize(15)
                                .fontWeight(FontWeight.Bold)
                                .fontColor(Theme.ink)
                                .fontFamily(this.serifBoldFamily())
                                .padding(left: 12, right: 12)
                                .height(28)
                                .borderRadius(4)
                                .border(width: this.stepLeftBorderW(), color: this.stepLeftBorderColor())
                                .backgroundColor(Theme.whitePaper)
                        }
                    }
                    .justifyContent(FlexAlign.Center)
                    .width(100.percent)
                    .height(28)
                    .margin(top: 8, bottom: 8)
                }
                /* BANDS.md composite: chapters 0..9.
                   Full-width 360×100 vp; Theme.bandClear keeps bust/flags
                   out of the Canvas grid (band.bottom ≤ board.top − 30px). */
                Column {
                    if (this.chapterIndex == 0) {
                        Image(rawImg("band_zhuojun_v91"))
                            .width(100.percent)
                            .height(Theme.bandH)
                    } else if (this.chapterIndex == 1) {
                        Image(rawImg("band_pingyuan_v91"))
                            .width(100.percent)
                            .height(Theme.bandH)
                    } else if (this.chapterIndex == 2) {
                        Image(rawImg("band_xuzhou_v91"))
                            .width(100.percent)
                            .height(Theme.bandH)
                    } else if (this.chapterIndex == 3) {
                        Image(rawImg("band_lvbu_v91"))
                            .width(100.percent)
                            .height(Theme.bandH)
                    } else if (this.chapterIndex == 4) {
                        Image(rawImg("band_touyuan_v91"))
                            .width(100.percent)
                            .height(Theme.bandH)
                    } else if (this.chapterIndex == 5) {
                        Image(rawImg("band_jingzhou_v91"))
                            .width(100.percent)
                            .height(Theme.bandH)
                    } else if (this.chapterIndex == 6) {
                        Image(rawImg("band_chibi_v91"))
                            .width(100.percent)
                            .height(Theme.bandH)
                    } else if (this.chapterIndex == 7) {
                        Image(rawImg("band_rushu_v91"))
                            .width(100.percent)
                            .height(Theme.bandH)
                    } else if (this.chapterIndex == 8) {
                        Image(rawImg("band_hanzhong_v91"))
                            .width(100.percent)
                            .height(Theme.bandH)
                    } else {
                        Image(rawImg("band_beifa_v91"))
                            .width(100.percent)
                            .height(Theme.bandH)
                    }
                }
                .width(100.percent)
                .height(Theme.bandH)
                .margin(top: if (this.hasParityBoard() || this.curLevel().stepLimit > 0) { 0 } else { 4 }, bottom: Theme.bandClear)
                Scroll {
                    Column {
                        Stack(alignContent: Alignment.TopStart) {
                            // Keys omit boardGen so unchanged shapes are reused between moves (perf); content fields keep keys unique.
                            // Layer 1: Cells (fill whitePaper/paperShade per cell with radius 2 and 1vp paperLine outline)
                            ForEach(
                                this.boardCells,
                                itemGenerator: { item: BoardRect, idx: Int64 =>
                                    Rect(width: item.w, height: item.h)
                                        .radius(2)
                                        .fill(item.color)
                                        .stroke(Theme.paperLine)
                                        .strokeWidth(1)
                                        .position(x: item.x, y: item.y)
                                },
                                // Keels 0.2.2: ForEach key label is keyGeneratorFunc (macro passes it to forEachUpdateFunction)
                                keyGeneratorFunc: { item: BoardRect, idx: Int64 =>
                                    "${idx}-${item.x}-${item.y}-${item.color}"
                                }
                            )

                            // Layer 3: Walls (4x24 ink round-cap bars centred exactly on the seam midpoint)
                            ForEach(
                                this.boardWalls,
                                itemGenerator: { item: BoardSeg, idx: Int64 =>
                                    Line(width: this.boardW(), height: this.boardH())
                                        .startPoint((item.x1, item.y1))
                                        .endPoint((item.x2, item.y2))
                                        .stroke(item.color)
                                        .strokeWidth(item.width)
                                        .strokeLineCap(LineCapStyle.Round)
                                        .antiAlias(true)
                                },
                                keyGeneratorFunc: { item: BoardSeg, idx: Int64 =>
                                    "${idx}-${item.x1}-${item.y1}-${item.x2}-${item.y2}-${item.color}"
                                }
                            )

                            // Layer 4: Parity labels (HarmonyOS: 11 device px serif inkMuted, textAlign start, baseline at my+4.0)
                            // HarmonyOS parity: 11 device px (Canvas px); readability noted in M2 report
                            ForEach(
                                this.boardParityLabels,
                                itemGenerator: { item: BoardLabel, idx: Int64 =>
                                    Text(if (item.text == "奇") { "奇" } else { "偶" })
                                        .fontSize(item.size)
                                        .fontColor(item.color)
                                        .fontFamily(this.serifFamily())
                                        .width(item.w)
                                        .textAlign(TextAlign.Start)
                                        .position(x: item.x, y: item.y)
                                },
                                keyGeneratorFunc: { item: BoardLabel, idx: Int64 =>
                                    "${idx}-${item.x}-${item.y}-${item.text}-${item.color}-${item.size}"
                                }
                            )

                            // Layer 5: Route polyline
                            // Route: one Line per consecutive pair with strokeLineCap Round.
                            // Round caps on every segment give round joins at corners in native vp coordinates without device px scaling artifacts.
                            ForEach(
                                this.boardRoute,
                                itemGenerator: { item: BoardSeg, idx: Int64 =>
                                    Line(width: this.boardW(), height: this.boardH())
                                        .startPoint((item.x1, item.y1))
                                        .endPoint((item.x2, item.y2))
                                        .stroke(item.color)
                                        .strokeWidth(item.width)
                                        .strokeLineCap(LineCapStyle.Round)
                                        .antiAlias(true)
                                },
                                keyGeneratorFunc: { item: BoardSeg, idx: Int64 =>
                                    "${idx}-${item.x1}-${item.y1}-${item.x2}-${item.y2}"
                                }
                            )

                            // Layer 6: Head dot (r=6 whitePaper fill + ink hairline)
                            ForEach(
                                this.boardDots,
                                itemGenerator: { item: BoardDot, idx: Int64 =>
                                    Circle(width: item.r * 2.0, height: item.r * 2.0)
                                        .fill(item.fill)
                                        .stroke(item.stroke)
                                        .strokeWidth(item.strokeW)
                                        .position(x: item.cx - item.r, y: item.cy - item.r)
                                },
                                keyGeneratorFunc: { item: BoardDot, idx: Int64 =>
                                    "${idx}-${item.cx}-${item.cy}-${item.r}-${item.fill}"
                                }
                            )

                            // Layer 7: Station circles (+ next ring)
                            ForEach(
                                this.boardStationCircles,
                                itemGenerator: { item: BoardDot, idx: Int64 =>
                                    Circle(width: item.r * 2.0, height: item.r * 2.0)
                                        .fill(item.fill)
                                        .fillOpacity(if (item.fill <= 0x01000000) { 0.0 } else { 1.0 })
                                        .stroke(item.stroke)
                                        .strokeWidth(if (item.hasStroke) { item.strokeW } else { 0.0 })
                                        .position(x: item.cx - item.r, y: item.cy - item.r)
                                },
                                keyGeneratorFunc: { item: BoardDot, idx: Int64 =>
                                    "${idx}-${item.cx}-${item.cy}-${item.r}-${item.fill}-${item.stroke}-${item.hasStroke}"
                                }
                            )

                            // Layer 8: Next station label ("下一驿" 11 device px sans gold, textAlign start, baseline at cy+r+12.0)
                            // HarmonyOS parity: 11 device px (Canvas px); readability noted in M2 report
                            ForEach(
                                this.boardNextLabels,
                                itemGenerator: { item: BoardLabel, idx: Int64 =>
                                    Text("下一驿")
                                        .fontSize(item.size)
                                        .fontColor(item.color)
                                        .fontFamily(this.sansFamily())
                                        .width(item.w)
                                        .textAlign(TextAlign.Start)
                                        .position(x: item.x, y: item.y)
                                },
                                keyGeneratorFunc: { item: BoardLabel, idx: Int64 =>
                                    "${idx}-${item.x}-${item.y}-${item.text}-${item.size}"
                                }
                            )

                            // Layer 9: Digits (Path with filled outlines, nonzero fill)
                            ForEach(
                                this.boardDigits,
                                itemGenerator: { item: BoardPath, idx: Int64 =>
                                    Path(width: this.boardW(), height: this.boardH(), commands: item.commands)
                                        .fill(item.color)
                                        .fillOpacity(1.0)
                                        .strokeWidth(0)
                                        .antiAlias(true)
                                        .position(x: 0, y: 0)
                                },
                                keyGeneratorFunc: { item: BoardPath, idx: Int64 =>
                                    "${idx}-${item.color}-${item.commands}"
                                }
                            )

                            // Parity reject overlay: flashing edge line + toast
                            if (this.parityRejectFlash && this.parityRejectText.size > 0) {
                                Line(width: this.boardW(), height: this.boardH())
                                    .startPoint(this.rejectEdgeStartPoint())
                                    .endPoint(this.rejectEdgeEndPoint())
                                    .stroke(Theme.vermillion)
                                    .strokeWidth(3)
                                    .strokeLineCap(LineCapStyle.Round)
                                    .antiAlias(true)
                                Text(this.parityRejectText)
                                    .fontSize(14)
                                    .fontFamily(this.serifBoldFamily())
                                    .fontColor(Theme.vermillion)
                                    .maxLines(1)
                                    .width(86)
                                    .height(28)
                                    .textAlign(TextAlign.Center)
                                    .padding(left: 14, right: 14)
                                    .borderRadius(4)
                                    .border(width: 1, color: Theme.vermillion)
                                    .backgroundColor(Theme.whitePaper)
                                    .position(x: this.rejectToastX(), y: this.rejectToastY())
                                    .visibility(if (this.rejectPlacement().shown) { Visibility.Visible } else { Visibility.None })
                            }
                        }
                        .width(this.boardW())
                        .height(this.boardH())
                        .backgroundColor(Theme.paperShade)
                        .border(width: 1, color: Theme.paperLine)
                        .borderRadius(8)
                        .onTouch({ evt =>
                            match (evt.eventType) {
                                case TouchType.Down => this.handleDrag(evt, true)
                                case TouchType.Move => this.handleDrag(evt, false)
                                case _ => ()
                            }
                        })
                    }
                    .width(100.percent)
                    .alignItems(HorizontalAlign.Center)
                }
                .width(100.percent)
                .height(this.boardH() + 2)
                Text(this.chromeLine())
                    .fontSize(11)
                    .lineHeight(15)
                    .fontColor(Theme.inkMuted)
                    .fontFamily(this.sansFamily())
                    .padding(left: Theme.inset, right: Theme.inset)
                    .margin(top: 14, bottom: 4)
                    .width(100.percent)
                Column() {}.width(100.percent).layoutWeight(1)
                // Divider not in OpenSDK 0.2.2: 1vp hairline Column, same color/width as HarmonyOS
                Column() {}.width(100.percent).height(1).backgroundColor(Theme.paperLine)
                Row(space: 12) {
                    Row(space: 8) {
                        Image(rawSvg("icon-undo"))
                            .width(Theme.iconVp)
                            .height(Theme.iconVp)
                        Text("撤销")
                            .fontSize(16)
                            .fontColor(Theme.ink)
                            .fontFamily(this.sansFamily())
                    }
                    .layoutWeight(1)
                    .height(Theme.undoH)
                    .justifyContent(FlexAlign.Center)
                    .alignItems(VerticalAlign.Center)
                    .backgroundColor(Theme.whitePaper)
                    .borderRadius(8)
                    .border(width: 1, color: Theme.ink)
                    .onClick({event => this.doUndo()})
                    Row(space: 8) {
                        Image(rawSvg("icon-reset"))
                            .width(Theme.iconVp)
                            .height(Theme.iconVp)
                        Text("重绘驿道")
                            .fontSize(16)
                            .fontColor(Theme.ink)
                            .fontFamily(this.sansFamily())
                    }
                    .layoutWeight(1)
                    .height(Theme.undoH)
                    .justifyContent(FlexAlign.Center)
                    .alignItems(VerticalAlign.Center)
                    .backgroundColor(Theme.whitePaper)
                    .borderRadius(8)
                    .border(width: 1, color: Theme.ink)
                    .onClick({event => this.doClear()})
                }
                .width(100.percent)
                .height(Theme.bottomBar)
                .alignItems(VerticalAlign.Center)
                .padding(left: Theme.inset, right: Theme.inset)
                        }
            .visibility(if (this.screen == 1) { Visibility.Visible } else { Visibility.None })
            .width(100.percent)
            .layoutWeight(1)
        }
        .width(100.percent)
        .height(100.percent)
        .padding(left: this.playInset(), right: this.playInset())
        .backgroundColor(this.playPaper())
        .alignItems(HorizontalAlign.Center)
        .onAreaChange({ old, new =>
            let w = new.width.value
            let targetW = if (w > 0.0) { w } else { 360.0 }
            if (targetW - this.winW > 0.5 || this.winW - targetW > 0.5) {
                this.winW = targetW
                this.rebuildBoard()
            }
        })
    }
}
