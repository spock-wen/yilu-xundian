// 进度存档平台后端工厂。
//
// 后端规划（后续步骤实现）：
// - 标准平台：使用 std.fs 读写文件；
// - iOS：目录取自 std.env.getHomeDirectory()；
// - Android：目录由宿主补丁经环境变量 YILU_FILES_DIR 传入；
// - 上述途径均读不到/不可用时，退回 Null 后端（不落盘）。
//
// 本步（第 2 步）尚未实现真实后端，makeProgressBackend() 暂时返回
// NullProgressBackend，待下一步替换为 std.fs 文件实现。
// （Mac 只读探测已确认 PersistentStorage 在 0.2.2 的 Android/iOS 库中
// 不存在：FfiOHOSAceFrameworkPersistent* 符号数为 0，故不能走该通道。）

package ohos_app_cangjie_entry

public func makeProgressBackend(): ProgressBackend {
    return NullProgressBackend()
}
