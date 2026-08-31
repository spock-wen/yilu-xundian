package ohos_app_cangjie_entry.game

/* 半印勘合 — slide two ticket halves until they meet.
   Not a Zip / patrol board. Copy from Notion「桑氏传粮 故事草稿」
   §失散插章 (2026-08-31). Engine stays Canvas-free. */

public class KanheGame {
    public static let halfW: Float64 = 140.0
    public static let halfH: Float64 = 168.0
    public static let alignTol: Float64 = 14.0
    public static let canvasW: Float64 = 320.0
    public static let canvasH: Float64 = 280.0
    public static let startLeftX: Float64 = 8.0
    public static let startLeftY: Float64 = 36.0
    public static let startRightX: Float64 = 172.0
    public static let startRightY: Float64 = 96.0
    public static let copyLeft: String = "乌巢仓破。持此半票。"
    public static let copyRight: String = "南寻汝南。持此半票。"
    public static let copyJoined: String = "仓破人散。南寻汝南。"
    public static let copySeal: String = "归队"
    public static let copyReturn: String = "北不可回。南寻汝南。"

    public var leftX: Float64 = 8.0
    public var leftY: Float64 = 36.0
    public var rightX: Float64 = 172.0
    public var rightY: Float64 = 96.0
    public var phase: Int64 = 0
    public var drag: Int64 = 0
    public var grabX: Float64 = 0.0
    public var grabY: Float64 = 0.0
    public var miss: Int64 = 0

    public init() {}

    public func reset(): Unit {
        this.leftX = KanheGame.startLeftX
        this.leftY = KanheGame.startLeftY
        this.rightX = KanheGame.startRightX
        this.rightY = KanheGame.startRightY
        this.phase = 0
        this.drag = 0
        this.grabX = 0.0
        this.grabY = 0.0
        this.miss = 0
    }

    func contains(px: Float64, py: Float64, x: Float64, y: Float64): Bool {
        return px >= x && py >= y && px <= x + KanheGame.halfW && py <= y + KanheGame.halfH
    }

    func clampX(v: Float64): Float64 {
        let hi = KanheGame.canvasW - KanheGame.halfW
        if (v < 0.0) {
            return 0.0
        }
        if (v > hi) {
            return hi
        }
        return v
    }

    func clampY(v: Float64): Float64 {
        let hi = KanheGame.canvasH - KanheGame.halfH
        if (v < 0.0) {
            return 0.0
        }
        if (v > hi) {
            return hi
        }
        return v
    }

    func absF(v: Float64): Float64 {
        if (v < 0.0) {
            return -v
        }
        return v
    }

    public func isAligned(): Bool {
        let dx = this.rightX - (this.leftX + KanheGame.halfW)
        let dy = this.rightY - this.leftY
        return this.absF(dx) <= KanheGame.alignTol && this.absF(dy) <= KanheGame.alignTol
    }

    func snap(): Unit {
        let joined = KanheGame.halfW * 2.0
        this.leftX = (KanheGame.canvasW - joined) / 2.0
        this.leftY = (KanheGame.canvasH - KanheGame.halfH) / 2.0
        this.rightX = this.leftX + KanheGame.halfW
        this.rightY = this.leftY
    }

    public func down(px: Float64, py: Float64): Unit {
        if (this.phase != 0) {
            return
        }
        let inLeft = this.contains(px, py, this.leftX, this.leftY)
        let inRight = this.contains(px, py, this.rightX, this.rightY)
        var pick: Int64 = 0
        if (inLeft && inRight) {
            let ldx = px - (this.leftX + KanheGame.halfW / 2.0)
            let ldy = py - (this.leftY + KanheGame.halfH / 2.0)
            let rdx = px - (this.rightX + KanheGame.halfW / 2.0)
            let rdy = py - (this.rightY + KanheGame.halfH / 2.0)
            if (ldx * ldx + ldy * ldy <= rdx * rdx + rdy * rdy) {
                pick = 1
            } else {
                pick = 2
            }
        } else if (inLeft) {
            pick = 1
        } else if (inRight) {
            pick = 2
        }
        this.drag = pick
        if (pick == 1) {
            this.grabX = px - this.leftX
            this.grabY = py - this.leftY
        } else if (pick == 2) {
            this.grabX = px - this.rightX
            this.grabY = py - this.rightY
        }
    }

    public func move(px: Float64, py: Float64): Unit {
        if (this.drag == 1) {
            this.leftX = this.clampX(px - this.grabX)
            this.leftY = this.clampY(py - this.grabY)
        } else if (this.drag == 2) {
            this.rightX = this.clampX(px - this.grabX)
            this.rightY = this.clampY(py - this.grabY)
        }
    }

    public func up(): Bool {
        if (this.drag == 0) {
            return false
        }
        this.drag = 0
        if (this.isAligned()) {
            this.snap()
            this.phase = 1
            this.miss = 0
            return true
        }
        this.miss = 1
        return false
    }

    public func cancel(): Unit {
        this.drag = 0
    }

    public func showReturn(): Unit {
        this.phase = 2
    }
}
