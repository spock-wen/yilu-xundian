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

    public static func isDessert(levelId: Int64): Bool {
        /* SHIP 点心: 涿郡·中山. Mock 第5驿 = JSON id 4. */
        return levelId == 4
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
