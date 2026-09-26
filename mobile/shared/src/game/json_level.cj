package yilu_zip.game

import std.collection.ArrayList
import yilu_zip.engine.Wall

/* Minimal JSON reader for one levels.json object.
   String bytes are read with String.get, which returns None past the end
   (1.1.3 String <: Collection<Byte>). operator[] throws IndexOutOfBoundsException,
   and that exception's message interpolates the index through numberToString.
   On the iOS 1.1.3 runtime that formatting recurses until the stack guard
   (YiluXundian-2026-09-26-223058.ips). This loader returns an error string instead.
   https://cj-docs.gitcode.com/zh/1.1.3/libs/std/core/core_package_api/core_package_structs.html
   https://github.com/cangjielanguage/cangjie_runtime/blob/v1.1.3/stdlib/libs/std/core/array.cj
   parityEdges must be absent or empty: this loader does not construct ParityEdge values.
   stepLimit is stored on LevelDef and not enforced, same as PatrolGame in patrol.cj. */

func asciiDigit(d: Int64): String {
    if (d == 1) {
        return "1"
    }
    if (d == 2) {
        return "2"
    }
    if (d == 3) {
        return "3"
    }
    if (d == 4) {
        return "4"
    }
    if (d == 5) {
        return "5"
    }
    if (d == 6) {
        return "6"
    }
    if (d == 7) {
        return "7"
    }
    if (d == 8) {
        return "8"
    }
    if (d == 9) {
        return "9"
    }
    return "0"
}

/* Decimal without Int64.toString / StringBuilder.append. Those call numberToString,
   which is the frame that recurses in the iOS crash. */
func decimalText(n: Int64): String {
    if (n <= 0) {
        return "0"
    }
    var v = n
    var out = ""
    while (v > 0) {
        out = asciiDigit(v % 10) + out
        v = v / 10
    }
    return out
}

public class LevelLoad {
    public var level: Option<LevelDef>
    public var error: String

    public init(level: Option<LevelDef>, error: String) {
        this.level = level
        this.error = error
    }
}

public class JsonField {
    public var key: String
    public var val: JsonVal

    public init(key: String, val: JsonVal) {
        this.key = key
        this.val = val
    }
}

/* kind: 0 null, 1 bool, 2 int, 3 string, 4 array, 5 object */
public class JsonVal {
    public var kind: Int64
    public var boolVal: Bool
    public var intVal: Int64
    public var strVal: String
    public var arr: ArrayList<JsonVal>
    public var fields: ArrayList<JsonField>

    public init() {
        this.kind = 0
        this.boolVal = false
        this.intVal = 0
        this.strVal = ""
        this.arr = ArrayList<JsonVal>()
        this.fields = ArrayList<JsonField>()
    }
}

public class JsonParser {
    var text: String
    var i: Int64
    public var failed: Bool
    public var message: String

    public init(text: String) {
        this.text = text
        this.i = 0
        this.failed = false
        this.message = ""
    }

    public func eof(): Bool {
        return this.i >= this.text.size
    }

    func markFailed(message: String): Unit {
        if (this.failed) {
            return
        }
        this.failed = true
        this.message = "json at " + decimalText(this.i) + ": " + message
    }

    func current(): Option<UInt8> {
        return this.text.get(this.i)
    }

    public func skipWs(): Unit {
        while (!this.failed) {
            match (this.current()) {
                case None => return
                case Some(b) =>
                    if (b != 32u8 && b != 9u8 && b != 10u8 && b != 13u8) {
                        return
                    }
                    this.i = this.i + 1
            }
        }
    }

    func consumeByte(b: UInt8): Bool {
        match (this.current()) {
            case Some(got) =>
                if (got == b) {
                    this.i = this.i + 1
                    return true
                }
            case None => ()
        }
        this.markFailed("expected delimiter")
        return false
    }

    func consumeByteIf(b: UInt8): Bool {
        match (this.current()) {
            case Some(got) =>
                if (got == b) {
                    this.i = this.i + 1
                    return true
                }
            case None => ()
        }
        return false
    }

    func consumeLiteral(literal: String): Bool {
        var k: Int64 = 0
        while (k < literal.size) {
            match (this.current()) {
                case None =>
                    this.markFailed("bad literal")
                    return false
                case Some(b) =>
                    match (literal.get(k)) {
                        case None =>
                            this.markFailed("bad literal")
                            return false
                        case Some(lb) =>
                            if (b != lb) {
                                this.markFailed("bad literal")
                                return false
                            }
                    }
            }
            this.i = this.i + 1
            k = k + 1
        }
        return true
    }

    func bytesToString(list: ArrayList<UInt8>): String {
        let n = list.size
        if (n == 0) {
            return ""
        }
        let arr = Array<UInt8>(n, {idx =>
            match (list.get(idx)) {
                case Some(b) => b
                case None => 0u8
            }
        })
        return unsafe { String.fromUtf8Unchecked(arr) }
    }

    func parseString(): String {
        this.skipWs()
        if (!this.consumeByte(34u8)) {
            return ""
        }
        let bytes = ArrayList<UInt8>()
        while (!this.failed) {
            match (this.current()) {
                case None =>
                    this.markFailed("unterminated string")
                    return ""
                case Some(_) => ()
            }
            let b = match (this.current()) {
                case Some(got) => got
                case None => 0u8
            }
            this.i = this.i + 1
            if (b == 34u8) {
                return this.bytesToString(bytes)
            }
            if (b == 92u8) {
                match (this.current()) {
                    case None =>
                        this.markFailed("truncated escape")
                        return ""
                    case Some(_) => ()
                }
                let e = match (this.current()) {
                    case Some(got) => got
                    case None => 0u8
                }
                this.i = this.i + 1
                if (e == 34u8 || e == 92u8 || e == 47u8) {
                    bytes.add(e)
                } else if (e == 98u8) {
                    bytes.add(8u8)
                } else if (e == 102u8) {
                    bytes.add(12u8)
                } else if (e == 110u8) {
                    bytes.add(10u8)
                } else if (e == 114u8) {
                    bytes.add(13u8)
                } else if (e == 116u8) {
                    bytes.add(9u8)
                } else if (e == 117u8) {
                    this.markFailed("unicode u-escapes are not accepted; use UTF-8 text")
                    return ""
                } else {
                    this.markFailed("bad escape")
                    return ""
                }
            } else if (b < 32u8) {
                this.markFailed("raw control in string")
                return ""
            } else {
                bytes.add(b)
            }
        }
        this.markFailed("unterminated string")
        return ""
    }

    func parseNumber(): Int64 {
        var sign: Int64 = 1
        match (this.current()) {
            case Some(b) =>
                if (b == 45u8) {
                    sign = -1
                    this.i = this.i + 1
                }
            case None => ()
        }
        match (this.current()) {
            case None =>
                this.markFailed("expected digit")
                return 0
            case Some(b) =>
                if (b < 48u8 || b > 57u8) {
                    this.markFailed("expected digit")
                    return 0
                }
        }
        var n: Int64 = 0
        while (true) {
            match (this.current()) {
                case None => break
                case Some(b) =>
                    if (b < 48u8 || b > 57u8) {
                        break
                    }
                    this.i = this.i + 1
                    n = n * 10 + (Int64(b) - 48)
            }
        }
        match (this.current()) {
            case Some(b) =>
                if (b == 46u8 || b == 101u8 || b == 69u8) {
                    this.markFailed("only integers are accepted")
                    return 0
                }
            case None => ()
        }
        return n * sign
    }

    public func parseValue(): JsonVal {
        if (this.failed) {
            return JsonVal()
        }
        this.skipWs()
        let b = match (this.current()) {
            case None =>
                this.markFailed("unexpected end")
                return JsonVal()
            case Some(got) => got
        }
        if (b == 123u8) {
            return this.parseObject()
        }
        if (b == 91u8) {
            return this.parseArray()
        }
        if (b == 34u8) {
            let v = JsonVal()
            v.kind = 3
            v.strVal = this.parseString()
            return v
        }
        if (b == 116u8) {
            if (this.consumeLiteral("true")) {
                let v = JsonVal()
                v.kind = 1
                v.boolVal = true
                return v
            }
            return JsonVal()
        }
        if (b == 102u8) {
            if (this.consumeLiteral("false")) {
                let v = JsonVal()
                v.kind = 1
                v.boolVal = false
                return v
            }
            return JsonVal()
        }
        if (b == 110u8) {
            if (this.consumeLiteral("null")) {
                return JsonVal()
            }
            return JsonVal()
        }
        if (b == 45u8 || (b >= 48u8 && b <= 57u8)) {
            let v = JsonVal()
            v.kind = 2
            v.intVal = this.parseNumber()
            return v
        }
        this.markFailed("unexpected value")
        return JsonVal()
    }

    func parseArray(): JsonVal {
        let arr = JsonVal()
        arr.kind = 4
        if (!this.consumeByte(91u8)) {
            return arr
        }
        this.skipWs()
        if (this.consumeByteIf(93u8)) {
            return arr
        }
        while (!this.failed) {
            arr.arr.add(this.parseValue())
            if (this.failed) {
                return arr
            }
            this.skipWs()
            if (this.consumeByteIf(44u8)) {
                this.skipWs()
            } else if (this.consumeByte(93u8)) {
                return arr
            } else {
                this.markFailed("expected , or ]")
                return arr
            }
        }
        return arr
    }

    func parseObject(): JsonVal {
        let obj = JsonVal()
        obj.kind = 5
        if (!this.consumeByte(123u8)) {
            return obj
        }
        this.skipWs()
        if (this.consumeByteIf(125u8)) {
            return obj
        }
        while (!this.failed) {
            let key = this.parseString()
            if (this.failed) {
                return obj
            }
            this.skipWs()
            if (!this.consumeByte(58u8)) {
                return obj
            }
            let val = this.parseValue()
            obj.fields.add(JsonField(key, val))
            if (this.failed) {
                return obj
            }
            this.skipWs()
            if (this.consumeByteIf(44u8)) {
                this.skipWs()
            } else if (this.consumeByte(125u8)) {
                return obj
            } else {
                this.markFailed("expected , or }")
                return obj
            }
        }
        return obj
    }
}

func jsonField(obj: JsonVal, key: String): Option<JsonVal> {
    var i: Int64 = 0
    while (i < obj.fields.size) {
        match (obj.fields.get(i)) {
            case None => return None
            case Some(field) =>
                if (field.key == key) {
                    return Some(field.val)
                }
        }
        i = i + 1
    }
    return None
}

func readIntField(obj: JsonVal, key: String, err: LevelLoad): Int64 {
    match (jsonField(obj, key)) {
        case None =>
            err.error = "missing " + key
            return 0
        case Some(v) =>
            if (v.kind != 2) {
                err.error = key + " must be an int"
                return 0
            }
            return v.intVal
    }
}

public func blankLevel(): LevelDef {
    return LevelDef(
        0,
        "",
        0,
        0,
        ArrayList<Waypoint>(),
        ArrayList<Wall>(),
        ArrayList<ParityEdge>(),
        0
    )
}

public func levelFromJson(text: String): LevelLoad {
    let parser = JsonParser(text)
    let root = parser.parseValue()
    if (parser.failed) {
        return LevelLoad(None, parser.message)
    }
    parser.skipWs()
    if (!parser.eof()) {
        return LevelLoad(None, "trailing data after json value")
    }
    if (root.kind != 5) {
        return LevelLoad(None, "level json must be an object")
    }
    let scratch = LevelLoad(None, "")
    let id = readIntField(root, "id", scratch)
    if (scratch.error != "") {
        return scratch
    }
    let cols = readIntField(root, "cols", scratch)
    if (scratch.error != "") {
        return scratch
    }
    let rows = readIntField(root, "rows", scratch)
    if (scratch.error != "") {
        return scratch
    }
    if (cols <= 0 || rows <= 0) {
        return LevelLoad(None, "cols and rows must be positive")
    }
    var name = ""
    match (jsonField(root, "name")) {
        case None => return LevelLoad(None, "missing name")
        case Some(v) =>
            if (v.kind != 3) {
                return LevelLoad(None, "name must be a string")
            }
            name = v.strVal
    }
    let waypoints = ArrayList<Waypoint>()
    match (jsonField(root, "waypoints")) {
        case None => return LevelLoad(None, "missing waypoints")
        case Some(v) =>
            if (v.kind != 4) {
                return LevelLoad(None, "waypoints must be an array")
            }
            var i: Int64 = 0
            while (i < v.arr.size) {
                let item = match (v.arr.get(i)) {
                    case None => return LevelLoad(None, "waypoint index")
                    case Some(got) => got
                }
                if (item.kind != 5) {
                    return LevelLoad(None, "waypoint must be an object")
                }
                let n = readIntField(item, "n", scratch)
                if (scratch.error != "") {
                    return scratch
                }
                let x = readIntField(item, "x", scratch)
                if (scratch.error != "") {
                    return scratch
                }
                let y = readIntField(item, "y", scratch)
                if (scratch.error != "") {
                    return scratch
                }
                waypoints.add(Waypoint(n, x, y))
                i = i + 1
            }
    }
    let walls = ArrayList<Wall>()
    match (jsonField(root, "walls")) {
        case None => return LevelLoad(None, "missing walls")
        case Some(v) =>
            if (v.kind != 4) {
                return LevelLoad(None, "walls must be an array")
            }
            var i: Int64 = 0
            while (i < v.arr.size) {
                let item = match (v.arr.get(i)) {
                    case None => return LevelLoad(None, "wall index")
                    case Some(got) => got
                }
                if (item.kind != 5) {
                    return LevelLoad(None, "wall must be an object")
                }
                let x1 = readIntField(item, "x1", scratch)
                if (scratch.error != "") {
                    return scratch
                }
                let y1 = readIntField(item, "y1", scratch)
                if (scratch.error != "") {
                    return scratch
                }
                let x2 = readIntField(item, "x2", scratch)
                if (scratch.error != "") {
                    return scratch
                }
                let y2 = readIntField(item, "y2", scratch)
                if (scratch.error != "") {
                    return scratch
                }
                walls.add(Wall(x1, y1, x2, y2))
                i = i + 1
            }
    }
    match (jsonField(root, "parityEdges")) {
        case None => ()
        case Some(v) =>
            if (v.kind != 4) {
                return LevelLoad(None, "parityEdges must be an array")
            }
            if (v.arr.size != 0) {
                return LevelLoad(None, "non-empty parityEdges are not loaded by the iOS v1 shell")
            }
    }
    var stepLimit: Int64 = 0
    match (jsonField(root, "stepLimit")) {
        case None => ()
        case Some(v) =>
            if (v.kind != 2) {
                return LevelLoad(None, "stepLimit must be an int")
            }
            stepLimit = v.intVal
    }
    let level = LevelDef(id, name, cols, rows, waypoints, walls, ArrayList<ParityEdge>(), stepLimit)
    return LevelLoad(Some(level), "")
}
