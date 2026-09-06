package ohos_app_cangjie_entry

/* Chapter windows over LevelCatalog. Boards stay in levels.cj / levels.json.
   Selectable this round: 涿郡 (0–9), 平原 (10–19).
   Later chapters (not selectable): 徐州, 吕布 — designer skins pending. */
import std.collection.ArrayList
import ohos_app_cangjie_entry.game.LevelDef

public class ChapterDef {
    public var id: Int64
    public var name: String
    public var levelStart: Int64
    public var levelCount: Int64

    public init(id: Int64, name: String, levelStart: Int64, levelCount: Int64) {
        this.id = id
        this.name = name
        this.levelStart = levelStart
        this.levelCount = levelCount
    }
}

public class ChapterCatalog {
    public static func all(): ArrayList<ChapterDef> {
        let chapters = ArrayList<ChapterDef>()
        chapters.add(ChapterDef(0, "涿郡", 0, 10))
        chapters.add(ChapterDef(1, "平原", 10, 10))
        return chapters
    }

    public static func byIndex(index: Int64): ChapterDef {
        return ChapterCatalog.all()[index]
    }

    public static func count(): Int64 {
        return ChapterCatalog.all().size
    }

    public static func unlocked(chapterId: Int64, cleared: Int64): Bool {
        if (chapterId <= 0) {
            return true
        }
        let prev = ChapterCatalog.byIndex(chapterId - 1)
        return cleared >= prev.levelStart + prev.levelCount
    }

    public static func clearedCount(chapterId: Int64, cleared: Int64): Int64 {
        let ch = ChapterCatalog.byIndex(chapterId)
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
            if (levelIndex >= ch.levelStart && levelIndex < ch.levelStart + ch.levelCount) {
                return ch.id
            }
            i = i + 1
        }
        return 0
    }

    public static func levelsOf(chapterId: Int64): ArrayList<LevelDef> {
        let ch = ChapterCatalog.byIndex(chapterId)
        let all = LevelCatalog.all()
        let out = ArrayList<LevelDef>()
        var i: Int64 = 0
        while (i < ch.levelCount) {
            out.add(all[ch.levelStart + i])
            i = i + 1
        }
        return out
    }
}
