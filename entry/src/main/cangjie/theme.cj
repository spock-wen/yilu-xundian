package ohos_app_cangjie_entry

/* Designer handoff tokens (mocks 01–06). Do not invent a second skin.
   Color ints follow official Canvas docs (0XRRGGBB). */
public class Theme {
    public static let paper: Int64 = 0XF3E8D6
    public static let paperShade: Int64 = 0XE6D5B8
    public static let paperLine: Int64 = 0XD4C4A8
    public static let ink: Int64 = 0X2C2A26
    public static let inkMuted: Int64 = 0X5C574E
    public static let qing: Int64 = 0X6B7A78
    public static let qingDeep: Int64 = 0X3D4A47
    public static let path: Int64 = 0X3F4F4C
    public static let gold: Int64 = 0XC4A35A
    public static let vermillion: Int64 = 0X9B3A2F
    public static let locked: Int64 = 0XC9BBA6
    public static let success: Int64 = 0X5E7A6A
    public static let whitePaper: Int64 = 0XFBF6EC
    /* 平原 board paper from chapter-flow v1.3 mock (sage). */
    public static let pingyuanPaper: Int64 = 0XE7EBD8
    /* ch05-10-SHIP.md paper tokens — preview screen only. */
    public static let touyuanPaper: Int64 = 0XE8E4DC
    public static let jingzhouPaper: Int64 = 0XE8EDE8
    public static let chibiPaper: Int64 = 0XE2E4EA
    public static let rushuPaper: Int64 = 0XE6E8E2
    public static let hanzhongPaper: Int64 = 0XE4E8E6
    public static let beifaPaper: Int64 = 0XEDE6D8

    public static func paperOf(chapterId: Int64): Int64 {
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
        if (chapterId == 1) {
            return Theme.pingyuanPaper
        }
        return Theme.paper
    }
    public static let flagHan: Int64 = 0XB33C32
    public static let flagHuang: Int64 = 0XE4C35A
    public static let flagGongsun: Int64 = 0X9AA7B0
    public static let flagYuan: Int64 = 0X7A6B32

    public static let inset: Int64 = 20
    public static let topBar: Int64 = 56
    public static let bottomBar: Int64 = 72
    /* Chapter cards / board chrome — fixed vp so thumbs stay sharp, no overlap.
       Official flags are 512×640 (公孙 560×640) ≈ 4:5 with pole; 24×30 keeps
       汉/黄/袁 readable. Busts are 600×800 = 3:4 → 36×48. */
    public static let chapterCardH: Int64 = 104
    /* Grey-lock card_05..10 are 888×528; 320vp content ≈ 190, use 176. */
    public static let chapterSkinCardH: Int64 = 176
    public static let chapterThumbRowW: Int64 = 128
    public static let flagThumbW: Int64 = 24
    public static let flagThumbH: Int64 = 30
    public static let bustThumbW: Int64 = 36
    public static let bustThumbH: Int64 = 48
    public static let chromeStripH: Int64 = 64
    /* BANDS.md landscape strip: 1080×300 px = 360×100 vp at SCALE 3.
       Origin (0, 246). Hard rule: band.bottom ≤ board.top − 30px (= 10 vp). */
    public static let designW: Int64 = 360
    public static let bandH: Int64 = 100
    public static let bandClear: Int64 = 10
    public static let tutorialCell: Int64 = 48
    public static let boardInner: Int64 = 288
    /* Mock 03-station: ~40 circle on the 48vp tutorial cell. */
    public static let stationD: Float64 = 40.0
    /* Mock 03-station: 22–24vp; board uses 24 at cell 48, then cs/48. */
    public static let stationNumber: Int64 = 24
    public static let stationNumberMin: Int64 = 22
    public static let pathStroke: Float64 = 8.0
    public static let primaryH: Int64 = 52
    public static let undoH: Int64 = 56
    public static let iconVp: Int64 = 24
    public static let hairline: Float64 = 1.0

    /* Text chrome still uses system generic families (docs_cangjie
       Text.fontFamily). Board waypoint digits are Path2D in vp. */
    public static let serif: String = "serif"
    public static let sans: String = "sans-serif"
    public static let stationSerif: String = "Noto Serif SC"
}
