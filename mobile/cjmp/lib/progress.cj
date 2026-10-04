package ohos_app_cangjie_entry

import std.collection.ArrayList
import ohos_app_cangjie_entry.game.{JsonParser, JsonVal, JsonField}

/* 进度存档（纯逻辑，无 ohos 依赖，不抛异常）。
 *
 * 存档格式：单行 JSON 对象 {"v":1,"cleared":N}。
 *   - v 为格式版本，恒为 1；读取时 v!=1 或缺失即视为损坏，返回 0。
 *   - cleared 为已通关的最高关卡下标+1（0..total），负数按 0 编码/读取时判 0。
 *
 * 永不抛异常：progressDecode / ProgressStore.load 全体包在 try/catch 里，
 * 任何输入（空串、截断、非 JSON、超长数字触发的 OverflowException 等）都
 * 归一为 0，存档损坏只表现为"从头开始"，不能让游戏崩掉。
 *
 * 为何复用 shared/src/game 的 JsonParser 而不是自带解析器：存档只含整数，
 * 与关卡解析共用同一份已在 box/iOS 上验证过的实现（尤其它刻意不经过
 * numberToString，规避 iOS 1.1.3 的栈溢出崩溃）。已知限制与关卡解析一致：
 *   - 只认整数，小数/科学计数解析失败（failed）→ 0；
 *   - 字符串不支持 \u 转义（failed）→ 0；
 *   - 数字超出 Int64 会抛 OverflowException，由外层 catch 吞掉 → 0。
 * progressEncode 不走 JsonParser，手工拼接字符串。
 */

func progressDigit(d: Int64): String {
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

/* 十进制输出不用 Int64.toString：它会走 numberToString，即 iOS 1.1.3
 * 崩溃日志里递归的那个帧（同 json_level.cj 的 decimalText，那边不是
 * public，这里各留一份）。 */
func progressDecimal(n: Int64): String {
    if (n <= 0) {
        return "0"
    }
    var v = n
    var out = ""
    while (v > 0) {
        out = progressDigit(v % 10) + out
        v = v / 10
    }
    return out
}

public func progressEncode(cleared: Int64): String {
    var n = cleared
    if (n < 0) {
        n = 0
    }
    return "{\"v\":1,\"cleared\":" + progressDecimal(n) + "}"
}

public func progressDecode(text: String, total: Int64): Int64 {
    try {
        var cap = total
        if (cap < 0) {
            cap = 0
        }
        let p = JsonParser(text)
        let root = p.parseValue()
        if (p.failed) {
            return 0
        }
        p.skipWs()
        if (!p.eof()) {
            return 0
        }
        if (root.kind != 5) {
            return 0
        }
        // 重复键取第一个：各键只记录首次出现，之后同名的直接跳过。
        var sawV = false
        var vOk = false
        var sawCleared = false
        var cleared: Int64 = 0
        let fields: ArrayList<JsonField> = root.fields
        for (i in 0..fields.size) {
            match (fields.get(i)) {
                case None => return 0
                case Some(f) =>
                    if (f.key == "v" && !sawV) {
                        sawV = true
                        if (f.val.kind == 2 && f.val.intVal == 1) {
                            vOk = true
                        }
                    } else if (f.key == "cleared" && !sawCleared) {
                        sawCleared = true
                        if (f.val.kind == 2) {
                            cleared = f.val.intVal
                        }
                    }
            }
        }
        if (!sawV || !vOk || !sawCleared) {
            return 0
        }
        if (cleared < 0) {
            return 0
        }
        if (cleared > cap) {
            return cap
        }
        return cleared
    } catch (e: Exception) {
        return 0
    }
}

public func progressAfterWin(cleared: Int64, levelIndex: Int64, total: Int64): Int64 {
    var cap = total
    if (cap < 0) {
        cap = 0
    }
    var n = cleared
    if (n < 0) {
        n = 0
    }
    if (levelIndex >= 0) {
        if (levelIndex >= cap) {
            // levelIndex+1 > cap，结果被 clamp 到 cap；同时避免
            // levelIndex 为 Int64.Max 时 +1 溢出。
            return cap
        }
        let target = levelIndex + 1
        if (target > n) {
            n = target
        }
    }
    if (n > cap) {
        n = cap
    }
    return n
}

public interface ProgressBackend {
    func read(): ?String
    func write(text: String): Bool
}

/* 空后端：不落盘。读永远没有存档，写永远失败。 */
public class NullProgressBackend <: ProgressBackend {
    public init() {
    }

    public func read(): ?String {
        return None
    }

    public func write(text: String): Bool {
        return false
    }
}

public class ProgressStore {
    public static func load(b: ProgressBackend, total: Int64): Int64 {
        try {
            match (b.read()) {
                case None =>
                    return 0
                case Some(text) =>
                    return progressDecode(text, total)
            }
        } catch (e: Exception) {
            return 0
        }
    }

    public static func save(b: ProgressBackend, cleared: Int64): Bool {
        try {
            if (b.write(progressEncode(cleared))) {
                return true
            }
            println("[progress] save failed")
            return false
        } catch (e: Exception) {
            println("[progress] save failed")
            return false
        }
    }
}
