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
    let parser = JsonParser(readTextFileAny(lockedFileCandidates(files[id / 10])))
    let root = parser.parseValue()
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
