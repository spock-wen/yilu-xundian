package ohos_app_cangjie_entry

import std.collection.ArrayList
import ohos_app_cangjie_entry.game.{LevelDef, LevelsLoad, levelsFromJson}

public class LevelCatalog {
    public static func load(): ArrayList<LevelDef> {
        let res: LevelsLoad = levelsFromJson(levelsJsonText())
        if (res.error != "") {
            return ArrayList<LevelDef>()
        }
        return res.levels
    }

    public static func loadError(): String {
        let res: LevelsLoad = levelsFromJson(levelsJsonText())
        return res.error
    }
}
