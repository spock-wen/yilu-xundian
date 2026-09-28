# CJMP (Keels) 移动端应用基座

`mobile/cjmp` 是基于 CJMP OpenSDK 0.2.2 与 Keels 工具链构建的 iOS / Android 跨平台应用源码（M1 基座）。

> **说明**：本项目独立于 `ios/` 与 `android/` 下的原生 UIKit / Kotlin 宿主壳，原有的原生壳保持原样未做任何修改。

## 目录结构

- `lib/`：应用源码与模块逻辑。包含页面入口、关卡数据加载及与引擎交互的逻辑。
- `fonts/`：精简后的字形子集字体文件（`YiluSerif-Regular.otf`、`YiluSerif-Bold.otf`）、字表定义（`charset.txt`）与开源许可（`OFL.txt`）。
- `scripts/`：工具脚本。
  - `sync_to_keels.sh`：将源码、共用引擎与资源同步至 Keels 工程。
  - `subset_fonts.py`：基于实际关卡与代码文本提取字符集并子集化 Noto Serif SC 字体。

## 构建指南

1. **创建或复用 Keels 工程**：
   使用 `keels create <proj_name>` 创建工程，或复用已有 Keels 工程目录。

2. **iOS Xcode 27 补丁（如需要）**：
   若使用较高版本的 Xcode/iOS SDK，可在生成的 Xcode 工程文件 `project.pbxproj` 中将 `IPHONEOS_DEPLOYMENT_TARGET` 设置或修补为 `15.0`。

3. **同步代码与资源**：
   ```bash
   ./mobile/cjmp/scripts/sync_to_keels.sh <keels_project_dir>
   ```

4. **编译与运行**：
   - Android APK：
     ```bash
     keels build apk
     ```
   - iOS 模拟器：
     ```bash
     keels build ios-sim
     ```

## 已知问题与变通方案 (Workarounds)

- **资源引用**：CJMP OpenSDK 0.2.2 暂不支持 `@r` 语法，图片与媒体资源统一通过 `resource://RAWFILE/` 协议路径加载。
- **字体注册**：由于公共字体注册 API 限制，字体通过引擎底层私有 FFI 符号 `FfiFontManagerRegisterFont` 配合 `dlsym` 进行动态注册（属内部私有符号，后续 SDK 版本可能调整）。
- **页面返回**：iOS 系统的侧滑返回手势在当前容器下不可用，所有子页面均内置页面内返回按钮 `〈`。
- **安全区与状态栏**：安全区及状态栏间距当前为占位实现（PLACEHOLDER），等待产品经理（PM）的设计决策最终确定。
- **棋盘实现**：当前棋盘为占位展示，完整巡点交互逻辑将在 M2 里程碑接入。
- **特殊机制与修缮关卡**：6 种核心特殊机制及修缮关卡暂未实现，计划在 M3 里程碑实现。

## 字体许可

字体基于 Noto Serif SC，遵循 SIL Open Font License 1.1 开源协议。详情请参阅 `fonts/OFL.txt`。
