package ohos_app_cangjie_entry

import std.time.DateTime
import std.time.MonoTime

public const PERF_LOG: Bool = false

public func perfNowMs(): Int64 {
    return DateTime.now().toUnixTimeStamp().toMilliseconds()
}

public func perfLog(msg: String): Unit {
    if (PERF_LOG) {
        println("PERF ${perfNowMs()} ${msg}")
    }
}
