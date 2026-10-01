package yilu_zip_test

/* 测试辅助:文件读取、levels.json 加载、boards-locked 归档路径读取。
   失败语义(readTextFile):失败时直接抛出 std.fs 的 FSException,不返回 "ERR:"
   前缀串 —— 异常消息自带原始路径;多候选路径的汇总报错见 readTextFileAny。 */
import std.fs.*
import std.collection.ArrayList
import std.unittest.*
import std.unittest.testmacro.*
import yilu_zip.engine.*
import yilu_zip.game.*

/* 读整个文件为 String;文件不存在/不可读时抛 FSException(见文件头注释)。 */
public func readTextFile(path: String): String {
    let bytes = File.readFrom(path)
    return unsafe { String.fromUtf8Unchecked(bytes) }
}

/* 逐个尝试候选路径,返回第一个存在者的内容;全部失败时抛 FSException 并列出候选。 */
public func readTextFileAny(candidates: Array<String>): String {
    var tried = ""
    for (p in candidates) {
        if (exists(p)) {
            return readTextFile(p)
        }
        tried = tried + p + "; "
    }
    throw FSException("no candidate file readable, tried: " + tried)
}

/* levels.json 的候选相对路径:cwd 为 shared-test / mobile / 仓库根 / shared 均可。 */
func levelsCandidates(): Array<String> {
    return ["../shared/levels/levels.json", "shared/levels/levels.json",
            "mobile/shared/levels/levels.json", "levels/levels.json"]
}

/* 读入 100 关。解析出错时 @Assert(loaded.error, "") 失败,断言输出里带 error 串。 */
public func loadAllLevels(): ArrayList<LevelDef> {
    let loaded = levelsFromJson(readTextFileAny(levelsCandidates()))
    @Assert(loaded.error, "")
    return loaded.levels
}

/* 与 tools/build_levels.py 的 LOCKED_FILES 相同的 10 个文件名,顺序一致。 */
/* 引擎 JsonParser.parseNumber 只读整数(shared/src/game/json_level.cj:281-311):
   吃完整数位就返回,若下一位是 '.',parseObject 随即 markFailed("expected , or ]")。
   boards-locked 有少量浮点元数据(decision_span/on_path_pct/mean_deg 等),与解法无关。
   JSON 中 '.' 只出现在数字和字符串内;本测试只读 boards[tip].path(整数数组),
   结构与整数不受影响,故解析前删掉全部 '.' 作为测试侧规避。引擎不改,限制另行报告。 */
public func stripDecimalDots(text: String): String {
    let out = ArrayList<UInt8>()
    var i: Int64 = 0
    while (i < text.size) {
        match (text.get(i)) {
            case Some(b) =>
                if (b != 46u8) { /* '.' */
                    out.add(b)
                }
            case None => ()
        }
        i = i + 1
    }
    if (out.size == 0) {
        return ""
    }
    let arr = Array<UInt8>(out.size, {idx =>
        match (out.get(idx)) {
            case Some(b) => b
            case None => 0u8
        }
    })
    return unsafe { String.fromUtf8Unchecked(arr) }
}

public func lockedFiles(): Array<String> {
    return ["ch1_zhuo.json", "ch2_pingyuan.json", "ch3_xuzhou.json",
            "ch4_lvbu.json", "ch5_touyuan.json", "ch6_jingzhou.json",
            "ch7_chibi.json", "ch8_rushu.json", "ch9_hanzhong.json",
            "ch10_beifa.json"]
}

/* boards-locked 下某文件的候选路径:cwd 为 shared-test / 仓库根 / mobile 均可。 */
func lockedFileCandidates(fname: String): Array<String> {
    return ["../../boards-locked/" + fname, "boards-locked/" + fname,
            "../boards-locked/" + fname]
}

/* json_level.cj 的 jsonField 是包内私有,这里实现等价的字段查找。 */
func field(obj: JsonVal, key: String): Option<JsonVal> {
    var i: Int64 = 0
    while (i < obj.fields.size) {
        match (obj.fields.get(i)) {
            case None => return None
            case Some(f) =>
                if (f.key == key) {
                    return Some(f.val)
                }
        }
        i = i + 1
    }
    return None
}

/* schema [r,c] → engine Cell(x=c 列, y=r 行);形状不对返回 None。 */
func rcCell(v: JsonVal): Option<Cell> {
    if (v.kind != 4 || v.arr.size != 2) {
        return None
    }
    let rv = v.arr[0]
    let cv = v.arr[1]
    if (rv.kind != 2 || cv.kind != 2) {
        return None
    }
    return Some(Cell(cv.intVal, rv.intVal))
}

/* 全局 id = 章序*10 + 盘序 → 归档 path([[r,c],…]) 转成 ArrayList<Cell>。
   id 越界 / JSON 解析失败 / path 缺失为空时 @Assert 失败,停止用例。 */
public func lockedPath(id: Int64): ArrayList<Cell> {
    let files = lockedFiles()
    @Assert(id >= 0 && id / 10 < files.size)
    let tip = id % 10
    let parser = JsonParser(stripDecimalDots(readTextFileAny(lockedFileCandidates(files[id / 10]))))
    let root = parser.parseValue()
    if (parser.failed || root.kind != 5) { /* 先打印再断言:断言会中止用例,留下定位线索 */
        println("LOCKED_PATH_PARSE_FAIL id=${id} failed=${parser.failed} rootKind=${root.kind} msg=${parser.message}")
    }
    @Assert(!parser.failed && root.kind == 5)
    let cells = ArrayList<Cell>()
    match (field(root, "boards")) {
        case Some(bv) =>
            if (bv.kind == 4) {
                match (bv.arr.get(tip)) {
                    case Some(board) =>
                        match (field(board, "path")) {
                            case Some(pv) =>
                                if (pv.kind == 4) {
                                    for (item in pv.arr) {
                                        match (rcCell(item)) {
                                            case Some(cell) => cells.add(cell)
                                            case None => ()
                                        }
                                    }
                                }
                            case None => ()
                        }
                    case None => ()
                }
            }
        case None => ()
    }
    @Assert(cells.size > 0)
    return cells
}

/* 手工小棋盘:clues=(n,x,y) 即 (编号,列,行);机制字段留空,由用例自行赋值。 */
public func mkLevel(cols: Int64, rows: Int64, clues: Array<(Int64, Int64, Int64)>): LevelDef {
    let wps = ArrayList<Waypoint>()
    for (c in clues) {
        wps.add(Waypoint(c[0], c[1], c[2]))
    }
    let stepLimit = cols * rows
    return LevelDef(0, "t", cols, rows, wps, ArrayList<Wall>(), ArrayList<ParityEdge>(), stepLimit)
}

/* 依次 tryStep 每一格;全部成功才 true,任一失败即 false。 */
public func stepAll(game: PatrolGame, cells: Array<(Int64, Int64)>): Bool {
    for (c in cells) {
        if (!game.tryStep(Cell(c[0], c[1]))) {
            return false
        }
    }
    return true
}
