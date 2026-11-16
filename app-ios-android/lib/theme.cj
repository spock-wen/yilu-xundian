package ohos_app_cangjie_entry

import std.env.*

/* 纯函数 parseHundredths: 将 1/100 点格式的整数字符串解析为 Int64。
 * None / 空串 / 含非 ASCII 数字 / 负号 / 溢出(>9位) 一律返回 0。
 * 禁用 Int64.parse / Int64.toString / 字符串插值。 */
public func parseHundredths(s: ?String): Int64 {
    match (s) {
        case None => return 0
        case Some(str) =>
            let arr = str.toArray()
            let n = arr.size
            if (n == 0 || n > 9) {
                return 0
            }
            var acc: Int64 = 0
            for (b in arr) {
                if (b < 48u8 || b > 57u8) {
                    return 0
                }
                acc = acc * 10 + (Int64(b) - 48)
            }
            return acc
    }
}

public func bottomMarginFor(c: Float64, sb: Float64): Float64 {
    let target = 24.0 - sb
    if (c > target) {
        return c
    } else {
        return target
    }
}

public func chipMarginFor(sb: Float64): Float64 {
    let target = 24.0 - sb
    if (12.0 > target) {
        return 12.0
    } else {
        return target
    }
}

public func chipBarHeightFor(sb: Float64): Float64 {
    return 56.0 + chipMarginFor(sb)
}

public func hasHundredths(s: ?String): Bool {
    match (s) {
        case None => return false
        case Some(str) =>
            let arr = str.toArray()
            let n = arr.size
            if (n == 0 || n > 9) {
                return false
            }
            for (b in arr) {
                if (b < 48u8 || b > 57u8) {
                    return false
                }
            }
            return true
    }
}

public func bottomMarginOrLegacy(c: Float64, legacy: Float64, sbSet: Bool, sb: Float64): Float64 {
    if (!sbSet) {
        return legacy
    }
    return bottomMarginFor(c, sb)
}

public func chipMarginOrLegacy(sbSet: Bool, sb: Float64): Float64 {
    if (!sbSet) {
        return 0.0
    }
    return chipMarginFor(sb)
}

public func chipBarHeightOrLegacy(sbSet: Bool, sb: Float64): Float64 {
    if (!sbSet) {
        return 72.0
    }
    return chipBarHeightFor(sb)
}

/* Designer handoff tokens (mocks 01–06). Do not invent a second skin.
   Color ints follow official Canvas docs (0XRRGGBB). */
public class Theme {
    public static const paper: Int64 = 0xFFF3E8D6
    public static const paperShade: Int64 = 0xFFE6D5B8
    public static const paperLine: Int64 = 0xFFD4C4A8
    public static const ink: Int64 = 0xFF2C2A26
    public static const inkMuted: Int64 = 0xFF5C574E
    public static const qing: Int64 = 0xFF6B7A78
    public static const qingDeep: Int64 = 0xFF3D4A47
    public static const path: Int64 = 0xFF3F4F4C
    public static const gold: Int64 = 0xFFC4A35A
    public static const vermillion: Int64 = 0xFF9B3A2F
    public static const locked: Int64 = 0xFFC9BBA6
    public static const success: Int64 = 0xFF5E7A6A
    public static const whitePaper: Int64 = 0xFFFBF6EC
    /* B4: 胜利(通关)页顶栏以下遮罩色, 纯色 50% ink (0x802C2A26) */
    public static const winScrim: Int64 = 0x802C2A26
    /* B9: 通关卡朱印「文书到」双框与字墨色 (#9B3A2F @ 不透明度 235/255, 0xEB9B3A2F; 验收遮罩色 143,137,126) */
    public static const sealInk: Int64 = 0xEB9B3A2F
    /* 泽地(滑行)填色, hard-fx-skin.md ze */
    public static const ze: Int64 = 0xFFC4D2D6
    /* Parity step limit warning threshold (mock warn state is N=3; applies to 3,2,1,0). */
    public static const stepWarnAt: Int64 = 3
    /* Locked chapter paper tokens (chapters 0..9). */
    public static const pingyuanPaper: Int64 = 0xFFE8EDE6
    public static const xuzhouPaper: Int64 = 0xFFE4E8EC
    public static const lvbuPaper: Int64 = 0xFFE6E4E2
    public static const touyuanPaper: Int64 = 0xFFE8E4DC
    public static const jingzhouPaper: Int64 = 0xFFE8EDE8
    public static const chibiPaper: Int64 = 0xFFE2E4EA
    public static const rushuPaper: Int64 = 0xFFE6E8E2
    public static const hanzhongPaper: Int64 = 0xFFE4E8E6
    public static const beifaPaper: Int64 = 0xFFEDE6D8

    public static func paperOf(chapterId: Int64): Int64 {
        if (chapterId == 1) {
            return Theme.pingyuanPaper
        }
        if (chapterId == 2) {
            return Theme.xuzhouPaper
        }
        if (chapterId == 3) {
            return Theme.lvbuPaper
        }
        if (chapterId == 4) {
            return Theme.touyuanPaper
        }
        if (chapterId == 5) {
            return Theme.jingzhouPaper
        }
        if (chapterId == 6) {
            return Theme.chibiPaper
        }
        if (chapterId == 7) {
            return Theme.rushuPaper
        }
        if (chapterId == 8) {
            return Theme.hanzhongPaper
        }
        if (chapterId == 9) {
            return Theme.beifaPaper
        }
        return Theme.paper
    }
    public static const flagHan: Int64 = 0xFFB33C32
    public static const flagHuang: Int64 = 0xFFE4C35A
    public static const flagGongsun: Int64 = 0xFF9AA7B0
    public static const flagYuan: Int64 = 0xFF7A6B32

    public static func safeTopSet(): Bool {
        var opt: ?String = None
        try {
            opt = getVariable("YILU_SAFE_TOP")
        } catch (e: Exception) {
            opt = None
        }
        return hasHundredths(opt)
    }

    public static func safeTop(): Float64 {
        var opt: ?String = None
        try {
            opt = getVariable("YILU_SAFE_TOP")
        } catch (e: Exception) {
            opt = None
        }
        return Float64(parseHundredths(opt)) / 100.0
    }

    public static func safeBottomSet(): Bool {
        var opt: ?String = None
        try {
            opt = getVariable("YILU_SAFE_BOTTOM")
        } catch (e: Exception) {
            opt = None
        }
        return hasHundredths(opt)
    }

    public static func safeBottom(): Float64 {
        var opt: ?String = None
        try {
            opt = getVariable("YILU_SAFE_BOTTOM")
        } catch (e: Exception) {
            opt = None
        }
        return Float64(parseHundredths(opt)) / 100.0
    }

    public static func bottomMargin(c: Float64, legacy: Float64): Float64 {
        return bottomMarginOrLegacy(c, legacy, Theme.safeBottomSet(), Theme.safeBottom())
    }

    public static func chipMargin(): Float64 {
        return chipMarginOrLegacy(Theme.safeBottomSet(), Theme.safeBottom())
    }

    public static func chipBarHeight(): Float64 {
        return chipBarHeightOrLegacy(Theme.safeBottomSet(), Theme.safeBottom())
    }

    public static const inset: Int64 = 20
    public static const topBar: Int64 = 56
    public static const bottomBar: Int64 = 72
    /* Chapter cards / board chrome — fixed vp so thumbs stay sharp, no overlap.
       Official flags are 512×640 (公孙 560×640) ≈ 4:5 with pole; 24×30 keeps
       汉/黄/袁 readable. Busts are 600×800 = 3:4 → 36×48. */
    public static const chapterCardH: Int64 = 104
    /* Grey-lock card_05..10 are 888×528; 320vp content ≈ 190, use 176. */
    public static const chapterSkinCardH: Int64 = 176
    public static const chapterThumbRowW: Int64 = 128
    public static const flagThumbW: Int64 = 24
    public static const flagThumbH: Int64 = 30
    public static const bustThumbW: Int64 = 36
    public static const bustThumbH: Int64 = 48
    public static const chromeStripH: Int64 = 64
    /* BANDS.md landscape strip: 1080×300 px = 360×100 vp at SCALE 3.
       Origin (0, 246). Hard rule: band.bottom ≤ board.top − 30px (= 10 vp). */
    public static const designW: Int64 = 360
    public static const bandH: Int64 = 100
    public static const bandClear: Int64 = 10
    public static const tutorialCell: Int64 = 48
    public static const boardInner: Int64 = 288
    /* Mock 03-station: ~36 circle on cell 43 (scaled by c/43). */
    public static const stationD: Float64 = 36.0
    /* Mock 03-station: 22–24vp; board uses 24 at cell 48, then cs/48. */
    public static const stationNumber: Int64 = 24
    public static const stationNumberMin: Int64 = 22
    public static const pathStroke: Float64 = 8.0
    public static const primaryH: Int64 = 52
    public static const undoH: Int64 = 56
    public static const iconVp: Int64 = 24
    public static const hairline: Float64 = 1.0

    /* Text chrome uses bundled families (docs_cangjie Text.fontFamily).
       Board waypoint digits are Path2D in vp. */
    public static const serif: String = "YiluSerif"
    public static const serifBold: String = "YiluSerifBold"
    // D-03: only bundled families are allowed (the system default family is not).
    public static const sans: String = "YiluSans"             // YiluSans-Regular.ttf (400)
    public static const sansMedium: String = "YiluSansMedium" // YiluSans-Medium.ttf (500)
    public static const sansBold: String = "YiluSansBold"     // YiluSans-Bold.ttf (700),仅用于首页「章节」
    // one family per file because Keels 0.2.2 cannot carry two weights under one family name (device-tested)
    public static const stationSerif: String = "YiluSerifBold"
}

/* B4: 胜利(通关)页几何纯函数与常量 */
public class WinGeom {
    public static func hairlineY(safeTop: Float64): Float64 {
        return safeTop + 56.0
    }

    public static func maskTop(safeTop: Float64): Float64 {
        return safeTop + 56.0
    }

    public static func maskHeight(h: Float64, safeTop: Float64): Float64 {
        let top = WinGeom.maskTop(safeTop)
        let rem = h - top
        if (rem > 0.0) {
            return rem
        } else {
            return 0.0
        }
    }

    public static func cardX(): Float64 {
        return 28.0
    }

    public static func cardW(w: Float64): Float64 {
        return w - 56.0
    }

    public static func cardH(): Float64 {
        return 360.0
    }

    public static func cardTop(h: Float64, safeTop: Float64, safeBottom: Float64): Float64 {
        let hl = WinGeom.hairlineY(safeTop)
        return hl + (h - safeBottom - hl - WinGeom.cardH()) / 2.0
    }

    public static func cardShadowDx(): Float64 {
        return 3.0
    }

    public static func cardShadowDy(): Float64 {
        return 5.0
    }

    /* 各文字中心偏移(28/62/82/124/154) */
    public static func passCenterY(): Float64 {
        return 28.0
    }

    public static func titleCenterY(): Float64 {
        return 62.0
    }

    public static func goldLineCenterY(): Float64 {
        return 82.0
    }

    public static func roadDoneCenterY(): Float64 {
        return 124.0
    }

    public static func docArriveCenterY(): Float64 {
        return 154.0
    }

    /* 显式行高与 Y 坐标: y = 中心 - h/2 */
    public static func passH(): Float64 {
        return 20.0
    }

    public static func passY(): Float64 {
        return WinGeom.passCenterY() - WinGeom.passH() / 2.0
    }

    public static func titleH(): Float64 {
        return 28.0
    }

    public static func titleY(): Float64 {
        return WinGeom.titleCenterY() - WinGeom.titleH() / 2.0
    }

    public static func goldLineH(): Float64 {
        return 1.2
    }

    public static func goldLineY(): Float64 {
        return WinGeom.goldLineCenterY() - WinGeom.goldLineH() / 2.0
    }

    /* YiluSerif-Bold 22u 实测字宽(advance × 22 / 1000):
     * 汉字=22.0, ·=7.37, 空格=5.5, -=8.14,
     * 数字: 0=13.046, 1=10.252, 2=13.068, 3=13.046, 4=13.046,
     *       5=13.068, 6=13.068, 7=12.936, 8=13.068, 9=13.112.
     * 未列 CJK(>= \u{2E80}) 保守回退 22.0; 其余未列 ASCII 保守回退 13.0。
     * 禁用 Int64.toString / Int64.parse。 */
    public static func serifBoldAdvance22(r: Rune): Float64 {
        if (r == r'·') {
            return 7.37
        } else if (r == r' ') {
            return 5.5
        } else if (r == r'-') {
            return 8.14
        } else if (r == r'0') {
            return 13.046
        } else if (r == r'1') {
            return 10.252
        } else if (r == r'2') {
            return 13.068
        } else if (r == r'3') {
            return 13.046
        } else if (r == r'4') {
            return 13.046
        } else if (r == r'5') {
            return 13.068
        } else if (r == r'6') {
            return 13.068
        } else if (r == r'7') {
            return 12.936
        } else if (r == r'8') {
            return 13.068
        } else if (r == r'9') {
            return 13.112
        } else if (r >= r'\u{2E80}') {
            return 22.0
        } else {
            return 13.0
        }
    }

    /* 关名实际排版宽度: 逐字符按 YiluSerif-Bold 22u 实测表求和 */
    public static func roadTitleWidth(title: String): Float64 {
        var w: Float64 = 0.0
        for (r in title.toRuneArray()) {
            w += WinGeom.serifBoldAdvance22(r)
        }
        return w
    }

    /* 金线宽度上限截断: 若宽 > 卡内宽(cardW - 2.0) 则 min(宽, cardW - 2.0) */
    public static func goldLineWidth(title: String, w: Float64): Float64 {
        let tw = WinGeom.roadTitleWidth(title)
        let maxW = WinGeom.cardW(w) - 2.0
        if (tw > maxW) {
            return maxW
        } else {
            return tw
        }
    }

    public static func goldLineX(w: Float64, titleW: Float64): Float64 {
        return (WinGeom.cardW(w) - titleW) / 2.0
    }

    public static func roadDoneH(): Float64 {
        return 22.0
    }

    public static func roadDoneX(): Float64 {
        return 24.0
    }

    public static func roadDoneY(): Float64 {
        return WinGeom.roadDoneCenterY() - WinGeom.roadDoneH() / 2.0
    }

    public static func docArriveH(): Float64 {
        return 18.0
    }

    public static func docArriveX(): Float64 {
        return 24.0
    }

    public static func docArriveY(): Float64 {
        return WinGeom.docArriveCenterY() - WinGeom.docArriveH() / 2.0
    }

    /* 朱印几何 */
    public static func sealSize(): Float64 {
        return 96.0
    }

    public static func sealAngle(): Float64 {
        return -18.0
    }

    public static func sealLeft(w: Float64): Float64 {
        return WinGeom.cardW(w) - 24.0 - WinGeom.sealSize()
    }

    public static func sealTop(): Float64 {
        return 100.0
    }

    /* 外框: 距印边 6.0, 线宽 6.0, 圆角 6.9 */
    public static func sealOuterInset(): Float64 {
        return 6.0
    }

    public static func sealOuterStroke(): Float64 {
        return 6.0
    }

    public static func sealOuterRadius(): Float64 {
        return 6.9
    }

    public static func sealOuterSize(): Float64 {
        return WinGeom.sealSize() - 2.0 * WinGeom.sealOuterInset()
    }

    public static func sealOuterW(): Float64 {
        return WinGeom.sealOuterSize()
    }

    /* 内框: 距印边 16.3, 线宽 3.0 (内缘 19.3), 圆角 4.8 */
    public static func sealInnerInset(): Float64 {
        return 16.3
    }

    public static func sealInnerStroke(): Float64 {
        return 3.0
    }

    public static func sealInnerRadius(): Float64 {
        return 4.8
    }

    public static func sealInnerSize(): Float64 {
        return WinGeom.sealSize() - 2.0 * WinGeom.sealInnerInset()
    }

    public static func sealInnerW(): Float64 {
        return WinGeom.sealInnerSize()
    }

    /* 印字: 3 个 Text「文」「书」「到」, 字号 17.0, 行距 19.0 */
    public static func sealGlyphFont(): Float64 {
        return 17.0
    }

    public static func sealGlyphPitch(): Float64 {
        return 19.0
    }

    /* 中心 y: 29 / 48 / 67 (整体居中于内框内缘) */
    public static func sealGlyphCenterY(i: Int64): Float64 {
        if (i == 0) {
            return 29.0
        } else if (i == 1) {
            return 48.0
        } else if (i == 2) {
            return 67.0
        } else {
            return 48.0 + Float64(i - 1) * WinGeom.sealGlyphPitch()
        }
    }

    /* y 坐标 = 中心 - pitch / 2.0 (19.5 / 38.5 / 57.5) */
    public static func sealGlyphY(i: Int64): Float64 {
        return WinGeom.sealGlyphCenterY(i) - WinGeom.sealGlyphPitch() / 2.0
    }

    /* 「下一驿」按钮几何 */
    public static func btnX(): Float64 {
        return 20.0
    }

    public static func btnW(w: Float64): Float64 {
        return WinGeom.cardW(w) - 40.0
    }

    public static func btnTop(): Float64 {
        return 288.0
    }

    public static func btnH(): Float64 {
        return 52.0
    }
}
