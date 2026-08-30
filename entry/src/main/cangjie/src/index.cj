package ohos_app_cangjie_entry

import ohos.base.*
import ohos.component.*
import ohos.state_manage.*
import ohos.state_macro_manage.*
import ohos_app_cangjie_entry.engine.{GridLayout, touchToCell}
import ohos_app_cangjie_entry.game.{LevelDef, PatrolGame, Waypoint}

/*
 * Canvas + onTouch pattern verified against published HarmonyOS NEXT
 * Cangjie drawing-board writeups (RenderingContextSettings / Path2D /
 * e.eventType.toString() == "Down"|"Move"|"Up").
 * Do not assume ArkTS TouchType exists in Cangjie.
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

    protected open func onPageShow() {
        this.context.lineWidth(3)
        this.context.strokeStyle(Theme.gridLine)
        this.drawBoard()
    }

    public func aboutToAppear(): Unit {
        this.drawBoard()
    }

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

    func handleTouch(e: TouchEvent): Unit {
        let kind = e.eventType.toString()
        if (kind != "Down" && kind != "Move") {
            return
        }
        let px = e.touches[0].x
        let py = e.touches[0].y
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

    func addLine(path: Path2D, x1: Float64, y1: Float64, x2: Float64, y2: Float64): Unit {
        path.moveTo(x1, y1)
        path.bezierCurveTo(x1, y1, x2, y2, x2, y2)
    }

    func addCircle(path: Path2D, cx: Float64, cy: Float64, r: Float64): Unit {
        let k = 0.55228475 * r
        path.moveTo(cx, cy - r)
        path.bezierCurveTo(cx + k, cy - r, cx + r, cy - k, cx + r, cy)
        path.bezierCurveTo(cx + r, cy + k, cx + k, cy + r, cx, cy + r)
        path.bezierCurveTo(cx - k, cy + r, cx - r, cy + k, cx - r, cy)
        path.bezierCurveTo(cx - r, cy - k, cx - k, cy - r, cx, cy - r)
    }

    func drawBoard(): Unit {
        this.context.clearRect(0.0, 0.0, 3000.0, 3000.0)
        let layout = this.currentLayout()
        let cols = layout.cols
        let rows = layout.rows
        let ox = layout.originX
        let oy = layout.originY
        let cs = layout.cellSize

        let grid = Path2D()
        var x: Int64 = 0
        while (x <= cols) {
            let px = ox + Float64(x) * cs
            this.addLine(grid, px, oy, px, oy + Float64(rows) * cs)
            x = x + 1
        }
        var y: Int64 = 0
        while (y <= rows) {
            let py = oy + Float64(y) * cs
            this.addLine(grid, ox, py, ox + Float64(cols) * cs, py)
            y = y + 1
        }
        this.context.lineWidth(2)
        this.context.strokeStyle(Theme.gridLine)
        this.context.stroke(grid)

        let walls = Path2D()
        for (wall in this.game.level.walls) {
            var ax = wall.x1
            var ay = wall.y1
            var bx = wall.x2
            var by = wall.y2
            if (ay == by && ax + 1 == bx) {
                let px = ox + Float64(bx) * cs
                this.addLine(walls, px, oy + Float64(ay) * cs + 4.0, px, oy + Float64(ay + 1) * cs - 4.0)
            } else if (ay == by && bx + 1 == ax) {
                let px = ox + Float64(ax) * cs
                this.addLine(walls, px, oy + Float64(ay) * cs + 4.0, px, oy + Float64(ay + 1) * cs - 4.0)
            } else if (ax == bx && ay + 1 == by) {
                let py = oy + Float64(by) * cs
                this.addLine(walls, ox + Float64(ax) * cs + 4.0, py, ox + Float64(ax + 1) * cs - 4.0, py)
            } else if (ax == bx && by + 1 == ay) {
                let py = oy + Float64(ay) * cs
                this.addLine(walls, ox + Float64(ax) * cs + 4.0, py, ox + Float64(ax + 1) * cs - 4.0, py)
            }
        }
        this.context.lineWidth(6)
        this.context.strokeStyle(Theme.wallInk)
        this.context.stroke(walls)

        if (this.game.path.size() >= 2) {
            let trail = Path2D()
            let first = this.game.path.at(0)
            var lx = ox + (Float64(first.x) + 0.5) * cs
            var ly = oy + (Float64(first.y) + 0.5) * cs
            var i: Int64 = 1
            while (i < this.game.path.size()) {
                let cell = this.game.path.at(i)
                let nx = ox + (Float64(cell.x) + 0.5) * cs
                let ny = oy + (Float64(cell.y) + 0.5) * cs
                this.addLine(trail, lx, ly, nx, ny)
                lx = nx
                ly = ny
                i = i + 1
            }
            this.context.lineWidth(8)
            this.context.strokeStyle(Theme.pathInk)
            this.context.stroke(trail)
        }

        let rings = Path2D()
        for (wp in this.game.level.waypoints) {
            let cx = ox + (Float64(wp.x) + 0.5) * cs
            let cy = oy + (Float64(wp.y) + 0.5) * cs
            this.addCircle(rings, cx, cy, cs * 0.32)
        }
        this.context.lineWidth(3)
        this.context.strokeStyle(Theme.stationRing)
        this.context.stroke(rings)
    }

    func waypointLeft(wp: Waypoint): Int64 {
        let layout = this.currentLayout()
        return Int64(layout.originX + Float64(wp.x) * layout.cellSize)
    }

    func waypointTop(wp: Waypoint): Int64 {
        let layout = this.currentLayout()
        return Int64(layout.originY + Float64(wp.y) * layout.cellSize)
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
                                    .onClick({e => this.openLevel(index)})
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
                    .onClick({e => this.nextLevel()})
                Button("返回驿册")
                    .width(80.percent)
                    .height(Theme.buttonHeight)
                    .backgroundColor(Theme.ink)
                    .fontColor(Theme.buttonText)
                    .fontSize(18)
                    .onClick({e => this.screen = 0})
            } else {
                Row {
                    Button("返回")
                        .height(40)
                        .backgroundColor(Theme.ink)
                        .fontColor(Theme.buttonText)
                        .onClick({e => this.screen = 0})
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
                Stack {
                    Canvas(this.context)
                        .width(Theme.boardPx)
                        .height(Theme.boardPx)
                        .backgroundColor(Theme.paper)
                        .onTouch({e: TouchEvent => this.handleTouch(e)})
                    ForEach(
                        this.game.level.waypoints,
                        itemGeneratorFunc: {wp: Waypoint, index: Int64 =>
                            Text("${wp.n}")
                                .fontSize(this.numberFont())
                                .fontColor(Theme.ink)
                                .fontWeight(FontWeight.Bold)
                                .width(Int64(this.currentLayout().cellSize).px)
                                .height(Int64(this.currentLayout().cellSize).px)
                                .textAlign(TextAlign.Center)
                                .position(x: this.waypointLeft(wp).px, y: this.waypointTop(wp).px)
                        }
                    )
                }
                .width(Theme.boardPx)
                .height(Theme.boardPx)
                Row(12) {
                    Button("撤销")
                        .width(48.percent)
                        .height(Theme.buttonHeight)
                        .backgroundColor(Theme.buttonFill)
                        .fontColor(Theme.buttonText)
                        .fontSize(18)
                        .onClick({e => this.doUndo()})
                    Button("重置")
                        .width(48.percent)
                        .height(Theme.buttonHeight)
                        .backgroundColor(Theme.ink)
                        .fontColor(Theme.buttonText)
                        .fontSize(18)
                        .onClick({e => this.doClear()})
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
