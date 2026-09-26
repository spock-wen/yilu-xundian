import Foundation

/// Thin caller for the Cangjie static library. Zip rules stay in `yilu_zip`.
final class YiluZip {
    private(set) var loaded = false
    private(set) var loadError = ""

    func loadBundledLevel() {
        guard let url = Bundle.main.url(forResource: "level", withExtension: "json") else {
            loaded = false
            loadError = "App bundle is missing level.json"
            return
        }
        let data: Data
        do {
            data = try Data(contentsOf: url)
        } catch {
            loaded = false
            loadError = "Could not read level.json"
            return
        }
        guard let text = String(data: data, encoding: .utf8) else {
            loaded = false
            loadError = "level.json is not UTF-8"
            return
        }
        yilu_ensure_cj_runtime()
        let rc = text.withCString { ptr in
            yilu_load_level_json(ptr)
        }
        if rc == 0 && yilu_ready() == 1 {
            loaded = true
            loadError = ""
        } else {
            loaded = false
            loadError = Self.copyCString { buf, cap in
                yilu_last_error(buf, cap)
            }
            if loadError.isEmpty {
                loadError = "yilu_load_level_json failed"
            }
        }
    }

    func levelName() -> String {
        guard loaded else { return "" }
        return Self.copyCString { buf, cap in
            yilu_copy_name(buf, cap)
        }
    }

    private static func copyCString(_ read: (UnsafeMutablePointer<UInt8>, Int32) -> Int32) -> String {
        var bytes = [UInt8](repeating: 0, count: 512)
        let n = bytes.withUnsafeMutableBufferPointer { raw -> Int32 in
            guard let base = raw.baseAddress else { return -1 }
            return read(base, Int32(raw.count))
        }
        if n < 0 {
            return ""
        }
        let count = Int(n)
        if count > bytes.count {
            return ""
        }
        return String(bytes: bytes.prefix(count), encoding: .utf8) ?? ""
    }
}
