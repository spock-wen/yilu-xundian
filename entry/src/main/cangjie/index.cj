package ohos_app_cangjie_entry

import kit.ArkUI.*
import ohos.arkui.state_macro_manage.*
import ohos_app_cangjie_entry.engine.{Cell, GridLayout, touchToCell}
import ohos_app_cangjie_entry.game.{LevelDef, PatrolGame}

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
    var game: PatrolGame = PatrolGame(LevelCatalog.byIndex(0))

    @State var screen: Int64 = 0
    @State var levelIndex: Int64 = 0
    @State var tick: Int64 = 0
    @State var cleared: Int64 = 0

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
        return "${this.game.level.name}·第 ${this.game.level.maxNumber()} 驿"
    }

    func currentName(): String {
        if (this.cleared >= LevelCatalog.count()) {
            return "已通"
        }
        return LevelCatalog.byIndex(this.cleared).name
    }

    func refresh(): Unit {
        this.tick = this.tick + 1
        this.drawBoard()
    }

    func openLevel(index: Int64): Unit {
        this.levelIndex = index
        this.game.reset(LevelCatalog.byIndex(index))
        this.screen = 1
        this.refresh()
    }

    func startPlay(): Unit {
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
        this.openLevel(index)
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
        if (this.game.undo()) {
            this.refresh()
        }
    }

    func doClear(): Unit {
        this.game.clear()
        this.refresh()
    }

    func handleDrag(event: TouchEvent): Unit {
        let px = event.touches[0].x
        let py = event.touches[0].y
        let hit = touchToCell(px, py, this.currentLayout())
        match (hit) {
            case None => ()
            case Some(cell) =>
                if (this.game.tryStep(cell)) {
                    if (this.game.isWin()) {
                        if (this.levelIndex + 1 > this.cleared) {
                            this.cleared = this.levelIndex + 1
                        }
                        this.screen = 2
                    }
                    this.refresh()
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

    func drawHomeMark(): Unit {
        this.markContext.clearRect(0.0, 0.0, 400.0, 260.0)
        this.markContext.globalAlpha = 0.18
        this.markContext.strokeStyle = Theme.paperLine
        this.markContext.lineWidth = Theme.hairline
        this.markContext.beginPath()
        this.markContext.moveTo(48.0, 36.0)
        this.markContext.lineTo(150.0, 88.0)
        this.markContext.lineTo(86.0, 150.0)
        this.markContext.lineTo(220.0, 176.0)
        this.markContext.stroke()
        this.markContext.fillStyle = Theme.inkMuted
        this.markContext.font = "normal 12px sans-serif"
        this.markContext.fillText("长安", 36.0, 30.0)
        this.markContext.fillText("洛阳", 146.0, 82.0)
        this.markContext.fillText("凉州", 72.0, 168.0)
        this.markContext.fillText("敦煌", 210.0, 190.0)
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
                this.context.lineTo((Float64(cell.x) + 0.5) * cs, (Float64(cell.y) + 0.5) * cs)
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

        let r = Theme.stationD / 2.0
        this.context.font = "normal 18px serif"
        this.context.textAlign = "center"
        this.context.textBaseline = "middle"
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
                this.context.fillText("${wp.n}", cx, cy)
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
                    this.context.font = "normal 18px serif"
                }
                this.context.fillStyle = Theme.ink
                this.context.fillText("${wp.n}", cx, cy)
            }
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
                    .height(200)
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
            } else {
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
                    Text(this.roadTitle())
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
                Divider()
                    .strokeWidth(1)
                    .color(Theme.paperLine)
                    .width(100.percent)
                Row(space: 12) {
                    Button("撤销")
                        .layoutWeight(1)
                        .height(Theme.undoH)
                        .backgroundColor(Theme.whitePaper)
                        .fontColor(Theme.ink)
                        .fontSize(16)
                        .fontFamily(Theme.sans)
                        .border(width: 1, color: Theme.ink)
                        .onClick({event => this.doUndo()})
                    Button("重绘驿道")
                        .layoutWeight(1)
                        .height(Theme.undoH)
                        .backgroundColor(Theme.whitePaper)
                        .fontColor(Theme.ink)
                        .fontSize(16)
                        .fontFamily(Theme.sans)
                        .border(width: 1, color: Theme.ink)
                        .onClick({event => this.doClear()})
                }
                .width(100.percent)
                .height(Theme.bottomBar)
                .alignItems(VerticalAlign.Center)
            }
        }
        .width(100.percent)
        .height(100.percent)
        .padding(left: Theme.inset, right: Theme.inset)
        .backgroundColor(Theme.paper)
        .alignItems(HorizontalAlign.Center)
    }
}
