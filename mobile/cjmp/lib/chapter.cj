package ohos_app_cangjie_entry

/* chapter-flow v1.3 SHIP cards over LevelCatalog.
   Catalog.open = has boards (涿郡..北伐 ch1..10), not current unlock.
   Runtime: 涿郡 always; later chapters iff cleared >= levelStart.
   All 10 chapters (levelCount 10) have boards wired in LevelCatalog.
   05–10 skins (assets/chapter-skins-05-10-v91) provide fullscreen preview when locked.
   Official media: bust_p01..p10 + bust_s01, flag_p01..p10 + flag_gate_pattern,
   skin_01/02 + skin_05..10, card_05..10. Gate flag is pattern-only (no 关).
   Board landscape bands (assets/chapter-bands-v91): band_zhuojun_v91 /
   band_pingyuan_v91 / band_xuzhou_v91 / band_lvbu_v91 / band_touyuan_v91 /
   band_jingzhou_v91 / band_chibi_v91 / band_rushu_v91 / band_hanzhong_v91 /
   band_beifa_v91, 1080×300 composite (bust+flag+terrain). */
import std.collection.ArrayList
import ohos_app_cangjie_entry.game.LevelDef

public class ChapterDef {
    public var id: Int64
    public var name: String
    public var label: String
    public var title: String
    public var subtitle: String
    public var listSubtitle: String
    public var boardSubtitle: String
    public var friendLine: String
    public var tensionLine: String
    public var cityLine: String
    public var levelStart: Int64
    public var levelCount: Int64
    public var open: Bool

    public init(
        id: Int64,
        name: String,
        label: String,
        title: String,
        subtitle: String,
        listSubtitle: String,
        boardSubtitle: String,
        friendLine: String,
        tensionLine: String,
        cityLine: String,
        levelStart: Int64,
        levelCount: Int64,
        open: Bool
    ) {
        this.id = id
        this.name = name
        this.label = label
        this.title = title
        this.subtitle = subtitle
        this.listSubtitle = listSubtitle
        this.boardSubtitle = boardSubtitle
        this.friendLine = friendLine
        this.tensionLine = tensionLine
        this.cityLine = cityLine
        this.levelStart = levelStart
        this.levelCount = levelCount
        this.open = open
    }

    // chapter 8 caption copy: city shown without the 城： label, PM decision 2026-10-01
    public func cityPrefix(): String {
        if (this.id == 7) {
            return ""
        }
        return "城："
    }

    public func chromeLine(): String {
        return "友：${this.friendLine} · 张力：${this.tensionLine} · ${this.cityPrefix()}${this.cityLine}"
    }
}

public class ChapterCatalog {
    public static func all(): ArrayList<ChapterDef> {
        let chapters = ArrayList<ChapterDef>()
        chapters.add(ChapterDef(
            0,
            "涿郡",
            "第1章 涿郡",
            "涿郡·安喜",
            "仓官×渠帅 · 汉×黄 · 黄巾乱世出粮",
            "仓官×渠帅 · 汉×黄 · 安喜",
            "仓官×渠帅 · 汉×黄 · 安喜",
            "汉廷官仓",
            "黄巾乱世出粮",
            "涿·安喜",
            0,
            10,
            true
        ))
        chapters.add(ChapterDef(
            1,
            "平原",
            "第2章 平原",
            "平原·郡治",
            "公孙×袁绍 · 袁绍为敌",
            "公孙×袁绍 · 公孙×袁 · 郡治",
            "公孙×袁绍 · 公孙×袁 · 郡治",
            "公孙瓒",
            "袁绍为敌",
            "高唐·郡治",
            10,
            10,
            true
        ))
        chapters.add(ChapterDef(
            2,
            "徐州",
            "第3章 徐州",
            "徐州·下邳",
            "刘×曹 · 淮泗争粮",
            "刘×曹 · 淮泗争粮",
            "刘×曹 · 淮泗争粮",
            "刘备",
            "淮泗争粮",
            "徐州·下邳",
            20,
            10,
            true
        ))
        chapters.add(ChapterDef(
            3,
            "吕布",
            "第4章 吕布",
            "吕布章",
            "吕×曹 · 下邳同仓",
            "吕×曹 · 下邳同仓",
            "吕×曹 · 下邳同仓",
            "吕布",
            "下邳同仓",
            "下邳",
            30,
            10,
            true
        ))
        chapters.add(ChapterDef(
            4,
            "投袁",
            "第5章 投袁",
            "投袁·邺",
            "乌巢仓破、半印失散；北不可回",
            "袁绍×曹操 · 袁×曹 · 邺",
            "袁绍×曹操 · 袁×曹 · 邺",
            "袁→备",
            "乌巢仓破、半印失散；北不可回",
            "邺（乌巢仓影可辅）",
            40,
            10,
            true
        ))
        chapters.add(ChapterDef(
            5,
            "荆州",
            "第6章 荆州",
            "荆州·襄阳",
            "刘表辖下友道；不给曹营送",
            "刘备×曹操 · 刘×曹 · 襄阳",
            "刘备×曹操 · 刘×曹 · 襄阳",
            "刘表",
            "刘表辖下友道；不给曹营送",
            "襄阳",
            50,
            10,
            true
        ))
        chapters.add(ChapterDef(
            6,
            "赤壁",
            "第7章 赤壁",
            "赤壁·柴桑",
            "孙刘联军岸；不往乌林送曹营",
            "孙权×曹操 · 孙×曹 · 柴桑",
            "孙权×曹操 · 孙×曹 · 柴桑",
            "孙刘",
            "孙刘联军岸；不往乌林送曹营",
            "柴桑",
            60,
            10,
            true
        ))
        chapters.add(ChapterDef(
            7,
            "入蜀",
            "第8章 入蜀",
            "入蜀·白水关",
            "峡江入川关隘递进；非曹粮道，勿挂曹脸",
            "刘备×关隘影 · 刘×纹样 · 白水关",
            "刘备×关隘影 · 刘×纹样 · 白水关",
            "蜀",
            "峡江入川关隘递进；非曹粮道勿挂曹脸",
            "白水关辅成都",
            70,
            10,
            true
        ))
        chapters.add(ChapterDef(
            8,
            "汉中南中",
            "第9章 汉中南中",
            "汉中南中·阳平关",
            "两道分运：汉中关城 vs 南中北运",
            "诸葛×曹操 · 诸葛×曹 · 阳平关",
            "诸葛×曹操 · 诸葛×曹 · 阳平关",
            "诸葛",
            "两道分运：汉中关城 vs 南中北运",
            "阳平关",
            80,
            10,
            true
        ))
        chapters.add(ChapterDef(
            9,
            "北伐",
            "第10章 北伐",
            "北伐·五丈原",
            "对魏远征；街亭/空仓余韵",
            "诸葛×司马 · 诸葛×司马 · 五丈原",
            "诸葛×司马 · 诸葛×司马 · 五丈原",
            "诸葛",
            "对魏远征；街亭/空仓余韵",
            "五丈原",
            90,
            10,
            true
        ))
        return chapters
    }

    public static func byIndex(index: Int64): ChapterDef {
        return ChapterCatalog.all()[index]
    }

    public static func count(): Int64 {
        return ChapterCatalog.all().size
    }

    public static func isOpen(chapterId: Int64, cleared: Int64): Bool {
        let ch = ChapterCatalog.byIndex(chapterId)
        if (!ch.open) {
            return false
        }
        if (ch.levelCount <= 0) {
            return false
        }
        return cleared >= ch.levelStart
    }

    public static func selectable(chapterId: Int64, cleared: Int64): Bool {
        return ChapterCatalog.isOpen(chapterId, cleared)
    }

    /* 05–10: skin-only. Tap opens fullscreen preview, never gameplay. */
    public static func hasSkinPreview(chapterId: Int64): Bool {
        return chapterId >= 4 && chapterId <= 9
    }

    public static func openCount(cleared: Int64): Int64 {
        var n: Int64 = 0
        var i: Int64 = 0
        while (i < ChapterCatalog.count()) {
            if (ChapterCatalog.isOpen(i, cleared)) {
                n = n + 1
            }
            i = i + 1
        }
        return n
    }

    // boards-locked 的 dessert 字段; mobile/shared/levels/levels.json 不带 dessert 键且按现有测试不得带, 所以这里是该数据的镜像, 由 scripts/check_ui_diffs.py 与 boards-locked 对账
    public static func dessertIds(): Array<Int64> {
        return [4, 14, 24, 34, 44, 54, 64, 74, 84, 94]
    }

    public static func isDessert(levelId: Int64): Bool {
        let ids = ChapterCatalog.dessertIds()
        var i: Int64 = 0
        while (i < ids.size) {
            if (ids[i] == levelId) {
                return true
            }
            i = i + 1
        }
        return false
    }

    public static func dessertCount(): Int64 {
        return ChapterCatalog.dessertIds().size
    }

    public static func yichengFooter(cleared: Int64, total: Int64, currentName: String): String {
        if (total > 0 && cleared >= total) {
            return SummaryCopy.footer(total)
        }
        return "已通 ${cleared} · 当前 ${currentName}"
    }

    public static func chapterListFooterText(chapterId: Int64, cleared: Int64, levels: ArrayList<LevelDef>): String {
        let ch = ChapterCatalog.byIndex(chapterId)
        let n = ChapterCatalog.clearedCount(chapterId, cleared)
        var dims = ""
        if (ch.levelStart < levels.size) {
            let board = levels[ch.levelStart]
            dims = " · ${board.cols}×${board.rows}"
        }
        if (ch.levelCount > 0 && n >= ch.levelCount) {
            if (chapterId < ChapterCatalog.count() - 1) {
                let nextCh = ChapterCatalog.byIndex(chapterId + 1)
                return "已通 ${n} · 本章全通 · 下一章 ${nextCh.name} · 共10驿${dims}"
            } else {
                return "已通 ${n} · 本章全通 · 驿路终章 · 共10驿${dims}"
            }
        }
        var curName = ""
        if (!ChapterCatalog.isOpen(ch.id, cleared)) {
            curName = "未开"
        } else if (cleared < ch.levelStart) {
            if (ch.levelStart < levels.size) {
                curName = levels[ch.levelStart].name
            }
        } else if (cleared < levels.size) {
            curName = levels[cleared].name
        }
        return "已通 ${n} · 当前${curName} · 共10驿${dims}"
    }

    public static func chapterListFooterLines(
        chapterId: Int64,
        cleared: Int64,
        levels: ArrayList<LevelDef>,
        winW: Float64
    ): Array<String> {
        let full = ChapterCatalog.chapterListFooterText(chapterId, cleared, levels)
        let ch = ChapterCatalog.byIndex(chapterId)
        let n = ChapterCatalog.clearedCount(chapterId, cleared)
        let isAllClear = (ch.levelCount > 0 && n >= ch.levelCount)
        if (isAllClear) {
            if (footerNeedsTwoLines(full, winW)) {
                var dims = ""
                if (ch.levelStart < levels.size) {
                    let board = levels[ch.levelStart]
                    dims = " · ${board.cols}×${board.rows}"
                }
                let l1 = "已通 ${n} · 本章全通"
                var l2 = ""
                if (chapterId < ChapterCatalog.count() - 1) {
                    let nextCh = ChapterCatalog.byIndex(chapterId + 1)
                    l2 = "下一章 ${nextCh.name} · 共10驿${dims}"
                } else {
                    l2 = "驿路终章 · 共10驿${dims}"
                }
                return [l1, l2]
            }
            return [full]
        }
        var curName = ""
        if (!ChapterCatalog.isOpen(ch.id, cleared)) {
            curName = "未开"
        } else if (cleared < ch.levelStart) {
            if (ch.levelStart < levels.size) {
                curName = levels[ch.levelStart].name
            }
        } else if (cleared < levels.size) {
            curName = levels[cleared].name
        }
        var dims = ""
        if (ch.levelStart < levels.size) {
            let board = levels[ch.levelStart]
            dims = " · ${board.cols}×${board.rows}"
        }
        return footerCurrentLines(n, curName, dims, winW)
    }

    public static func groupState(chapterId: Int64, cleared: Int64): Int64 {
        let ch = ChapterCatalog.byIndex(chapterId)
        if (cleared < ch.levelStart) {
            return 2
        }
        if (ch.levelCount > 0 && ChapterCatalog.clearedCount(chapterId, cleared) >= ch.levelCount) {
            return 1
        }
        return 0
    }

    public static func groupHeaderRight(chapterId: Int64, cleared: Int64): String {
        let ch = ChapterCatalog.byIndex(chapterId)
        let st = ChapterCatalog.groupState(chapterId, cleared)
        if (st == 1) {
            return "全通 ${ch.levelCount} / ${ch.levelCount}"
        }
        if (st == 2) {
            return "未开"
        }
        let n = ChapterCatalog.clearedCount(chapterId, cleared)
        return "已通 ${n} / ${ch.levelCount}"
    }

    public static func groupIsCurrent(chapterId: Int64, cleared: Int64): Bool {
        let ch = ChapterCatalog.byIndex(chapterId)
        if (ch.levelCount <= 0) {
            return false
        }
        return cleared >= ch.levelStart && cleared < ch.levelStart + ch.levelCount
    }


    public static func clearedCount(chapterId: Int64, cleared: Int64): Int64 {
        let ch = ChapterCatalog.byIndex(chapterId)
        if (ch.levelCount <= 0) {
            return 0
        }
        if (cleared <= ch.levelStart) {
            return 0
        }
        let n = cleared - ch.levelStart
        if (n >= ch.levelCount) {
            return ch.levelCount
        }
        return n
    }

    public static func chapterIdForLevel(levelIndex: Int64): Int64 {
        var i: Int64 = 0
        while (i < ChapterCatalog.count()) {
            let ch = ChapterCatalog.byIndex(i)
            if (ch.levelCount > 0 && levelIndex >= ch.levelStart &&
                levelIndex < ch.levelStart + ch.levelCount) {
                return ch.id
            }
            i = i + 1
        }
        return 0
    }

    public static func levelsOf(chapterId: Int64, levels: ArrayList<LevelDef>): ArrayList<LevelDef> {
        let ch = ChapterCatalog.byIndex(chapterId)
        let out = ArrayList<LevelDef>()
        if (ch.levelCount <= 0) {
            return out
        }
        var i: Int64 = 0
        while (i < ch.levelCount) {
            if (ch.levelStart + i < levels.size) {
                out.add(levels[ch.levelStart + i])
            }
            i = i + 1
        }
        return out
    }
}

/* 驿程全表百驿全通总结卡(B7)文案集中处:render_cjmp_gaps_v1.draw_summary。
   文案已由作家定稿(COPY_ALLCLEAR_20261004.md);若再改标题,只改 title() 这一处,
   页脚/subtitle/sealChars 全部经它引用,index.cj 与页脚不得另写字面量。 */
public class SummaryCopy {
    // 作家定稿标题「驿路全通」;换文案只改这一行
    public static func title(): String {
        return "驿路全通"
    }

    public static func subtitle(total: Int64): String {
        return "已通 ${total} / ${total} · 十章皆通"
    }

    public static func sealChars(): Array<String> {
        return ["全", "通"]
    }

    public static func footer(total: Int64): String {
        return "已通 ${total} · ${SummaryCopy.title()}"
    }

    /* 总结卡可见性:cleared >= total 且 total > 0。 */
    public static func summaryVisible(cleared: Int64, total: Int64): Bool {
        return cleared >= total && total > 0
    }
}

/* 总结卡(B7)几何常量:draw_summary(SUMMARY_H=88、rrect r8、左内边 16、
   title y+30 serif 20、line y+58 sans 12)与 make_seal(size=147px=56u, 2.625 px/u, 旋转 -8°)。
   朱印各值按 make_seal(147px) 公式取 px/2.625 结果,注释标明公式。 */
public class SummaryGeom {
    public static func cardH(): Float64 { return 88.0 } /* SUMMARY_H */
    public static func radius(): Float64 { return 8.0 } /* 卡圆角 rrect 8 */
    public static func padLeft(): Float64 { return 16.0 }
    public static func padRight(): Float64 { return 16.0 }
    public static func titleCenterY(): Float64 { return 30.0 }
    public static func lineCenterY(): Float64 { return 58.0 }
    public static func titleFont(): Float64 { return 20.0 }
    public static func lineFont(): Float64 { return 12.0 }
    public static func gapBelow(): Float64 { return 12.0 }
    public static func sealSize(): Float64 { return 56.0 }
    public static func sealAngle(): Float64 { return -8.0 } /* rotate(-8) */

    /* 朱印 make_seal(147px) 公式, 2.625 px/u */
    public static func sealFrameInset(): Float64 { return 9.0 / 2.625 } /* m=max(2,147//16)=9px ≈ 3.4286u */
    public static func sealFrameW(): Float64 { return 9.0 / 2.625 } /* max(2,147//16)=9px ≈ 3.4286u */
    public static func sealFrameR(): Float64 { return 10.0 / 2.625 } /* 147//14=10px ≈ 3.8095u */
    public static func sealInnerInset(): Float64 { return 25.0 / 2.625 } /* m+147//9=9+16=25px ≈ 9.5238u */
    public static func sealInnerW(): Float64 { return 4.0 / 2.625 } /* max(1,147//30)=4px ≈ 1.5238u */
    public static func sealInnerR(): Float64 { return 7.0 / 2.625 } /* 147//20=7px ≈ 2.6667u */
    public static func sealFont(): Float64 { return 44.0 / 2.625 } /* int(147*0.30)=44px ≈ 16.7619u */
    public static func sealLineStep(): Float64 { return 1.02 } /* 字间距系数 */
    public static func sealAlpha(): Float64 { return 0.92 } /* 235/255 */
}

/* 首页「章节 · 驿程」文字链与点击区几何 (SPEC_A1_ADDENDUM §3.3 & RULINGS_ABF56B0)。
   推导 (相对屏幕中线 x=0):
   - 内容总宽 = blockW(64) + gap(12) + blockW(64) = 140
   - 无偏移居中为 [-70, +70], 整行向右偏移 +2 (centerShift=2.0) 得到:
     章节块 [chapterX0, chapterX1] = [-68, -4]
     圆点空档 [-4, +8], 4×4 圆点居中于 dotCenterX = +2
     驿程块 [yichengX0, yichengX1] = [+8, +72]
   - 外层 Column 居中机制下, Row 设置 rowMarginLeft = 4 (排版槽 144 居中于 [-72, +72]),
     使内容整体中心落在 +2, 各块精准对应上述区间, 两块互不相交。 */
public class HomeLinkGeom {
    public static const blockW: Int64 = 64
    public static const blockH: Int64 = 44
    public static const gap: Int64 = 12
    public static const dotSize: Int64 = 4
    public static const dotRadius: Int64 = 2
    public static const dotMarginLR: Int64 = 4
    public static const underlineW: Int64 = 32 // 2 chars * 16 fontSize
    public static const underlineH: Float64 = 1.2
    public static const underlineMarginTop: Int64 = 2
    public static const centerShift: Float64 = 2.0
    public static const rowMarginLeft: Int64 = 4 // 2 * centerShift = 4 to shift centered 140w content right by 2
    public static const rowMarginTop: Int64 = 2

    public static func chapterX0(): Int64 { return -68 }
    public static func chapterX1(): Int64 { return -4 }
    public static func yichengX0(): Int64 { return 8 }
    public static func yichengX1(): Int64 { return 72 }
    public static func dotCenterX(): Float64 { return 2.0 }
    public static func rowShift(): Float64 { return 2.0 }
}

/*
 * 页脚 Sans 12 字符 advance 表 (12u 未取整宽度 = advance / unitsPerEm * 12.0)。
 * 字体来源: mobile/cjmp/fonts/YiluSans-Regular.ttf (unitsPerEm = 1000)
 * 生成/验证方式 (Python TTFont / fontTools):
 *     from fontTools.ttLib import TTFont
 *     font = TTFont('mobile/cjmp/fonts/YiluSans-Regular.ttf')
 *     upem = font['head'].unitsPerEm
 *     hmtx = font['hmtx']
 *     cmap = font.getBestCmap()
 *     chars = '已通 0123456789·本章全下一平原徐州吕布投袁荆州赤壁入蜀汉中南北伐驿路终共×/当前'
 *     for ch in sorted(set(chars)):
 *         code = ord(ch)
 *         g = cmap[code]
 *         adv, _ = hmtx[g]
 *         print(f'{ch} (U+{code:04X}): {adv} -> {adv/upem*12.0:.4f}')
 * 字符 advance 数据 (12u 未取整):
 *   ' ' (U+0020): advance=224 -> 2.688 u
 *   '/' (U+002F): advance=392 -> 4.704 u
 *   '0'..'9' (U+0030..U+0039): advance=555 -> 6.66 u
 *   '·' (U+00B7): advance=1000 -> 12.0 u
 *   '×' (U+00D7): advance=1000 -> 12.0 u
 *   所有中文字符及全角标点: advance=1000 -> 12.0 u
 *   不在表中的字符缺省按 12.0 u 计
 * 校验值 (整串 12u 真实 advance 之和):
 *   ch1 (涿郡→平原, 6×6): 282.84 u
 *   ch8 (入蜀→汉中南中, 7×7): 306.84 u
 *   ch10 (北伐驿路终章, 7×7): 268.152 u (~268.15 u)
 */
func footerRuneAdvance(r: Rune): Float64 {
    if (r == r' ') {
        return 2.688
    } else if (r == r'/') {
        return 4.704
    } else if (r >= r'0' && r <= r'9') {
        return 6.66
    }
    return 12.0
}

public func footerTextWidth(s: String): Float64 {
    var total: Float64 = 0.0
    for (r in s.toRuneArray()) {
        total += footerRuneAdvance(r)
    }
    return total
}

public func footerSlack(): Float64 {
    return 0.5
}

public func footerWidthOverflows(w: Float64, avail: Float64): Bool {
    return w > avail + footerSlack()
}

public func footerNeedsTwoLines(text: String, winW: Float64): Bool {
    return footerWidthOverflows(footerTextWidth(text), winW - 40.0)
}

func footerStrStartsWith(s: String, prefix: String): Bool {
    if (s.size < prefix.size) {
        return false
    }
    var i: Int64 = 0
    while (i < prefix.size) {
        match (s.get(i)) {
            case Some(b1) => match (prefix.get(i)) {
                case Some(b2) => if (b1 != b2) { return false }
                case None => return false
            }
            case None => return false
        }
        i = i + 1
    }
    return true
}

public func footerCurrentLines(n: Int64, curName: String, dims: String, winW: Float64): Array<String> {
    var dimsPart = dims
    if (dimsPart.size > 0 && !footerStrStartsWith(dimsPart, " · ")) {
        dimsPart = " · " + dimsPart
    }
    let full = "已通 ${n} · 当前${curName} · 共10驿${dimsPart}"
    if (footerNeedsTwoLines(full, winW)) {
        let l1 = "已通 ${n} · 当前${curName}"
        let l2 = "共10驿${dimsPart}"
        return [l1, l2]
    }
    return [full]
}

/* 驿程全表行与章内驿程行几何与字号规格 (SPEC B3–B7, 06-levels, RULINGS_ABF56B0, render_cjmp_gaps_v1).
   全表(global): h64, ringR 14, ringD 28, numFont 14(Serif Bold), nameFont 20(Serif Bold),
     metaFont 12(Sans), padLeft 14, nameGap 16, statusRightInset 16, lockRight 28 (lockCx=W-48,
     rowRight=W-20 -> (W-20)-(W-48)=28), badgeFont 12.
     环心 x=48 (pageInset 20 + padLeft 14 + ringR 14 = 48), 驿名左缘 x=78 (48 + 14 + 16 = 78).
   章内(chapter): h52, ringR 13, ringD 26, numFont 13(Serif Bold), nameFont 16(Serif Bold),
     metaFont 11(Sans), padLeft 15, nameGap 13, statusRightInset 16, lockRight 18 (lockCx=W-38,
     rowRight=W-20 -> (W-20)-(W-38)=18), badgeFont 11.
     环心 x=48 (pageInset 20 + padLeft 15 + ringR 13 = 48), 驿名左缘 x=74 (48 + 13 + 13 = 74). */
public class StationRowGeom {
    public var rowH: Int64
    public var ringR: Int64
    public var numFont: Int64
    public var nameFont: Int64
    public var metaFont: Int64
    public var padLeft: Int64
    public var nameGap: Int64
    public var statusRightInset: Int64
    public var lockRight: Int64
    public var lockCx: Int64
    public var badgeFont: Int64

    public init(
        rowH: Int64,
        ringR: Int64,
        numFont: Int64,
        nameFont: Int64,
        metaFont: Int64,
        padLeft: Int64,
        nameGap: Int64,
        statusRightInset: Int64,
        lockRight: Int64,
        badgeFont: Int64
    ) {
        this.rowH = rowH
        this.ringR = ringR
        this.numFont = numFont
        this.nameFont = nameFont
        this.metaFont = metaFont
        this.padLeft = padLeft
        this.nameGap = nameGap
        this.statusRightInset = statusRightInset
        this.lockRight = lockRight
        this.lockCx = lockRight
        this.badgeFont = badgeFont
    }

    public func ringD(): Int64 {
        return this.ringR * 2
    }

    public func ringDiameter(): Int64 {
        return this.ringR * 2
    }

    public static func global(): StationRowGeom {
        return StationRowGeom(
            64, 14, 14, 20, 12, 14, 16, 16, 28, 12
        )
    }

    public static func chapter(): StationRowGeom {
        return StationRowGeom(
            52, 13, 13, 16, 11, 15, 13, 16, 18, 11
        )
    }

    // Static constants for direct access
    public static const globalRowH: Int64 = 64
    public static const globalRingR: Int64 = 14
    public static const globalRingD: Int64 = 28
    public static const globalNumFont: Int64 = 14
    public static const globalNameFont: Int64 = 20
    public static const globalMetaFont: Int64 = 12
    public static const globalPadLeft: Int64 = 14
    public static const globalNameGap: Int64 = 16
    public static const globalStatusRightInset: Int64 = 16
    public static const globalLockRight: Int64 = 28
    public static const globalLockCx: Int64 = 28
    public static const globalBadgeFont: Int64 = 12

    public static const chapterRowH: Int64 = 52
    public static const chapterRingR: Int64 = 13
    public static const chapterRingD: Int64 = 26
    public static const chapterNumFont: Int64 = 13
    public static const chapterNameFont: Int64 = 16
    public static const chapterMetaFont: Int64 = 11
    public static const chapterPadLeft: Int64 = 15
    public static const chapterNameGap: Int64 = 13
    public static const chapterStatusRightInset: Int64 = 16
    public static const chapterLockRight: Int64 = 18
    public static const chapterLockCx: Int64 = 18
    public static const chapterBadgeFont: Int64 = 11
}


