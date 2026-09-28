package ohos_app_cangjie_entry

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
    /* 平原 board paper from chapter-flow v1.3 mock (sage). */
    public static const pingyuanPaper: Int64 = 0xFFE7EBD8
    /* ch05-10-SHIP.md paper tokens — preview screen only. */
    public static const touyuanPaper: Int64 = 0xFFE8E4DC
    public static const jingzhouPaper: Int64 = 0xFFE8EDE8
    public static const chibiPaper: Int64 = 0xFFE2E4EA
    public static const rushuPaper: Int64 = 0xFFE6E8E2
    public static const hanzhongPaper: Int64 = 0xFFE4E8E6
    public static const beifaPaper: Int64 = 0xFFEDE6D8

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
    public static const flagHan: Int64 = 0xFFB33C32
    public static const flagHuang: Int64 = 0xFFE4C35A
    public static const flagGongsun: Int64 = 0xFF9AA7B0
    public static const flagYuan: Int64 = 0xFF7A6B32

    // PLACEHOLDER(M1): safe area / status bar follows current HarmonyOS styling (no extra inset, paper background) until PM design decision.
    public static const safeAreaTop: Int64 = 0

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
    /* Mock 03-station: ~40 circle on the 48vp tutorial cell. */
    public static const stationD: Float64 = 40.0
    /* Mock 03-station: 22–24vp; board uses 24 at cell 48, then cs/48. */
    public static const stationNumber: Int64 = 24
    public static const stationNumberMin: Int64 = 22
    public static const pathStroke: Float64 = 8.0
    public static const primaryH: Int64 = 52
    public static const undoH: Int64 = 56
    public static const iconVp: Int64 = 24
    public static const hairline: Float64 = 1.0

    /* Text chrome still uses system generic families (docs_cangjie
       Text.fontFamily). Board waypoint digits are Path2D in vp. */
    public static const serif: String = "YiluSerif"
    public static const serifBold: String = "YiluSerifBold"
    public static const sans: String = "sans-serif"
    public static const stationSerif: String = "YiluSerifBold"
}
