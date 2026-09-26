import UIKit

struct BoardMetrics {
    var origin: CGPoint
    var cell: CGFloat
    var cols: Int
    var rows: Int
}

/// Draws engine state and forwards touches through `yilu_touch_to_cell` / `yilu_try_step`.
final class BoardView: UIView {
    var onChange: (() -> Void)?
    private var lastCell: (Int32, Int32)?

    override init(frame: CGRect) {
        super.init(frame: frame)
        isMultipleTouchEnabled = false
        isOpaque = true
        backgroundColor = BoardPalette.paper
        contentMode = .redraw
    }

    required init?(coder: NSCoder) {
        return nil
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        setNeedsDisplay()
    }

    override func draw(_ rect: CGRect) {
        guard let ctx = UIGraphicsGetCurrentContext() else { return }
        BoardPalette.paper.setFill()
        ctx.fill(bounds)
        guard yilu_ready() == 1 else { return }
        guard let metrics = makeMetrics() else { return }
        drawCells(ctx, metrics)
        drawGrid(ctx, metrics)
        drawWalls(ctx, metrics)
        drawPath(ctx, metrics)
        drawNumbers(metrics)
    }

    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
        lastCell = nil
        if let point = touches.first?.location(in: self) {
            apply(point)
        }
    }

    override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent?) {
        if let point = touches.first?.location(in: self) {
            apply(point)
        }
    }

    override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent?) {
        lastCell = nil
    }

    override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent?) {
        lastCell = nil
    }

    private func apply(_ point: CGPoint) {
        guard yilu_ready() == 1, let metrics = makeMetrics(), metrics.cell > 0 else { return }
        var x: Int32 = -1
        var y: Int32 = -1
        let hit = yilu_touch_to_cell(
            Double(point.x),
            Double(point.y),
            Double(metrics.origin.x),
            Double(metrics.origin.y),
            Double(metrics.cell),
            &x,
            &y
        )
        if hit != 1 {
            return
        }
        if lastCell?.0 == x && lastCell?.1 == y {
            return
        }
        lastCell = (x, y)
        _ = yilu_try_step(x, y)
        setNeedsDisplay()
        onChange?()
    }

    private func makeMetrics() -> BoardMetrics? {
        let cols = Int(yilu_cols())
        let rows = Int(yilu_rows())
        if cols <= 0 || rows <= 0 || bounds.width < 2 || bounds.height < 2 {
            return nil
        }
        let pad: CGFloat = 12
        let availW = bounds.width - pad * 2
        let availH = bounds.height - pad * 2
        if availW <= 0 || availH <= 0 {
            return nil
        }
        let cell = min(availW / CGFloat(cols), availH / CGFloat(rows))
        let gridW = cell * CGFloat(cols)
        let gridH = cell * CGFloat(rows)
        let origin = CGPoint(x: (bounds.width - gridW) / 2, y: (bounds.height - gridH) / 2)
        return BoardMetrics(origin: origin, cell: cell, cols: cols, rows: rows)
    }

    private func cellRect(_ x: Int, _ y: Int, _ m: BoardMetrics) -> CGRect {
        CGRect(
            x: m.origin.x + CGFloat(x) * m.cell,
            y: m.origin.y + CGFloat(y) * m.cell,
            width: m.cell,
            height: m.cell
        )
    }

    private func center(_ x: Int32, _ y: Int32, _ m: BoardMetrics) -> CGPoint {
        CGPoint(
            x: m.origin.x + (CGFloat(x) + 0.5) * m.cell,
            y: m.origin.y + (CGFloat(y) + 0.5) * m.cell
        )
    }

    private func drawCells(_ ctx: CGContext, _ m: BoardMetrics) {
        let next = yilu_next_required()
        for y in 0..<m.rows {
            for x in 0..<m.cols {
                let rect = cellRect(x, y, m).insetBy(dx: 1, dy: 1)
                BoardPalette.whitePaper.setFill()
                ctx.fill(rect)
                let n = yilu_number_at(Int32(x), Int32(y))
                if n != 0 && n == next {
                    BoardPalette.gold.setStroke()
                    ctx.setLineWidth(1)
                    ctx.stroke(rect.insetBy(dx: 2, dy: 2))
                }
            }
        }
    }

    private func drawGrid(_ ctx: CGContext, _ m: BoardMetrics) {
        BoardPalette.paperLine.setStroke()
        ctx.setLineWidth(1)
        ctx.beginPath()
        for c in 0...m.cols {
            let x = m.origin.x + CGFloat(c) * m.cell
            ctx.move(to: CGPoint(x: x, y: m.origin.y))
            ctx.addLine(to: CGPoint(x: x, y: m.origin.y + CGFloat(m.rows) * m.cell))
        }
        for r in 0...m.rows {
            let y = m.origin.y + CGFloat(r) * m.cell
            ctx.move(to: CGPoint(x: m.origin.x, y: y))
            ctx.addLine(to: CGPoint(x: m.origin.x + CGFloat(m.cols) * m.cell, y: y))
        }
        ctx.strokePath()
    }

    private func drawWalls(_ ctx: CGContext, _ m: BoardMetrics) {
        let count = Int(yilu_wall_count())
        if count <= 0 {
            return
        }
        BoardPalette.ink.setStroke()
        ctx.setLineWidth(max(3, m.cell * 0.12))
        ctx.setLineCap(.round)
        ctx.beginPath()
        for i in 0..<count {
            var x1: Int32 = 0
            var y1: Int32 = 0
            var x2: Int32 = 0
            var y2: Int32 = 0
            if yilu_wall_at(Int32(i), &x1, &y1, &x2, &y2) != 1 {
                continue
            }
            addWall(ctx, x1: Int(x1), y1: Int(y1), x2: Int(x2), y2: Int(y2), m: m)
        }
        ctx.strokePath()
    }

    private func addWall(_ ctx: CGContext, x1: Int, y1: Int, x2: Int, y2: Int, m: BoardMetrics) {
        let left = min(x1, x2)
        let top = min(y1, y2)
        if y1 == y2 {
            let x = m.origin.x + CGFloat(left + 1) * m.cell
            let y = m.origin.y + CGFloat(y1) * m.cell
            ctx.move(to: CGPoint(x: x, y: y + m.cell * 0.12))
            ctx.addLine(to: CGPoint(x: x, y: y + m.cell * 0.88))
        } else if x1 == x2 {
            let x = m.origin.x + CGFloat(x1) * m.cell
            let y = m.origin.y + CGFloat(top + 1) * m.cell
            ctx.move(to: CGPoint(x: x + m.cell * 0.12, y: y))
            ctx.addLine(to: CGPoint(x: x + m.cell * 0.88, y: y))
        }
    }

    private func drawPath(_ ctx: CGContext, _ m: BoardMetrics) {
        let count = Int(yilu_path_len())
        if count <= 0 {
            return
        }
        for i in 0..<count {
            var x: Int32 = 0
            var y: Int32 = 0
            if yilu_path_at(Int32(i), &x, &y) != 1 {
                continue
            }
            let rect = cellRect(Int(x), Int(y), m).insetBy(dx: m.cell * 0.18, dy: m.cell * 0.18)
            BoardPalette.qing.setFill()
            ctx.fill(rect)
        }
        BoardPalette.path.setStroke()
        ctx.setLineWidth(max(4, m.cell * 0.16))
        ctx.setLineCap(.round)
        ctx.setLineJoin(.round)
        ctx.beginPath()
        for i in 0..<count {
            var x: Int32 = 0
            var y: Int32 = 0
            if yilu_path_at(Int32(i), &x, &y) != 1 {
                continue
            }
            let p = center(x, y, m)
            if i == 0 {
                ctx.move(to: p)
            } else {
                ctx.addLine(to: p)
            }
        }
        ctx.strokePath()
    }

    private func drawNumbers(_ m: BoardMetrics) {
        let font = UIFont.systemFont(ofSize: max(12, m.cell * 0.42), weight: .medium)
        let attrs: [NSAttributedString.Key: Any] = [
            .font: font,
            .foregroundColor: BoardPalette.ink,
        ]
        for y in 0..<m.rows {
            for x in 0..<m.cols {
                let n = yilu_number_at(Int32(x), Int32(y))
                if n == 0 {
                    continue
                }
                let text = "\(n)" as NSString
                let size = text.size(withAttributes: attrs)
                let rect = cellRect(x, y, m)
                let drawRect = CGRect(
                    x: rect.midX - size.width / 2,
                    y: rect.midY - size.height / 2,
                    width: size.width,
                    height: size.height
                )
                text.draw(in: drawRect, withAttributes: attrs)
            }
        }
    }
}

enum BoardPalette {
    /* Tokens from the repo README「设计师 token」table. */
    static let paper = BoardPalette.color(0xF3E8D6)
    static let paperLine = BoardPalette.color(0xD4C4A8)
    static let ink = BoardPalette.color(0x2C2A26)
    static let qing = BoardPalette.color(0x6B7A78)
    static let path = BoardPalette.color(0x3F4F4C)
    static let gold = BoardPalette.color(0xC4A35A)
    static let whitePaper = BoardPalette.color(0xFBF6EC)

    static func color(_ hex: UInt32) -> UIColor {
        UIColor(
            red: CGFloat((hex >> 16) & 0xFF) / 255,
            green: CGFloat((hex >> 8) & 0xFF) / 255,
            blue: CGFloat(hex & 0xFF) / 255,
            alpha: 1
        )
    }
}
