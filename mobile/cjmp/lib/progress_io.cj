// 进度存档平台后端：std.fs 文件实现 + 工厂。
//
// 后端形态：目录 dir 下的 progress.json；写入走临时文件 progress.json.tmp
// 加 rename 覆盖，避免半截写坏存档（读到损坏 JSON 只会归零，不崩）。
//
// 目录来源（progressPickDir 的优先级）：
// - Android：宿主补丁 scripts/patch_android_filesdir.py 在 Activity 里
//   setenv("YILU_FILES_DIR", filesDir)，优先于 HOME；
// - iOS：$HOME/Documents。HOME 经 std.env.getVariable 读取，刻意不调
//   std.env.getHomeDirectory——pw_dir 为 NULL 时它可能崩；
// - 两者都取不到（Some 且非空且非 "/"）则退回 NullProgressBackend（内存，
//   实际即不落盘，读永远为空）。
//
// 注：Android 上若补丁失效而 HOME 恰有值，会尝试写 HOME/Documents，失败时
// write 返回 false，被 ProgressStore.save 降级（只打日志），不会崩。
//
// 本文件无 ohos 依赖，只用 std.*；所有异常都在本层吞掉，对外永不抛。

package ohos_app_cangjie_entry

import std.fs.*
import std.env.*

/* 纯函数：按 YILU_FILES_DIR > $HOME/Documents > None 选存档目录。
 * Some(s) 需非空且非 "/" 才算有效。 */
public func progressPickDir(yiluFilesDir: ?String, home: ?String): ?String {
    match (yiluFilesDir) {
        case Some(s) =>
            if (s != "" && s != "/") {
                return Some(s)
            }
        case None => ()
    }
    match (home) {
        case Some(h) =>
            if (h != "" && h != "/") {
                return Some(progressJoin(h, "Documents"))
            }
        case None => ()
    }
    return None
}

public func progressJoin(dir: String, name: String): String {
    if (dir.endsWith("/")) {
        return dir + name
    }
    return dir + "/" + name
}

public func progressFilePath(dir: String): String {
    return progressJoin(dir, "progress.json")
}

public func progressTmpPath(dir: String): String {
    return progressJoin(dir, "progress.json.tmp")
}

/* 文件后端：dir/progress.json，写入先落 .tmp 再 rename 覆盖。 */
public class FileProgressBackend <: ProgressBackend {
    private let dir: String

    public init(dir: String) {
        this.dir = dir
    }

    /* 读不到/读失败一律 None，永不抛。 */
    public func read(): ?String {
        try {
            let path = progressFilePath(this.dir)
            if (!exists(path)) {
                return None
            }
            let bytes = File.readFrom(path)
            // 存档文件可能被写坏，非法 UTF-8 不能走 Unchecked（会把坏字节
            // 直接塞进 String）；fromUtf8 对非法序列抛异常，被下面的 catch
            // 吞掉归 None。
            return Some(String.fromUtf8(bytes))
        } catch (e: Exception) {
            return None
        }
    }

    /* 目录不存在则先建；写 tmp 成功后 rename 覆盖最终文件。失败清理 tmp
     * 并返回 false，永不抛。 */
    public func write(text: String): Bool {
        let tmp = progressTmpPath(this.dir)
        try {
            if (!exists(this.dir)) {
                Directory.create(this.dir, recursive: true)
            }
            File.writeTo(tmp, text.toArray())
            rename(tmp, to: progressFilePath(this.dir), overwrite: true)
            return true
        } catch (e: Exception) {
            try {
                remove(tmp)
            } catch (e2: Exception) {
                // tmp 本来就没写出来，删不掉也无所谓
            }
            return false
        }
    }
}

/* 工厂：读环境变量选目录。getVariable 各自包 try/catch（异常当 None）。 */
public func makeProgressBackend(): ProgressBackend {
    var yiluDirOpt: ?String = None
    try {
        yiluDirOpt = getVariable("YILU_FILES_DIR")
    } catch (e: Exception) {
        yiluDirOpt = None
    }
    var homeOpt: ?String = None
    try {
        homeOpt = getVariable("HOME")
    } catch (e: Exception) {
        homeOpt = None
    }
    match (progressPickDir(yiluDirOpt, homeOpt)) {
        case Some(dir) => return FileProgressBackend(dir)
        case None => return NullProgressBackend()
    }
}
