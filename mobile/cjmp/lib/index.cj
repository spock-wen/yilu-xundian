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
    // A2: back button pressed ripple opacity
    @State var backPressedOpacity: Float64 = 0.0

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
        // M2: parity toast (animateTo removed)
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
        if (this.cleared >= this.levels.size) {
            return "已通"
        }
        return this.levels[this.cleared].name
    }

    func refresh(): Unit {
        this.tick = this.tick + 1
        this.stepFilled = this.game.filled()
    }

    func openLevel(index: Int64): Unit {
        this.levelIndex = index
        this.chapterIndex = ChapterCatalog.chapterIdForLevel(index)
        if (index >= 0 && index < this.levels.size) {
            this.game.reset(this.levels[index])
        }
        this.screen = 1
        this.refresh()
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
                // PLACEHOLDER(M2): home mark route (was Canvas drawHomeMark)
                Column {}
                    .width(100.percent)
                    .height(140)
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
                Text(this.currentChapter().listSubtitle)
                    .fontSize(12)
                    .fontColor(Theme.inkMuted)
                    .fontFamily(this.sansFamily())
                    .margin(bottom: 8)
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
            } else if (this.screen == 1) {
                Stack {
                    Row {
                        // A2: 48vp hit area — in-page back: iOS edge swipe does not pop on Keels 0.2.2
                        this.backButton({ => this.leaveBoard() }, true)
                        Blank()
                    }
                    .width(100.percent)
                    .height(48)
                    Text(this.roadTitle())
                        .fontSize(18)
                        .fontColor(Theme.ink)
                        .fontFamily(this.serifBoldFamily())
                        .fontWeight(FontWeight.Bold)
                }
                .width(100.percent)
                .height(48)
                .padding(left: Theme.inset, right: Theme.inset)
                Text(this.boardSubtitle())
                    .fontSize(12)
                    .fontColor(Theme.inkMuted)
                    .fontFamily(this.sansFamily())
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
                                .fontFamily(this.serifBoldFamily())
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
                                .fontFamily(this.serifBoldFamily())
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
                            .fontFamily(this.serifFamily())
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
                        Image(rawImg("band_zhuojun_v91"))
                            .width(100.percent)
                            .height(Theme.bandH)
                    } else {
                        Image(rawImg("band_pingyuan_v91"))
                            .width(100.percent)
                            .height(Theme.bandH)
                    }
                }
                .width(100.percent)
                .height(Theme.bandH)
                .margin(bottom: Theme.bandClear)
                Scroll {
                    Column {
                        // PLACEHOLDER(M2): board renderer (was Canvas drawBoard + onTouch)
                        Column {
                            Text("棋盘 · M2")
                                .fontSize(14)
                                .fontColor(Theme.inkMuted)
                                .fontFamily(this.sansFamily())
                        }
                        .width(this.boardW())
                        .height(this.boardH())
                        .backgroundColor(Theme.whitePaper)
                        .border(width: 1, color: Theme.paperLine)
                        .justifyContent(FlexAlign.Center)
                        .alignItems(HorizontalAlign.Center)
                    }
                    .width(100.percent)
                    .alignItems(HorizontalAlign.Center)
                }
                .width(100.percent)
                .layoutWeight(1)
                Text(this.chromeLine())
                    .fontSize(11)
                    .lineHeight(15)
                    .fontColor(Theme.inkMuted)
                    .fontFamily(this.sansFamily())
                    .padding(left: Theme.inset, right: Theme.inset)
                    .margin(top: 4, bottom: 4)
                    .width(100.percent)
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
        }
        .width(100.percent)
        .height(100.percent)
        .padding(left: this.playInset(), right: this.playInset())
        .backgroundColor(this.playPaper())
        .alignItems(HorizontalAlign.Center)
    }
}
