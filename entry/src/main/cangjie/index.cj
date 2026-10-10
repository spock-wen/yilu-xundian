package ohos_app_cangjie_entry

import kit.ArkUI.*
import ohos.arkui.state_macro_manage.*
import std.math.sqrt
import ohos_app_cangjie_entry.engine.{Cell, GridLayout, GridPath, touchToCell}
import ohos_app_cangjie_entry.game.{FerryDef, LevelDef, PatrolGame}

/*
 * Canvas + onTouch from official docs_cangjie (kit.ArkUI.*).
 * lineWidth / strokeStyle / fillStyle / font / lineCap are properties.
 * Draw after onReady. Touch field is event.eventType.
 * Skin tokens: designer mocks 01–06 via Theme.
 */
@Entry
@Component
class EntryView {
    var boardSettings: RenderingContextSettings = RenderingContextSettings(antialias: true)
    var context: CanvasRenderingContext2D = CanvasRenderingContext2D(this.boardSettings)
    var markSettings: RenderingContextSettings = RenderingContextSettings(antialias: true)
    var markContext: CanvasRenderingContext2D = CanvasRenderingContext2D(this.markSettings)
    var undoSettings: RenderingContextSettings = RenderingContextSettings(antialias: true)
    var undoContext: CanvasRenderingContext2D = CanvasRenderingContext2D(this.undoSettings)
    var redrawSettings: RenderingContextSettings = RenderingContextSettings(antialias: true)
    var redrawContext: CanvasRenderingContext2D = CanvasRenderingContext2D(this.redrawSettings)
    var game: PatrolGame = PatrolGame(LevelCatalog.byIndex(0))

    @State var screen: Int64 = 0
    @State var levelIndex: Int64 = 0
    @State var chapterIndex: Int64 = 0
    @State var boardBack: Int64 = 0
    @State var tick: Int64 = 0
    @State var cleared: Int64 = 0
    @State var stepFilled: Int64 = 0
    @State var parityRejectText: String = ""
    @State var parityRejectFlash: Bool = false
    @State var parityRejectGen: Int64 = 0

    func clearParityReject(): Unit {
        this.parityRejectGen = this.parityRejectGen + 1
        this.parityRejectText = ""
        this.parityRejectFlash = false
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
        this.parityRejectGen = this.parityRejectGen + 1
        let gen = this.parityRejectGen
        /* UI-thread delayed clear: animateTo's onFinish runs on the
           UI thread, so @State writes repaint immediately.  The 180ms
           duration drives a no-op animation; onFinish clears the toast. */
        this.getUIContext().animateTo(
            AnimateParam(duration: 180, onFinish: Some({ =>
                if (gen == this.parityRejectGen) {
                    this.clearParityReject()
                }
            })),
            { => }
        )
    }

    func remainingSteps(): Int64 {
        let lim = this.game.level.stepLimit
        if (lim <= 0) { return 0 }
        var taken = this.stepFilled - 1
        if (taken < 0) { taken = 0 }
        let left = lim - taken
        if (left < 0) { return 0 }
        return left
    }

    func stepChipBorder(): Int64 {
        if (this.parityRejectFlash) { return Theme.vermillion }
        return Theme.paperLine
    }

    func hasParityBoard(): Bool {
        return this.game.level.parityEdges.size > 0
    }

    func stepChipLabel(): String {
        return "第 ${this.stepFilled} 步"
    }

    func cellVp(): Int64 {
        let cols = this.game.level.cols
        let rows = this.game.level.rows
        if (cols == 6 && rows == 8) {
            return Theme.tutorialCell
        }
        return Theme.boardInner / cols
    }

    func boardW(): Int64 {
        return this.game.level.cols * this.cellVp()
    }

    func boardH(): Int64 {
        return this.game.level.rows * this.cellVp()
    }

    func currentLayout(): GridLayout {
        return GridLayout(0.0, 0.0, Float64(this.cellVp()), this.game.level.cols, this.game.level.rows)
    }

    func roadTitle(): String {
        return this.game.level.name
    }

    func currentName(): String {
        if (this.cleared >= LevelCatalog.count()) {
            return "已通"
        }
        return LevelCatalog.byIndex(this.cleared).name
    }

    func refresh(): Unit {
        this.tick = this.tick + 1
        this.stepFilled = this.game.filled()
        this.drawBoard()
    }

    func openLevel(index: Int64): Unit {
        this.levelIndex = index
        this.chapterIndex = ChapterCatalog.chapterIdForLevel(index)
        this.game.reset(LevelCatalog.byIndex(index))
        this.screen = 1
        this.refresh()
    }

    func startPlay(): Unit {
        this.boardBack = 0
        if (this.cleared >= LevelCatalog.count()) {
            this.openLevel(LevelCatalog.count() - 1)
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
        /* 平原 board + 通关 share sage paper. screen==2 used to fall
           through to 涿郡 Theme.paper and flash the win sheet. */
        if ((this.screen == 1 || this.screen == 2) && this.levelIndex >= 10) {
            return Theme.pingyuanPaper
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
            return LevelCatalog.byIndex(ch.levelStart).name
        }
        return LevelCatalog.byIndex(this.cleared).name
    }

    func chapterListFooter(): String {
        let ch = this.currentChapter()
        let n = ChapterCatalog.clearedCount(this.chapterIndex, this.cleared)
        /* 本章尺寸取自 LevelCatalog 首驿（ch1–3 6×6，ch4–10 7×7）。 */
        let board = LevelCatalog.byIndex(ch.levelStart)
        return "已通 ${n} · 当前${this.chapterCurrentName()} · 共10驿 · ${board.cols}×${board.rows}"
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
        if (nxt >= LevelCatalog.count()) {
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

    /* Approved 24vp stroke-only undo/redraw (icons/icon-undo.svg,
       icons/icon-reset.svg). SVG A → Path2D.arc; open chevron is two
       separate moveTo/lineTo strokes. lineWidth is a property
       (docs_cangjie cj-canvas-drawing-canvasrenderingcontext2d.md).
       Harmony Button default start-icon tofu is avoided by drawing on
       Canvas inside a clickable Row. */
    func drawUndoIcon(): Unit {
        this.undoContext.clearRect(0.0, 0.0, Float64(Theme.iconVp), Float64(Theme.iconVp))
        this.undoContext.lineWidth = 1.5
        this.undoContext.strokeStyle = Theme.ink
        this.undoContext.lineCap = "round"
        let undoArc = Path2D()
        undoArc.arc(13.02, 12.07, 6.35, 2.28, 4.18, counterclockwise: true)
        this.undoContext.stroke(undoArc)
        let undoArmA = Path2D()
        undoArmA.moveTo(12.0, 2.5)
        undoArmA.lineTo(6.5, 6.5)
        this.undoContext.stroke(undoArmA)
        let undoArmB = Path2D()
        undoArmB.moveTo(6.5, 9.5)
        undoArmB.lineTo(12.0, 14.0)
        this.undoContext.stroke(undoArmB)
    }

    func drawRedrawIcon(): Unit {
        this.redrawContext.clearRect(0.0, 0.0, Float64(Theme.iconVp), Float64(Theme.iconVp))
        this.redrawContext.lineWidth = 1.5
        this.redrawContext.strokeStyle = Theme.ink
        this.redrawContext.lineCap = "round"
        let redrawArc = Path2D()
        redrawArc.arc(10.98, 12.07, 6.35, 0.86, 5.24, counterclockwise: false)
        this.redrawContext.stroke(redrawArc)
        let redrawArmA = Path2D()
        redrawArmA.moveTo(12.0, 2.5)
        redrawArmA.lineTo(17.5, 6.5)
        this.redrawContext.stroke(redrawArmA)
        let redrawArmB = Path2D()
        redrawArmB.moveTo(17.5, 9.5)
        redrawArmB.lineTo(12.0, 14.0)
        this.redrawContext.stroke(redrawArmB)
    }

    func handleDrag(event: TouchEvent): Unit {
        /* Win sets screen=2 then refresh(); a trailing Move can still
           hit the Canvas and drag-back-undo the last cell. */
        if (this.screen != 1) {
            return
        }
        let px = event.touches[0].x
        let py = event.touches[0].y
        let hit = touchToCell(px, py, this.currentLayout())
        match (hit) {
            case None => ()
            case Some(cell) =>
                if (this.game.tryStep(cell)) {
                    this.clearParityReject()
                    if (this.game.isWin()) {
                        if (this.levelIndex + 1 > this.cleared) {
                            this.cleared = this.levelIndex + 1
                        }
                        this.screen = 2
                    }
                    this.refresh()
                } else {
                    if (this.game.lastRejectParity != 0) {
                        this.showParityReject()
                        this.refresh()
                    }
                }
        }
    }

    func rowBorder(index: Int64): Int64 {
        if (index == this.cleared) {
            return Theme.ink
        }
        return Theme.whitePaper
    }

    func stationState(n: Int64): Int64 {
        let nxt = this.game.nextRequired()
        if (n < nxt) {
            return 2
        }
        if (n == nxt) {
            return 1
        }
        return 0
    }

    /* Waypoint digits 0–15 as Path2D in vp — same unit as arc / the
       station circle (cj-canvas-drawing-path2d.md moveTo/lineTo/arc
       「默认单位：vp」). fillText / font px and vp2px did not enlarge
       ink on device. Glyph height 0.60 of diameter (tutorial 40 → 24vp). */
    func strokeStationPath(path: Path2D, h: Float64): Unit {
        this.context.lineWidth = h * 0.16
        this.context.lineCap = "round"
        this.context.lineJoin = "round"
        this.context.stroke(path)
    }

    func drawStationNumber(n: Int64, cx: Float64, cy: Float64, h: Float64): Unit {
        if (n >= 10) {
            let pair = h * 0.90
            this.drawStationDigit(1, cx - h * 0.34, cy, pair)
            this.drawStationDigit(n - 10, cx + h * 0.30, cy, pair)
            return
        }
        this.drawStationDigit(n, cx, cy, h)
    }

    func drawStationDigit(d: Int64, cx: Float64, cy: Float64, h: Float64): Unit {
        let path = Path2D()
        if (d == 0) {
            path.arc(cx, cy, h * 0.22, 0.0, 6.28)
        } else if (d == 1) {
            path.moveTo(cx - h * 0.16, cy - h * 0.18)
            path.lineTo(cx + h * 0.04, cy - h * 0.32)
            path.lineTo(cx + h * 0.04, cy + h * 0.32)
            path.moveTo(cx - h * 0.18, cy + h * 0.32)
            path.lineTo(cx + h * 0.20, cy + h * 0.32)
        } else if (d == 2) {
            path.arc(cx, cy - h * 0.14, h * 0.18, 2.90, 0.35, counterclockwise: false)
            path.lineTo(cx - h * 0.22, cy + h * 0.32)
            path.lineTo(cx + h * 0.22, cy + h * 0.32)
        } else if (d == 3) {
            path.arc(cx, cy - h * 0.14, h * 0.16, 2.70, 0.70, counterclockwise: false)
            path.moveTo(cx + h * 0.16, cy + h * 0.14)
            path.arc(cx, cy + h * 0.14, h * 0.17, 5.60, 2.20, counterclockwise: false)
        } else if (d == 4) {
            path.moveTo(cx + h * 0.14, cy + h * 0.32)
            path.lineTo(cx + h * 0.14, cy - h * 0.32)
            path.lineTo(cx - h * 0.22, cy + h * 0.04)
            path.lineTo(cx + h * 0.24, cy + h * 0.04)
        } else if (d == 5) {
            path.moveTo(cx + h * 0.20, cy - h * 0.32)
            path.lineTo(cx - h * 0.18, cy - h * 0.32)
            path.lineTo(cx - h * 0.18, cy - h * 0.02)
            path.lineTo(cx + h * 0.06, cy - h * 0.02)
            path.arc(cx, cy + h * 0.14, h * 0.18, 5.20, 2.40, counterclockwise: false)
        } else if (d == 6) {
            path.arc(cx, cy + h * 0.10, h * 0.18, 0.0, 6.28)
            path.moveTo(cx - h * 0.18, cy + h * 0.10)
            path.lineTo(cx - h * 0.10, cy - h * 0.32)
        } else if (d == 7) {
            path.moveTo(cx - h * 0.22, cy - h * 0.32)
            path.lineTo(cx + h * 0.22, cy - h * 0.32)
            path.lineTo(cx - h * 0.04, cy + h * 0.32)
        } else if (d == 8) {
            path.arc(cx, cy - h * 0.14, h * 0.14, 0.0, 6.28)
            path.moveTo(cx + h * 0.16, cy + h * 0.16)
            path.arc(cx, cy + h * 0.16, h * 0.16, 0.0, 6.28)
        } else if (d == 9) {
            path.arc(cx, cy - h * 0.10, h * 0.18, 0.0, 6.28)
            path.moveTo(cx + h * 0.18, cy - h * 0.10)
            path.lineTo(cx + h * 0.12, cy + h * 0.32)
        }
        this.strokeStationPath(path, h)
    }

    /* ---- 渡口(仅 this.game.level.ferry 为 Some 时画) ---- */
    /* 画法抄 mobile/cjmp/lib/board_mech.cj:
       buildBoardMechDots —— 甲乙各两个同心描边圆(r=0.38c 线宽 1.5、r=0.30c
         线宽 1.0,色 qingDeep,无填充);
       buildBoardMechLabels —— 甲/乙 0.30c 居中(格内有驿号时小字 0.20c 放左上角),
         甲乙中点「渡」0.24c 色 qing;
       buildBoardMechPaths 的 d 段 —— 甲乙圆环之间的虚线,走过 甲→乙 后深色加粗。
       层序同 CJMP(驿站圆 → 甲/乙/渡 字 → 虚线),故放在 waypoints 循环之后。 */
    func drawFerry(f: FerryDef, cs: Float64): Unit {
        let jx = (Float64(f.jiaX) + 0.5) * cs
        let jy = (Float64(f.jiaY) + 0.5) * cs
        let yx = (Float64(f.yiX) + 0.5) * cs
        let yy = (Float64(f.yiY) + 0.5) * cs
        this.drawFerryRings(jx, jy, cs)
        this.drawFerryRings(yx, yy, cs)
        /* 格内有驿号 → 小字放左上角 0.2c;否则居中 0.30c。 */
        if (this.game.level.numberAt(f.jiaX, f.jiaY) != 0) {
            let s = 0.20 * cs
            this.drawFerryChar("甲", Float64(f.jiaX) * cs + 0.08 * cs + s * 0.5,
                Float64(f.jiaY) * cs + 0.06 * cs + s * 0.5, s, Theme.qingDeep)
        } else {
            this.drawFerryChar("甲", jx, jy, 0.30 * cs, Theme.qingDeep)
        }
        if (this.game.level.numberAt(f.yiX, f.yiY) != 0) {
            let s = 0.20 * cs
            this.drawFerryChar("乙", Float64(f.yiX) * cs + 0.08 * cs + s * 0.5,
                Float64(f.yiY) * cs + 0.06 * cs + s * 0.5, s, Theme.qingDeep)
        } else {
            this.drawFerryChar("乙", yx, yy, 0.30 * cs, Theme.qingDeep)
        }
        this.drawFerryChar("渡", (jx + yx) * 0.5, (jy + yy) * 0.5, 0.24 * cs, Theme.qing)
        match (ferryDashSpan(jx, jy, yx, yy, cs)) {
            case Some(span) =>
                /* 走过 甲→乙 后虚线改深色加粗。 */
                if (ferryTraversed(this.game.path, f.jiaX, f.jiaY, f.yiX, f.yiY)) {
                    this.context.strokeStyle = Theme.qingDeep
                    this.context.lineWidth = 2.5
                } else {
                    this.context.strokeStyle = Theme.qing
                    this.context.lineWidth = 1.5
                }
                this.context.lineCap = "round"
                this.drawFerryDashSeg(span[0], span[1], span[2], span[3])
                this.drawFerryDashSeg(span[4], span[5], span[6], span[7])
            case None => ()
        }
    }

    func drawFerryRings(cx: Float64, cy: Float64, cs: Float64): Unit {
        this.context.strokeStyle = Theme.qingDeep
        this.context.beginPath()
        this.context.arc(cx, cy, 0.38 * cs, 0.0, 6.28)
        this.context.lineWidth = 1.5
        this.context.stroke()
        this.context.beginPath()
        this.context.arc(cx, cy, 0.30 * cs, 0.0, 6.28)
        this.context.lineWidth = 1.0
        this.context.stroke()
    }

    /* 甲/乙/渡 是汉字,没法用笔画路径;沿用 drawHomeMark 的 fillText + font 写法。
       风险:README 与本文件约 398 行记录过 fillText / font 的 px 在鸿蒙真机上未能
       放大墨像素,甲/乙/渡 字号需真机确认;若过小,后续改 Path2D 字形或叠 Text。
       x/y 传字形中心:基线 = cy + 0.36×字号,左缘 = cx − 0.5×字号。 */
    func drawFerryChar(text: String, cx: Float64, cy: Float64, size: Float64, color: Int64): Unit {
        this.context.fillStyle = color
        this.context.font = "normal ${ferryFontPx(size)}px serif"
        this.context.fillText(text, cx - size * 0.5, cy + size * 0.36)
    }

    /* 一段虚线:2vp 实 / 7vp 空(抄 board_mech.cj dashSub 的步进 2.0 / 9.0)。 */
    func drawFerryDashSeg(ax: Float64, ay: Float64, bx: Float64, by: Float64): Unit {
        let dx = bx - ax
        let dy = by - ay
        let l = sqrt(dx * dx + dy * dy)
        if (l <= 0.0) {
            return
        }
        let ux = dx / l
        let uy = dy / l
        var t: Float64 = 0.0
        while (t < l) {
            let t2 = if (t + 2.0 < l) { t + 2.0 } else { l }
            this.context.beginPath()
            this.context.moveTo(ax + ux * t, ay + uy * t)
            this.context.lineTo(ax + ux * t2, ay + uy * t2)
            this.context.stroke()
            t = t + 9.0
        }
    }

    /* 渡口 甲→乙 是非相邻格:path 折线跳过这一段(不画成穿过中间格的普通实线),
       由上面的渡口虚线/加粗线表示。无渡口关 ferry 为 None,恒 false。 */
    func isFerryJump(a: Cell, b: Cell): Bool {
        match (this.game.level.ferry) {
            case Some(f) =>
                return a.x == f.jiaX && a.y == f.jiaY && b.x == f.yiX && b.y == f.yiY
            case None =>
                return false
        }
    }

    func drawHomeMark(): Unit {
        this.markContext.clearRect(0.0, 0.0, 400.0, 140.0)
        this.markContext.globalAlpha = 0.18
        this.markContext.strokeStyle = Theme.paperLine
        this.markContext.lineWidth = Theme.hairline
        this.markContext.beginPath()
        this.markContext.moveTo(40.0, 24.0)
        this.markContext.lineTo(130.0, 56.0)
        this.markContext.lineTo(78.0, 96.0)
        this.markContext.lineTo(200.0, 118.0)
        this.markContext.stroke()
        this.markContext.fillStyle = Theme.inkMuted
        this.markContext.font = "normal 12px sans-serif"
        this.markContext.fillText("涿郡", 28.0, 20.0)
        this.markContext.fillText("平原", 126.0, 52.0)
        this.markContext.fillText("安喜", 64.0, 108.0)
        this.markContext.fillText("郡治", 190.0, 124.0)
        this.markContext.globalAlpha = 1.0
    }

    func drawBoard(): Unit {
        let layout = this.currentLayout()
        let cols = layout.cols
        let rows = layout.rows
        let cs = layout.cellSize
        let bw = Float64(cols) * cs
        let bh = Float64(rows) * cs
        this.context.clearRect(0.0, 0.0, bw + 8.0, bh + 8.0)

        var y: Int64 = 0
        while (y < rows) {
            var x: Int64 = 0
            while (x < cols) {
                let cell = Cell(x, y)
                if (this.game.path.contains(cell)) {
                    this.context.fillStyle = Theme.paperShade
                } else {
                    this.context.fillStyle = Theme.whitePaper
                }
                this.context.fillRect(Float64(x) * cs, Float64(y) * cs, cs, cs)
                x = x + 1
            }
            y = y + 1
        }

        this.context.lineWidth = Theme.hairline
        this.context.strokeStyle = Theme.paperLine
        var gx: Int64 = 0
        while (gx <= cols) {
            let px = Float64(gx) * cs
            this.context.beginPath()
            this.context.moveTo(px, 0.0)
            this.context.lineTo(px, bh)
            this.context.stroke()
            gx = gx + 1
        }
        var gy: Int64 = 0
        while (gy <= rows) {
            let py = Float64(gy) * cs
            this.context.beginPath()
            this.context.moveTo(0.0, py)
            this.context.lineTo(bw, py)
            this.context.stroke()
            gy = gy + 1
        }

        this.context.lineWidth = 3.0
        this.context.strokeStyle = Theme.ink
        for (wall in this.game.level.walls) {
            var ax = wall.x1
            var ay = wall.y1
            var bx = wall.x2
            var by = wall.y2
            if (ay == by && ax + 1 == bx) {
                let px = Float64(bx) * cs
                this.context.beginPath()
                this.context.moveTo(px, Float64(ay) * cs + 4.0)
                this.context.lineTo(px, Float64(ay + 1) * cs - 4.0)
                this.context.stroke()
            } else if (ay == by && bx + 1 == ax) {
                let px = Float64(ax) * cs
                this.context.beginPath()
                this.context.moveTo(px, Float64(ay) * cs + 4.0)
                this.context.lineTo(px, Float64(ay + 1) * cs - 4.0)
                this.context.stroke()
            } else if (ax == bx && ay + 1 == by) {
                let py = Float64(by) * cs
                this.context.beginPath()
                this.context.moveTo(Float64(ax) * cs + 4.0, py)
                this.context.lineTo(Float64(ax + 1) * cs - 4.0, py)
                this.context.stroke()
            } else if (ax == bx && by + 1 == ay) {
                let py = Float64(ay) * cs
                this.context.beginPath()
                this.context.moveTo(Float64(ax) * cs + 4.0, py)
                this.context.lineTo(Float64(ax + 1) * cs - 4.0, py)
                this.context.stroke()
            }
        }

        this.context.fillStyle = Theme.inkMuted
        this.context.font = "normal 11px serif"
        for (pe in this.game.level.parityEdges) {
            let mx = (Float64(pe.x1) + Float64(pe.x2) + 1.0) * cs * 0.5
            let my = (Float64(pe.y1) + Float64(pe.y2) + 1.0) * cs * 0.5
            let label = if (pe.requireOdd) { "奇" } else { "偶" }
            this.context.fillText(label, mx - 5.5, my + 4.0)
        }

        if (this.game.path.size() >= 2) {
            this.context.lineWidth = Theme.pathStroke
            this.context.strokeStyle = Theme.path
            this.context.lineCap = "round"
            this.context.lineJoin = "round"
            this.context.beginPath()
            let first = this.game.path.at(0)
            this.context.moveTo((Float64(first.x) + 0.5) * cs, (Float64(first.y) + 0.5) * cs)
            var i: Int64 = 1
            while (i < this.game.path.size()) {
                let cell = this.game.path.at(i)
                let prev = this.game.path.at(i - 1)
                let px = (Float64(cell.x) + 0.5) * cs
                let py = (Float64(cell.y) + 0.5) * cs
                /* 渡口 甲→乙 是非相邻格:这一段交给渡口虚线/加粗线,不画成
                   穿过中间格的普通实线(CJMP buildBoardRoute 也只画相邻段)。
                   无渡口关 isFerryJump 恒 false,折线与改动前逐点一致。 */
                if (this.isFerryJump(prev, cell)) {
                    this.context.moveTo(px, py)
                } else {
                    this.context.lineTo(px, py)
                }
                i = i + 1
            }
            this.context.stroke()
        }

        if (this.game.path.size() >= 1) {
            let last = this.game.path.at(this.game.path.size() - 1)
            let hx = (Float64(last.x) + 0.5) * cs
            let hy = (Float64(last.y) + 0.5) * cs
            this.context.beginPath()
            this.context.arc(hx, hy, 6.0, 0.0, 6.28)
            this.context.fillStyle = Theme.whitePaper
            this.context.fill()
            this.context.lineWidth = Theme.hairline
            this.context.strokeStyle = Theme.ink
            this.context.stroke()
        }

        /* Scale circle + digit with cell (cs / 48). Tutorial 48 →
           diameter 40, Path2D glyph 0.60 * 40 = 24vp. */
        let r = Theme.stationD * cs / 48.0 / 2.0
        var glyphH: Float64 = Theme.stationD * cs / 48.0 * 0.60
        if (glyphH < Float64(Theme.stationNumberMin)) {
            glyphH = Float64(Theme.stationNumberMin)
        }
        for (wp in this.game.level.waypoints) {
            let cx = (Float64(wp.x) + 0.5) * cs
            let cy = (Float64(wp.y) + 0.5) * cs
            let st = this.stationState(wp.n)
            if (st == 2) {
                this.context.beginPath()
                this.context.arc(cx, cy, r, 0.0, 6.28)
                this.context.fillStyle = Theme.qing
                this.context.fill()
                this.context.fillStyle = Theme.whitePaper
                this.context.strokeStyle = Theme.whitePaper
                this.drawStationNumber(wp.n, cx, cy, glyphH)
            } else {
                this.context.beginPath()
                this.context.arc(cx, cy, r, 0.0, 6.28)
                this.context.fillStyle = Theme.whitePaper
                this.context.fill()
                this.context.lineWidth = Theme.hairline
                this.context.strokeStyle = Theme.ink
                this.context.stroke()
                if (st == 1) {
                    this.context.beginPath()
                    this.context.arc(cx, cy, r + 3.0, 0.0, 6.28)
                    this.context.strokeStyle = Theme.gold
                    this.context.lineWidth = Theme.hairline
                    this.context.stroke()
                    this.context.fillStyle = Theme.gold
                    this.context.font = "normal 11px sans-serif"
                    this.context.fillText("下一驿", cx, cy + r + 12.0)
                }
                this.context.fillStyle = Theme.ink
                this.context.strokeStyle = Theme.ink
                this.drawStationNumber(wp.n, cx, cy, glyphH)
            }
        }

        /* 渡口标记:只在这关有 ferry 时进这段;无渡口关下面一次绘制调用都不发生,
           画面与改动前一致。 */
        match (this.game.level.ferry) {
            case Some(f) =>
                this.drawFerry(f, cs)
            case None => ()
        }
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
                            .fontFamily(Theme.serif)
                        Text("防")
                            .fontSize(14)
                            .fontColor(Theme.whitePaper)
                            .fontFamily(Theme.serif)
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
                        .fontFamily(Theme.serif)
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
                    .fontFamily(Theme.serif)
                    .fontWeight(FontWeight.Bold)
                    .margin(top: 8)
                Divider()
                    .strokeWidth(1)
                    .color(Theme.gold)
                    .width(168)
                    .margin(top: 6, bottom: 8)
                Text("传书过驿")
                    .fontSize(14)
                    .fontColor(Theme.inkMuted)
                    .fontFamily(Theme.sans)
                Canvas(this.markContext)
                    .width(100.percent)
                    .height(140)
                    .onReady({
                        =>
                        this.drawHomeMark()
                    })
                Blank()
                Button("开始传书")
                    .width(100.percent)
                    .height(Theme.primaryH)
                    .backgroundColor(Theme.qingDeep)
                    .fontColor(Theme.whitePaper)
                    .fontSize(18)
                    .fontFamily(Theme.sans)
                    .onClick({event => this.startPlay()})
                Row {
                    Text("章节")
                        .fontSize(18)
                        .fontColor(Theme.ink)
                        .fontFamily(Theme.sans)
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
                    .fontFamily(Theme.sans)
                    .margin(top: 16, bottom: 12)
                    .onClick({event => this.screen = 3})
            } else if (this.screen == 3) {
                Stack {
                    Row {
                        Text("〈")
                            .fontSize(22)
                            .fontColor(Theme.ink)
                            .fontFamily(Theme.sans)
                            .onClick({event => this.screen = 0})
                        Blank()
                    }
                    .width(100.percent)
                    .height(Theme.topBar)
                    Text("驿程")
                        .fontSize(20)
                        .fontColor(Theme.ink)
                        .fontFamily(Theme.serif)
                }
                .width(100.percent)
                .height(Theme.topBar)
                Divider()
                    .strokeWidth(1)
                    .color(Theme.paperLine)
                    .width(100.percent)
                Scroll {
                    Column(space: 10) {
                        ForEach(
                            LevelCatalog.all(),
                            itemGeneratorFunc: {item: LevelDef, index: Int64 =>
                                Row {
                                    if (index < this.cleared) {
                                        Text("通")
                                            .fontSize(14)
                                            .fontColor(Theme.success)
                                            .fontFamily(Theme.serif)
                                            .width(36)
                                            .height(36)
                                            .border(width: 1, color: Theme.success)
                                            .borderRadius(18)
                                            .textAlign(TextAlign.Center)
                                        Text(item.name)
                                            .fontSize(18)
                                            .fontColor(Theme.ink)
                                            .fontFamily(Theme.serif)
                                            .margin(left: 12)
                                        Blank()
                                        Text("已通")
                                            .fontSize(14)
                                            .fontColor(Theme.success)
                                            .fontFamily(Theme.sans)
                                    } else if (index == this.cleared) {
                                        Text("${index + 1}")
                                            .fontSize(16)
                                            .fontColor(Theme.whitePaper)
                                            .fontFamily(Theme.serif)
                                            .width(36)
                                            .height(36)
                                            .backgroundColor(Theme.ink)
                                            .borderRadius(18)
                                            .textAlign(TextAlign.Center)
                                        Text(item.name)
                                            .fontSize(18)
                                            .fontColor(Theme.ink)
                                            .fontFamily(Theme.serif)
                                            .fontWeight(FontWeight.Bold)
                                            .margin(left: 12)
                                        Blank()
                                        Text("当前")
                                            .fontSize(14)
                                            .fontColor(Theme.ink)
                                            .fontFamily(Theme.sans)
                                    } else {
                                        Text("${index + 1}")
                                            .fontSize(16)
                                            .fontColor(Theme.locked)
                                            .fontFamily(Theme.serif)
                                            .width(36)
                                            .height(36)
                                            .border(width: 1, color: Theme.locked)
                                            .borderRadius(18)
                                            .textAlign(TextAlign.Center)
                                        Text(item.name)
                                            .fontSize(18)
                                            .fontColor(Theme.locked)
                                            .fontFamily(Theme.serif)
                                            .margin(left: 12)
                                        Blank()
                                        Text("锁")
                                            .fontSize(14)
                                            .fontColor(Theme.locked)
                                            .fontFamily(Theme.sans)
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
                    .fontSize(13)
                    .fontColor(Theme.inkMuted)
                    .fontFamily(Theme.sans)
                    .margin(top: 12, bottom: 8)
                    .width(100.percent)
            } else if (this.screen == 4) {
                Stack {
                    Row {
                        Text("〈")
                            .fontSize(22)
                            .fontColor(Theme.ink)
                            .fontFamily(Theme.sans)
                            .onClick({event => this.screen = 0})
                        Blank()
                    }
                    .width(100.percent)
                    .height(Theme.topBar)
                    Text("章节")
                        .fontSize(20)
                        .fontColor(Theme.ink)
                        .fontFamily(Theme.serif)
                }
                .width(100.percent)
                .height(Theme.topBar)
                Text("选章入驿 · 开章可入 · 灰章未启")
                    .fontSize(12)
                    .fontColor(Theme.inkMuted)
                    .fontFamily(Theme.sans)
                    .margin(top: 2, bottom: 8)
                    .width(100.percent)
                Scroll {
                    Column(space: 8) {
                        ForEach(
                            ChapterCatalog.all(),
                            itemGeneratorFunc: {item: ChapterDef, index: Int64 =>
                                Column {
                                if (item.id == 4) {
                                    Image(@r(app.media.card_05_touyuan_v91))
                                        .width(100.percent)
                                        .height(Theme.chapterSkinCardH)
                                        .objectFit(ImageFit.Contain)
                                } else if (item.id == 5) {
                                    Image(@r(app.media.card_06_jingzhou_v91))
                                        .width(100.percent)
                                        .height(Theme.chapterSkinCardH)
                                        .objectFit(ImageFit.Contain)
                                } else if (item.id == 6) {
                                    Image(@r(app.media.card_07_chibi_v91))
                                        .width(100.percent)
                                        .height(Theme.chapterSkinCardH)
                                        .objectFit(ImageFit.Contain)
                                } else if (item.id == 7) {
                                    Image(@r(app.media.card_08_rushu_v91))
                                        .width(100.percent)
                                        .height(Theme.chapterSkinCardH)
                                        .objectFit(ImageFit.Contain)
                                } else if (item.id == 8) {
                                    Image(@r(app.media.card_09_hanzhong_v91))
                                        .width(100.percent)
                                        .height(Theme.chapterSkinCardH)
                                        .objectFit(ImageFit.Contain)
                                } else if (item.id == 9) {
                                    Image(@r(app.media.card_10_beifa_v91))
                                        .width(100.percent)
                                        .height(Theme.chapterSkinCardH)
                                        .objectFit(ImageFit.Contain)
                                }
                                Row(space: 8) {
                                    Row(space: 2) {
                                        if (item.id == 0) {
                                            Image(@r(app.media.bust_p01_cangguan))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                            Image(@r(app.media.flag_p01_han))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(@r(app.media.flag_p02_huang))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(@r(app.media.bust_p02_huangjin))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                        } else if (item.id == 1) {
                                            Image(@r(app.media.bust_p03_gongsun))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                            Image(@r(app.media.flag_p03_gongsun))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(@r(app.media.flag_p04_yuan))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(@r(app.media.bust_p04_yuanshao))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                        } else if (item.id == 2) {
                                            Image(@r(app.media.bust_p05_liubei))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                            Image(@r(app.media.flag_p05_liu))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(@r(app.media.flag_p06_cao))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(@r(app.media.bust_p06_caocao))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                        } else if (item.id == 3) {
                                            Image(@r(app.media.bust_p07_lvbu))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                            Image(@r(app.media.flag_p07_lv))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(@r(app.media.flag_p06_cao))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(@r(app.media.bust_p06_caocao))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                        } else if (item.id == 4) {
                                            Image(@r(app.media.bust_p04_yuanshao))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                            Image(@r(app.media.flag_p04_yuan))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(@r(app.media.flag_p06_cao))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(@r(app.media.bust_p06_caocao))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                        } else if (item.id == 5) {
                                            Image(@r(app.media.bust_p05_liubei))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                            Image(@r(app.media.flag_p05_liu))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(@r(app.media.flag_p06_cao))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(@r(app.media.bust_p06_caocao))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                        } else if (item.id == 6) {
                                            Image(@r(app.media.bust_p08_sunquan))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                            Image(@r(app.media.flag_p08_sun))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(@r(app.media.flag_p06_cao))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(@r(app.media.bust_p06_caocao))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                        } else if (item.id == 7) {
                                            Image(@r(app.media.bust_p05_liubei))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                            Image(@r(app.media.flag_p05_liu))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(@r(app.media.flag_gate_pattern))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(@r(app.media.bust_s01_guanai))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                        } else if (item.id == 8) {
                                            Image(@r(app.media.bust_p09_zhugeliang))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                            Image(@r(app.media.flag_p09_zhuge))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(@r(app.media.flag_p06_cao))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(@r(app.media.bust_p06_caocao))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                        } else {
                                            Image(@r(app.media.bust_p09_zhugeliang))
                                                .width(Theme.bustThumbW)
                                                .height(Theme.bustThumbH)
                                            Image(@r(app.media.flag_p09_zhuge))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(@r(app.media.flag_p10_sima))
                                                .width(Theme.flagThumbW)
                                                .height(Theme.flagThumbH)
                                            Image(@r(app.media.bust_p10_simayi))
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
                                            .fontColor(this.cardMutedColor(this.chapterOpen(item.id)))
                                            .fontFamily(Theme.sans)
                                        Text(item.title)
                                            .fontSize(17)
                                            .fontColor(this.cardTitleColor(this.chapterOpen(item.id)))
                                            .fontFamily(Theme.serif)
                                            .fontWeight(FontWeight.Bold)
                                            .margin(top: 2)
                                        Text(item.subtitle)
                                            .fontSize(11)
                                            .fontColor(this.cardMutedColor(this.chapterOpen(item.id)))
                                            .fontFamily(Theme.sans)
                                            .margin(top: 2)
                                    }
                                    .layoutWeight(1)
                                    .alignItems(HorizontalAlign.Start)
                                    if (this.chapterOpen(item.id)) {
                                        Text("可入")
                                            .fontSize(13)
                                            .fontColor(this.enterInk(index))
                                            .fontFamily(Theme.sans)
                                            .width(48)
                                            .height(28)
                                            .textAlign(TextAlign.Center)
                                            .backgroundColor(this.enterFill(index))
                                            .borderRadius(6)
                                            .border(width: 1, color: Theme.ink)
                                    } else {
                                        Text("未开")
                                            .fontSize(13)
                                            .fontColor(Theme.locked)
                                            .fontFamily(Theme.sans)
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
                    .fontFamily(Theme.sans)
                    .margin(top: 8, bottom: 8)
                    .width(100.percent)
            } else if (this.screen == 5) {
                Stack {
                    Row {
                        Text("〈")
                            .fontSize(22)
                            .fontColor(Theme.ink)
                            .fontFamily(Theme.sans)
                            .onClick({event => this.screen = 4})
                        Blank()
                    }
                    .width(100.percent)
                    .height(Theme.topBar)
                    Text(this.chapterListTitle())
                        .fontSize(20)
                        .fontColor(Theme.ink)
                        .fontFamily(Theme.serif)
                }
                .width(100.percent)
                .height(Theme.topBar)
                Text(this.currentChapter().listSubtitle)
                    .fontSize(12)
                    .fontColor(Theme.inkMuted)
                    .fontFamily(Theme.sans)
                    .margin(bottom: 8)
                    .width(100.percent)
                Scroll {
                    Column(space: 8) {
                        ForEach(
                            ChapterCatalog.levelsOf(this.chapterIndex),
                            itemGeneratorFunc: {item: LevelDef, index: Int64 =>
                                Row {
                                    if (item.id < this.cleared) {
                                        Text("通")
                                            .fontSize(14)
                                            .fontColor(Theme.success)
                                            .fontFamily(Theme.serif)
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
                                                    .fontFamily(Theme.serif)
                                                if (ChapterCatalog.isDessert(item.id)) {
                                                    Text("点心")
                                                        .fontSize(10)
                                                        .fontColor(Theme.inkMuted)
                                                        .fontFamily(Theme.sans)
                                                        .padding(left: 4, right: 4)
                                                        .border(width: 1, color: Theme.paperLine)
                                                        .borderRadius(4)
                                                }
                                            }
                                            Text("${item.cols}×${item.rows}")
                                                .fontSize(12)
                                                .fontColor(Theme.inkMuted)
                                                .fontFamily(Theme.sans)
                                        }
                                        .margin(left: 10)
                                        .alignItems(HorizontalAlign.Start)
                                        Blank()
                                        Text("已通")
                                            .fontSize(13)
                                            .fontColor(Theme.success)
                                            .fontFamily(Theme.sans)
                                    } else if (item.id == this.cleared) {
                                        Text("${index + 1}")
                                            .fontSize(14)
                                            .fontColor(Theme.whitePaper)
                                            .fontFamily(Theme.serif)
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
                                                    .fontFamily(Theme.serif)
                                                    .fontWeight(FontWeight.Bold)
                                                if (ChapterCatalog.isDessert(item.id)) {
                                                    Text("点心")
                                                        .fontSize(10)
                                                        .fontColor(Theme.ink)
                                                        .fontFamily(Theme.sans)
                                                        .padding(left: 4, right: 4)
                                                        .border(width: 1, color: Theme.ink)
                                                        .borderRadius(4)
                                                }
                                            }
                                            Text("${item.cols}×${item.rows}")
                                                .fontSize(12)
                                                .fontColor(Theme.inkMuted)
                                                .fontFamily(Theme.sans)
                                        }
                                        .margin(left: 10)
                                        .alignItems(HorizontalAlign.Start)
                                        Blank()
                                        Text("当前")
                                            .fontSize(13)
                                            .fontColor(Theme.ink)
                                            .fontFamily(Theme.sans)
                                    } else {
                                        Text("${index + 1}")
                                            .fontSize(14)
                                            .fontColor(Theme.locked)
                                            .fontFamily(Theme.serif)
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
                                                    .fontFamily(Theme.serif)
                                                if (ChapterCatalog.isDessert(item.id)) {
                                                    Text("点心")
                                                        .fontSize(10)
                                                        .fontColor(Theme.locked)
                                                        .fontFamily(Theme.sans)
                                                        .padding(left: 4, right: 4)
                                                        .border(width: 1, color: Theme.locked)
                                                        .borderRadius(4)
                                                }
                                            }
                                            Text("${item.cols}×${item.rows}")
                                                .fontSize(12)
                                                .fontColor(Theme.locked)
                                                .fontFamily(Theme.sans)
                                        }
                                        .margin(left: 10)
                                        .alignItems(HorizontalAlign.Start)
                                        Blank()
                                        Text("锁")
                                            .fontSize(13)
                                            .fontColor(Theme.locked)
                                            .fontFamily(Theme.sans)
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
                }
                .width(100.percent)
                .layoutWeight(1)
                /* 共10驿 — sizes stay ${item.cols}×${item.rows} from levels.json */
                Text(this.chapterListFooter())
                    .fontSize(12)
                    .fontColor(Theme.inkMuted)
                    .fontFamily(Theme.sans)
                    .margin(top: 8, bottom: 8)
                    .width(100.percent)
            } else if (this.screen == 6) {
                /* Skin-only preview for locked 05–10. No boards, no gameplay. */
                Stack {
                    Row {
                        Text("〈")
                            .fontSize(22)
                            .fontColor(Theme.ink)
                            .fontFamily(Theme.sans)
                            .onClick({event => this.screen = 4})
                        Blank()
                    }
                    .width(100.percent)
                    .height(Theme.topBar)
                    .padding(left: Theme.inset, right: Theme.inset)
                    Text(this.currentChapter().title)
                        .fontSize(20)
                        .fontColor(Theme.ink)
                        .fontFamily(Theme.serif)
                }
                .width(100.percent)
                .height(Theme.topBar)
                Text(this.currentChapter().listSubtitle)
                    .fontSize(12)
                    .fontColor(Theme.inkMuted)
                    .fontFamily(Theme.sans)
                    .padding(left: Theme.inset, right: Theme.inset)
                    .margin(bottom: 4)
                    .width(100.percent)
                if (this.chapterIndex == 4) {
                    Image(@r(app.media.skin_05_touyuan_v91))
                        .width(100.percent)
                        .layoutWeight(1)
                        .objectFit(ImageFit.Contain)
                } else if (this.chapterIndex == 5) {
                    Image(@r(app.media.skin_06_jingzhou_v91))
                        .width(100.percent)
                        .layoutWeight(1)
                        .objectFit(ImageFit.Contain)
                } else if (this.chapterIndex == 6) {
                    Image(@r(app.media.skin_07_chibi_v91))
                        .width(100.percent)
                        .layoutWeight(1)
                        .objectFit(ImageFit.Contain)
                } else if (this.chapterIndex == 7) {
                    Image(@r(app.media.skin_08_rushu_v91))
                        .width(100.percent)
                        .layoutWeight(1)
                        .objectFit(ImageFit.Contain)
                } else if (this.chapterIndex == 8) {
                    Image(@r(app.media.skin_09_hanzhong_v91))
                        .width(100.percent)
                        .layoutWeight(1)
                        .objectFit(ImageFit.Contain)
                } else {
                    Image(@r(app.media.skin_10_beifa_v91))
                        .width(100.percent)
                        .layoutWeight(1)
                        .objectFit(ImageFit.Contain)
                }
            } else if (this.screen == 2) {
                Blank()
                Column {
                    Text("通关")
                        .fontSize(14)
                        .fontColor(Theme.inkMuted)
                        .fontFamily(Theme.sans)
                        .margin(bottom: 8)
                    Text(this.roadTitle())
                        .fontSize(26)
                        .fontColor(Theme.ink)
                        .fontFamily(Theme.serif)
                        .fontWeight(FontWeight.Bold)
                        .margin(bottom: 16)
                    Row {
                        Column {
                            Text("驿道已通")
                                .fontSize(14)
                                .fontColor(Theme.inkMuted)
                                .fontFamily(Theme.sans)
                            Text("文书递达本驿")
                                .fontSize(14)
                                .fontColor(Theme.inkMuted)
                                .fontFamily(Theme.sans)
                                .margin(top: 4)
                        }
                        .alignItems(HorizontalAlign.Start)
                        Blank()
                        /* Win seal copy: 文书到 (vermillion only). */
                        Column {
                            Text("文")
                                .fontSize(13)
                                .fontColor(Theme.whitePaper)
                                .fontFamily(Theme.serif)
                            Text("书")
                                .fontSize(13)
                                .fontColor(Theme.whitePaper)
                                .fontFamily(Theme.serif)
                            Text("到")
                                .fontSize(13)
                                .fontColor(Theme.whitePaper)
                                .fontFamily(Theme.serif)
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
                        .fontSize(18)
                        .fontFamily(Theme.sans)
                        .onClick({event => this.nextLevel()})
                }
                .width(86.percent)
                .padding(20)
                .backgroundColor(Theme.whitePaper)
                .borderRadius(12)
                Blank()
            } else if (this.screen == 1) {
                Stack {
                    Row {
                        Text("〈")
                            .fontSize(22)
                            .fontColor(Theme.ink)
                            .fontFamily(Theme.sans)
                            .onClick({event => this.leaveBoard()})
                        Blank()
                    }
                    .width(100.percent)
                    .height(40)
                    Text(this.roadTitle())
                        .fontSize(18)
                        .fontColor(Theme.ink)
                        .fontFamily(Theme.serif)
                }
                .width(100.percent)
                .height(40)
                .padding(left: Theme.inset, right: Theme.inset)
                Text(this.boardSubtitle())
                    .fontSize(12)
                    .fontColor(Theme.inkMuted)
                    .fontFamily(Theme.sans)
                    .padding(left: Theme.inset, right: Theme.inset)
                    .margin(bottom: 4)
                    .width(100.percent)
                if (this.hasParityBoard() || this.game.level.stepLimit > 0) {
                    Row(space: 8) {
                        if (this.hasParityBoard()) {
                            Text(this.stepChipLabel())
                                .fontSize(15)
                                .fontWeight(FontWeight.Bold)
                                .fontColor(Theme.ink)
                                .fontFamily(Theme.serif)
                                .padding(left: 12, right: 12)
                                .height(28)
                                .borderRadius(4)
                                .border(width: 1, color: this.stepChipBorder())
                                .backgroundColor(Theme.whitePaper)
                        }
                        if (this.game.level.stepLimit > 0) {
                            Text("余步 · ${this.remainingSteps()}")
                                .fontSize(15)
                                .fontWeight(FontWeight.Bold)
                                .fontColor(Theme.ink)
                                .fontFamily(Theme.serif)
                                .padding(left: 12, right: 12)
                                .height(28)
                                .borderRadius(4)
                                .border(width: 1, color: Theme.paperLine)
                                .backgroundColor(Theme.whitePaper)
                        }
                    }
                    .justifyContent(FlexAlign.Center)
                    .width(100.percent)
                    .margin(bottom: 4)
                }
                if (this.parityRejectText.size > 0) {
                    Row {
                        Text(this.parityRejectText)
                            .fontSize(14)
                            .fontFamily(Theme.serif)
                            .fontColor(Theme.vermillion)
                            .padding(left: 14, right: 14)
                            .height(28)
                            .borderRadius(4)
                            .border(width: 1, color: Theme.vermillion)
                            .backgroundColor(Theme.whitePaper)
                    }
                    .justifyContent(FlexAlign.Center)
                    .width(100.percent)
                    .margin(bottom: 4)
                }
                /* BANDS.md composite: 涿郡 0–9 / 平原 10–19.
                   Full-width 360×100 vp; Theme.bandClear keeps bust/flags
                   out of the Canvas grid (band.bottom ≤ board.top − 30px). */
                Column {
                    if (this.levelIndex < 10) {
                        Image(@r(app.media.band_zhuojun_v91))
                            .width(100.percent)
                            .height(Theme.bandH)
                    } else {
                        Image(@r(app.media.band_pingyuan_v91))
                            .width(100.percent)
                            .height(Theme.bandH)
                    }
                }
                .width(100.percent)
                .height(Theme.bandH)
                .margin(bottom: Theme.bandClear)
                Scroll {
                    Column {
                        Canvas(this.context)
                            .width(this.boardW())
                            .height(this.boardH())
                            .backgroundColor(Theme.paper)
                            .onReady({
                                =>
                                this.drawBoard()
                            })
                            .onTouch({event =>
                                match (event.eventType) {
                                    case TouchType.Down => this.handleDrag(event)
                                    case TouchType.Move => this.handleDrag(event)
                                    case _ => ()
                                }
                            })
                    }
                    .width(100.percent)
                    .alignItems(HorizontalAlign.Center)
                }
                .width(100.percent)
                .layoutWeight(1)
                Text(this.chromeLine())
                    .fontSize(11)
                    .fontColor(Theme.inkMuted)
                    .fontFamily(Theme.sans)
                    .padding(left: Theme.inset, right: Theme.inset)
                    .margin(top: 4, bottom: 4)
                    .width(100.percent)
                Divider()
                    .strokeWidth(1)
                    .color(Theme.paperLine)
                    .width(100.percent)
                Row(space: 12) {
                    Row(space: 8) {
                        Canvas(this.undoContext)
                            .width(Theme.iconVp)
                            .height(Theme.iconVp)
                            .onReady({
                                =>
                                this.drawUndoIcon()
                            })
                        Text("撤销")
                            .fontSize(16)
                            .fontColor(Theme.ink)
                            .fontFamily(Theme.sans)
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
                        Canvas(this.redrawContext)
                            .width(Theme.iconVp)
                            .height(Theme.iconVp)
                            .onReady({
                                =>
                                this.drawRedrawIcon()
                            })
                        Text("重绘驿道")
                            .fontSize(16)
                            .fontColor(Theme.ink)
                            .fontFamily(Theme.sans)
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
        }
        .width(100.percent)
        .height(100.percent)
        .padding(left: this.playInset(), right: this.playInset())
        .backgroundColor(this.playPaper())
        .alignItems(HorizontalAlign.Center)
    }
}

/* ---- 渡口纯计算(不依赖 ohos/ArkUI,可在 cjpm 工程编译验证:
   /workspace/cjmp-smoke/ferry6/y2_check/) ---- */

/* Canvas font 只吃整数 px;0.30c / 0.24c / 0.20c 随格边 cs 缩放后四舍五入。 */
func ferryFontPx(size: Float64): Int64 {
    return Int64(size + 0.5)
}

/* 甲乙圆环之间虚线的两段(甲侧、乙侧)起止点,扁平数组
   [sx,sy,m1x,m1y, m2x,m2y,ex,ey]:两端各让出环半径 r=0.38c+1,中段留
   g=0.16c 缺口给「渡」字;总长放不下两段虚线时返回 None。
   判定抄 board_mech.cj 的 d 段(L > 2r + 2g)。 */
func ferryDashSpan(jx: Float64, jy: Float64, yx: Float64, yy: Float64, cs: Float64): Option<Array<Float64>> {
    let dx = yx - jx
    let dy = yy - jy
    let l = sqrt(dx * dx + dy * dy)
    if (l <= 0.0) {
        return None
    }
    let ux = dx / l
    let uy = dy / l
    let r = 0.38 * cs + 1.0
    let g = 0.16 * cs
    if (l <= 2.0 * r + 2.0 * g) {
        return None
    }
    let sx = jx + ux * r
    let sy = jy + uy * r
    let ex = yx - ux * r
    let ey = yy - uy * r
    let mx = (sx + ex) * 0.5
    let my = (sy + ey) * 0.5
    return Some([sx, sy, mx - ux * g, my - uy * g, mx + ux * g, my + uy * g, ex, ey])
}

/* 路径走过 甲→乙:path 里甲 的下一格是乙。 */
func ferryTraversed(path: GridPath, jiaX: Int64, jiaY: Int64, yiX: Int64, yiY: Int64): Bool {
    var i: Int64 = 0
    while (i < path.size()) {
        let pc = path.at(i)
        if (pc.x == jiaX && pc.y == jiaY) {
            if (i + 1 < path.size()) {
                let nc = path.at(i + 1)
                if (nc.x == yiX && nc.y == yiY) {
                    return true
                }
            }
            return false
        }
        i = i + 1
    }
    return false
}
