package ohos_app_cangjie_entry

/* Generated from resources/rawfile/levels.json. Do not invent levels here. */
import std.collection.ArrayList
import ohos_app_cangjie_entry.engine.Wall
import ohos_app_cangjie_entry.game.{LevelDef, Waypoint}

public class LevelCatalog {
    public static func all(): ArrayList<LevelDef> {
        let levels = ArrayList<LevelDef>()
        let wps0 = ArrayList<Waypoint>()
        wps0.add(Waypoint(1, 2, 0))
        wps0.add(Waypoint(2, 3, 2))
        wps0.add(Waypoint(3, 1, 4))
        wps0.add(Waypoint(4, 5, 5))
        wps0.add(Waypoint(5, 0, 7))
        let walls0 = ArrayList<Wall>()
        levels.add(LevelDef(0, "长安", 6, 8, wps0, walls0))

        let wps1 = ArrayList<Waypoint>()
        wps1.add(Waypoint(1, 0, 0))
        wps1.add(Waypoint(2, 2, 2))
        let walls1 = ArrayList<Wall>()
        levels.add(LevelDef(1, "长安", 3, 3, wps1, walls1))

        let wps2 = ArrayList<Waypoint>()
        wps2.add(Waypoint(1, 0, 0))
        wps2.add(Waypoint(2, 1, 1))
        wps2.add(Waypoint(3, 2, 2))
        let walls2 = ArrayList<Wall>()
        levels.add(LevelDef(2, "洛阳", 3, 3, wps2, walls2))

        let wps3 = ArrayList<Waypoint>()
        wps3.add(Waypoint(1, 0, 0))
        wps3.add(Waypoint(2, 2, 0))
        wps3.add(Waypoint(3, 0, 1))
        wps3.add(Waypoint(4, 2, 2))
        let walls3 = ArrayList<Wall>()
        levels.add(LevelDef(3, "汴梁", 3, 3, wps3, walls3))

        let wps4 = ArrayList<Waypoint>()
        wps4.add(Waypoint(1, 0, 0))
        wps4.add(Waypoint(2, 3, 3))
        wps4.add(Waypoint(3, 1, 2))
        let walls4 = ArrayList<Wall>()
        levels.add(LevelDef(4, "扬州", 4, 4, wps4, walls4))

        let wps5 = ArrayList<Waypoint>()
        wps5.add(Waypoint(1, 0, 0))
        wps5.add(Waypoint(2, 3, 0))
        wps5.add(Waypoint(3, 0, 3))
        wps5.add(Waypoint(4, 1, 2))
        let walls5 = ArrayList<Wall>()
        levels.add(LevelDef(5, "杭州", 4, 4, wps5, walls5))

        let wps6 = ArrayList<Waypoint>()
        wps6.add(Waypoint(1, 0, 0))
        wps6.add(Waypoint(2, 3, 1))
        wps6.add(Waypoint(3, 0, 2))
        wps6.add(Waypoint(4, 2, 1))
        wps6.add(Waypoint(5, 1, 2))
        let walls6 = ArrayList<Wall>()
        levels.add(LevelDef(6, "苏州", 4, 4, wps6, walls6))

        let wps7 = ArrayList<Waypoint>()
        wps7.add(Waypoint(1, 0, 0))
        wps7.add(Waypoint(2, 3, 2))
        wps7.add(Waypoint(3, 1, 1))
        wps7.add(Waypoint(4, 1, 2))
        let walls7 = ArrayList<Wall>()
        walls7.add(Wall(1, 0, 1, 1))
        levels.add(LevelDef(7, "凉州", 4, 4, wps7, walls7))

        let wps8 = ArrayList<Waypoint>()
        wps8.add(Waypoint(1, 0, 0))
        wps8.add(Waypoint(2, 1, 0))
        wps8.add(Waypoint(3, 2, 4))
        wps8.add(Waypoint(4, 4, 4))
        let walls8 = ArrayList<Wall>()
        walls8.add(Wall(0, 1, 1, 1))
        levels.add(LevelDef(8, "敦煌", 5, 5, wps8, walls8))

        let wps9 = ArrayList<Waypoint>()
        wps9.add(Waypoint(1, 0, 0))
        wps9.add(Waypoint(2, 4, 0))
        wps9.add(Waypoint(3, 0, 2))
        wps9.add(Waypoint(4, 4, 3))
        wps9.add(Waypoint(5, 4, 4))
        let walls9 = ArrayList<Wall>()
        walls9.add(Wall(1, 0, 1, 1))
        walls9.add(Wall(2, 2, 2, 3))
        levels.add(LevelDef(9, "肃州", 5, 5, wps9, walls9))

        let wps10 = ArrayList<Waypoint>()
        wps10.add(Waypoint(1, 0, 0))
        wps10.add(Waypoint(2, 4, 4))
        wps10.add(Waypoint(3, 0, 1))
        wps10.add(Waypoint(4, 3, 3))
        wps10.add(Waypoint(5, 2, 2))
        let walls10 = ArrayList<Wall>()
        walls10.add(Wall(1, 0, 1, 1))
        walls10.add(Wall(2, 0, 2, 1))
        levels.add(LevelDef(10, "滑州", 5, 5, wps10, walls10))

        let wps11 = ArrayList<Waypoint>()
        wps11.add(Waypoint(1, 0, 0))
        wps11.add(Waypoint(2, 0, 4))
        wps11.add(Waypoint(3, 1, 0))
        wps11.add(Waypoint(4, 3, 4))
        wps11.add(Waypoint(5, 3, 0))
        wps11.add(Waypoint(6, 4, 4))
        let walls11 = ArrayList<Wall>()
        walls11.add(Wall(0, 0, 1, 0))
        walls11.add(Wall(2, 1, 3, 1))
        walls11.add(Wall(1, 2, 2, 2))
        levels.add(LevelDef(11, "通州", 5, 5, wps11, walls11))

        let wps12 = ArrayList<Waypoint>()
        wps12.add(Waypoint(1, 0, 0))
        wps12.add(Waypoint(2, 2, 0))
        wps12.add(Waypoint(3, 0, 1))
        wps12.add(Waypoint(4, 2, 2))
        wps12.add(Waypoint(5, 0, 3))
        wps12.add(Waypoint(6, 4, 4))
        let walls12 = ArrayList<Wall>()
        walls12.add(Wall(0, 0, 0, 1))
        walls12.add(Wall(3, 1, 3, 2))
        walls12.add(Wall(1, 3, 1, 4))
        levels.add(LevelDef(12, "济宁", 5, 5, wps12, walls12))

        return levels
    }

    public static func byIndex(index: Int64): LevelDef {
        return LevelCatalog.all()[index]
    }

    public static func count(): Int64 {
        return LevelCatalog.all().size
    }
}
