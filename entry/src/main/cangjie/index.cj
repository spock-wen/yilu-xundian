package ohos_app_cangjie_entry

import kit.ArkUI.*
import ohos.arkui.state_macro_manage.*
import ohos_app_cangjie_entry.engine.{GridLayout, touchToCell}
import ohos_app_cangjie_entry.game.{LevelDef, PatrolGame}

/*
 * Canvas + onTouch from official docs_cangjie:
 * - arkui-cj/cj-drawing-customization-on-canvas.md
 * - reference/arkui-cj/cj-canvas-drawing-canvasrenderingcontext2d.md
 * - arkui-cj/cj-common-events-touch-screen-event.md
 * Imports: kit.ArkUI.* + ohos.arkui.state_macro_manage.*
 * lineWidth / strokeStyle / fillStyle are properties. Draw after onReady.
 * Touch field is event.eventType (not ArkTS event.type).
 */
@Entry
@Component
class EntryView {
    var settings: RenderingContextSettings = RenderingContextSettings(antialias: true)
    var context: CanvasRenderingContext2D = CanvasRenderingContext2D(this.settings)
    var game: PatrolGame = PatrolGame(LevelCatalog.byIndex(0))

    @State var screen: Int64 = 0
    @State var levelIndex: Int64 = 0
    @State var tick: Int64 = 0
    @State var winTitle: String = ""

    func currentLayout(): GridLayout {
        let cols = this.game.level.cols
        let rows = this.game.level.rows
        let inner = Theme.boardSize - Theme.boardInset * 2.0
        var side = cols
        if (rows > side) {
            side = rows
        }
        let cell = inner / Float64(side)
        return GridLayout(Theme.boardInset, Theme.boardInset, cell, cols, rows)
    }

    func numberFont(): Int64 {
        let cols = this.game.level.cols
        if (cols <= 3) {
            return 36
        }
        if (cols <= 4) {
            return 28
        }
        return 22
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
                        this.winTitle = this.game.level.name
                        this.screen = 2
                    }
                    this.refresh()
                }
        }
    }

    func drawBoard(): Unit {
        this.context.clearRect(0.0, 0.0, 3000.0, 3000.0)
        let layout = this.currentLayout()
        let cols = layout.cols
        let rows = layout.rows
        let ox = layout.originX
        let oy = layout.originY
        let cs = layout.cellSize

        this.context.fillStyle = Theme.paper
        this.context.fillRect(ox, oy, Float64(cols) * cs, Float64(rows) * cs)

        this.context.lineWidth = 2.0
        this.context.strokeStyle = Theme.gridLine
        var x: Int64 = 0
        while (x <= cols) {
            let px = ox + Float64(x) * cs
            this.context.beginPath()
            this.context.moveTo(px, oy)
            this.context.lineTo(px, oy + Float64(rows) * cs)
            this.context.stroke()
            x = x + 1
        }
        var y: Int64 = 0
        while (y <= rows) {
            let py = oy + Float64(y) * cs
            this.context.beginPath()
            this.context.moveTo(ox, py)
            this.context.lineTo(ox + Float64(cols) * cs, py)
            this.context.stroke()
            y = y + 1
        }

        this.context.lineWidth = 6.0
        this.context.strokeStyle = Theme.wallInk
        for (wall in this.game.level.walls) {
            var ax = wall.x1
            var ay = wall.y1
            var bx = wall.x2
            var by = wall.y2
            if (ay == by && ax + 1 == bx) {
                let px = ox + Float64(bx) * cs
                this.context.beginPath()
                this.context.moveTo(px, oy + Float64(ay) * cs + 4.0)
                this.context.lineTo(px, oy + Float64(ay + 1) * cs - 4.0)
                this.context.stroke()
            } else if (ay == by && bx + 1 == ax) {
                let px = ox + Float64(ax) * cs
                this.context.beginPath()
                this.context.moveTo(px, oy + Float64(ay) * cs + 4.0)
                this.context.lineTo(px, oy + Float64(ay + 1) * cs - 4.0)
                this.context.stroke()
            } else if (ax == bx && ay + 1 == by) {
                let py = oy + Float64(by) * cs
                this.context.beginPath()
                this.context.moveTo(ox + Float64(ax) * cs + 4.0, py)
                this.context.lineTo(ox + Float64(ax + 1) * cs - 4.0, py)
                this.context.stroke()
            } else if (ax == bx && by + 1 == ay) {
                let py = oy + Float64(ay) * cs
                this.context.beginPath()
                this.context.moveTo(ox + Float64(ax) * cs + 4.0, py)
                this.context.lineTo(ox + Float64(ax + 1) * cs - 4.0, py)
                this.context.stroke()
            }
        }

        if (this.game.path.size() >= 2) {
            this.context.lineWidth = 8.0
            this.context.strokeStyle = Theme.pathInk
            this.context.beginPath()
            let first = this.game.path.at(0)
            this.context.moveTo(ox + (Float64(first.x) + 0.5) * cs, oy + (Float64(first.y) + 0.5) * cs)
            var i: Int64 = 1
            while (i < this.game.path.size()) {
                let cell = this.game.path.at(i)
                this.context.lineTo(ox + (Float64(cell.x) + 0.5) * cs, oy + (Float64(cell.y) + 0.5) * cs)
                i = i + 1
            }
            this.context.stroke()
        }

        let fs = this.numberFont()
        this.context.font = "normal bolder ${fs}px sans-serif"
        for (wp in this.game.level.waypoints) {
            let cx = ox + (Float64(wp.x) + 0.5) * cs
            let cy = oy + (Float64(wp.y) + 0.5) * cs
            let r = cs * 0.32
            this.context.beginPath()
            this.context.arc(cx, cy, r, 0.0, 6.28)
            this.context.fillStyle = Theme.stationFill
            this.context.fill()
            this.context.lineWidth = 3.0
            this.context.strokeStyle = Theme.ink
            this.context.stroke()
            this.context.fillStyle = Theme.ink
            this.context.fillText("${wp.n}", cx - Float64(fs) * 0.28, cy + Float64(fs) * 0.34)
        }
    }

    func build() {
        Column {
            if (this.screen == 0) {
                Text("驿路巡点")
                    .fontSize(28)
                    .fontColor(Theme.ink)
                    .fontWeight(FontWeight.Bold)
                    .margin(top: 12, bottom: 4)
                Text("按号巡驿，走遍每一格。正交四向，不可越墙。")
                    .fontSize(14)
                    .fontColor(Theme.muted)
                    .margin(bottom: 12)
                Scroll {
                    Column(10) {
                        ForEach(
                            LevelCatalog.all(),
                            itemGeneratorFunc: {item: LevelDef, index: Int64 =>
                                Button("${item.name}    ${item.cols}×${item.rows}")
                                    .width(100.percent)
                                    .height(Theme.buttonHeight)
                                    .backgroundColor(Theme.buttonFill)
                                    .fontColor(Theme.buttonText)
                                    .fontSize(18)
                                    .onClick({event => this.openLevel(index)})
                            }
                        )
                    }
                    .width(100.percent)
                }
                .width(100.percent)
                .height(70.percent)
            } else if (this.screen == 2) {
                Text("文书达驿")
                    .fontSize(32)
                    .fontColor(Theme.ink)
                    .fontWeight(FontWeight.Bold)
                    .margin(top: 48, bottom: 8)
                Text("已抵${this.winTitle}")
                    .fontSize(20)
                    .fontColor(Theme.pathInk)
                    .margin(bottom: 28)
                Button("下一站")
                    .width(80.percent)
                    .height(Theme.buttonHeight)
                    .backgroundColor(Theme.buttonFill)
                    .fontColor(Theme.buttonText)
                    .fontSize(18)
                    .margin(bottom: 12)
                    .onClick({event => this.nextLevel()})
                Button("返回驿册")
                    .width(80.percent)
                    .height(Theme.buttonHeight)
                    .backgroundColor(Theme.ink)
                    .fontColor(Theme.buttonText)
                    .fontSize(18)
                    .onClick({event => this.screen = 0})
            } else {
                Row {
                    Button("返回")
                        .height(40)
                        .backgroundColor(Theme.ink)
                        .fontColor(Theme.buttonText)
                        .onClick({event => this.screen = 0})
                    Text("${this.game.level.name}  ${this.game.level.cols}×${this.game.level.rows}")
                        .fontSize(20)
                        .fontColor(Theme.ink)
                        .fontWeight(FontWeight.Bold)
                        .margin(left: 12)
                }
                .width(100.percent)
                .margin(bottom: 8)
                Text("从 1 起笔，拖过邻格；退回上一格即撤销。")
                    .fontSize(13)
                    .fontColor(Theme.muted)
                    .margin(bottom: 8)
                Canvas(this.context)
                    .width(Theme.boardPx)
                    .height(Theme.boardPx)
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
                Row(12) {
                    Button("撤销")
                        .width(48.percent)
                        .height(Theme.buttonHeight)
                        .backgroundColor(Theme.buttonFill)
                        .fontColor(Theme.buttonText)
                        .fontSize(18)
                        .onClick({event => this.doUndo()})
                    Button("重置")
                        .width(48.percent)
                        .height(Theme.buttonHeight)
                        .backgroundColor(Theme.ink)
                        .fontColor(Theme.buttonText)
                        .fontSize(18)
                        .onClick({event => this.doClear()})
                }
                .width(Theme.boardPx)
                .margin(top: 16)
                Text("步数 ${this.game.path.size()} / ${this.game.level.cols * this.game.level.rows}  ·  ${this.tick}")
                    .fontSize(12)
                    .fontColor(Theme.muted)
                    .margin(top: 8)
            }
        }
        .width(100.percent)
        .height(100.percent)
        .padding(Theme.pagePad)
        .backgroundColor(Theme.paper)
        .alignItems(HorizontalAlign.Center)
    }
}
