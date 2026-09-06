package ohos_app_cangjie_entry

/* chapter-flow v1.3 SHIP cards over LevelCatalog.
   OPEN: 涿郡 (0–9), 平原 (10–19). LOCKED cards only: 徐州, 吕布 — no boards. */
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

    public func chromeLine(): String {
        return "友：${this.friendLine} · 张力：${this.tensionLine} · 城：${this.cityLine}"
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
            0,
            false
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
            20,
            0,
            false
        ))
        return chapters
    }

    public static func byIndex(index: Int64): ChapterDef {
        return ChapterCatalog.all()[index]
    }

    public static func count(): Int64 {
        return ChapterCatalog.all().size
    }

    public static func selectable(chapterId: Int64): Bool {
        return ChapterCatalog.byIndex(chapterId).open
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

    public static func levelsOf(chapterId: Int64): ArrayList<LevelDef> {
        let ch = ChapterCatalog.byIndex(chapterId)
        let out = ArrayList<LevelDef>()
        if (ch.levelCount <= 0) {
            return out
        }
        let all = LevelCatalog.all()
        var i: Int64 = 0
        while (i < ch.levelCount) {
            out.add(all[ch.levelStart + i])
            i = i + 1
        }
        return out
    }
}
