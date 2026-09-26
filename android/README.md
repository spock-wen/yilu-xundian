# 驿路巡点 Android 壳

Kotlin 只画格子，并把触摸交给 `mobile/shared` 里的仓颉 Zip 引擎。不是把 Zip 重写成 Kotlin，也不是鸿蒙界面移植。JNI 见 `android/app/src/main/cpp/yilu_jni.c`，符号与 iOS 相同（`mobile/include/yilu_zip.h`）。

## SMOKE: FAIL（programmer Mac，2026-09-27 Asia/Shanghai）

programmer Mac 在 tip `4986524`（`4986524a6cb3cb8889c73cd2d475fc832dade380`）上的冒烟是 **FAIL**。不要标 PASSED。

- 用仓颉 Android SDK 1.1.3 + NDK 27.0.12077973 + platform 34 编出 debug APK。
- 装上 AVD `grokdump`（Pixel 6 / Android 15 arm64，emulator-5560）。
- 原生库能加载（打进 NDK `libc++_shared.so`，并把 JNI 的 `DT_NEEDED` 改成 `libyilu_zip.so` 之后）。
- **第一次 `yilu_load_level_json` 就 abort**：`Check failed: runtime != nullptr`。栈顶是 `yilu_load_level_json` ← `Java_com_yilu_xundian_YiluZip_nativeLoadLevel` ← `MainActivity.onCreate`。时间戳 2026-09-27 00:28:40 CST。仓颉运行时单例是空的；iOS 用 `CJ_MRT_CjRuntimeInit` 避开同一类检查（[Runtime.h](https://github.com/cangjielanguage/cangjie_runtime/blob/v1.1.3/runtime/src/Common/Runtime.h)）。
- 棋盘（涿郡·范阳 / id 1）**没有**出现。截图是崩溃后的桌面或错误态，目录名 `_smoke/` 与 `qa-shots/android-shell-4986524-gate/`。本检出不含这些目录。

这次改动在 JNI 里补了一次性的 `CJ_MRT_CjRuntimeInit`（见下文「运行时」）。**本环境没有 AVD，没有重装、没有重跑。** 状态仍是 FAIL，直到同一类 Mac 冒烟打开涿郡·范阳 id 1，并且能看见 6×6 格子。`build_debug.sh` 只编 APK，不安装、不启动。

### 那次 Mac 会话的环境（只在当次 shell，没有写进 profile）

- `CANGJIE_HOME=/Users/spock/sdk/cangjie-android/cangjie`（从 Downloads 的 Android 包解出；iOS SDK 仍在 `/Users/spock/sdk/cangjie`）
- `ANDROID_HOME=/opt/homebrew/share/android-commandlinetools`
- `ANDROID_NDK_HOME` 指到该 SDK 下的 `ndk/27.0.12077973`

## 这一关

与 iOS 相同：`entry/src/main/resources/rawfile/levels.json` **id 1「涿郡·范阳」**（6×6，6 驿站，2 墙，`parityEdges: []`，`stepLimit: 0`）。

- 源：`mobile/shared/levels/zhuojun-fanyang.json`
- 进 APK：`android/app/src/main/assets/level.json`

```bash
python3 mobile/scripts/check_level.py
```

## 环境清单

仓颉交叉编译到 Android 的宿主可以是 Linux x64、macOS aarch64 或 Windows x64（[交叉编译 1.1.3](https://cj-docs.gitcode.com/zh/1.1.3/dev-guide/source_zh_cn/compile_and_build/cross_compilation.html)）。下载页 [1.1.3](https://cangjie-lang.cn/download/1.1.3) 上能看到的包：

- Linux x64：`cangjie-sdk-linux-x64-android-1.1.3.tar.gz`
- macOS aarch64：`cangjie-sdk-mac-aarch64-android-1.1.3.tar.gz`
- Windows x64：交叉编译表写的是 `cangjie-sdk-windows-x64-android.x.y.z.zip` 或 `.exe`；以下载页实际列出的文件名为准

另外需要：

- Android NDK（该页要求 **API 26+**，示例用的是 NDK r25b 的 `toolchains/llvm/prebuilt/linux-x86_64`）
- Android SDK，且已安装 **platform 34**（本工程 `compileSdk = 34`，`minSdk = 26`，与仓颉 Android 最低 API 26 对齐）
- JDK 17（Gradle 8.7 / Android Gradle Plugin 8.5.2）
- `CANGJIE_HOME` 指到含 `envsetup.sh` 的目录，路径不要有空格

```bash
export CANGJIE_HOME=/absolute/path/to/cangjie
source "$CANGJIE_HOME/envsetup.sh"
export ANDROID_NDK_HOME=/absolute/path/to/ndk
export ANDROID_HOME=/absolute/path/to/android-sdk
cjc -v
```

可选 CJMP：本树没有跑 `keels`。[start-tools](https://gitcode.com/CJMP/Docs/blob/opensource/zh-cn/app-dev/quick-start/start-tools.md) 把 Android 列为 `keels run` 的目标之一。前置与 iOS 一样要 `CJMP_SDK_HOME`。那条路径的样例界面是 `Hello Keels`，不是这张棋盘。

## 编译

在仓库根目录：

```bash
source "$CANGJIE_HOME/envsetup.sh"
export ANDROID_NDK_HOME=/absolute/path/to/ndk
export ANDROID_HOME=/absolute/path/to/android-sdk
android/scripts/build_debug.sh
```

脚本做的事：

1. 找到 NDK 的 `toolchains/llvm/prebuilt/<host>/sysroot`，以及 `libclang_rt.builtins-aarch64-android.a` 所在目录。交叉编译页的示例宿主目录是 `linux-x86_64`；脚本按 `uname` 选 `prebuilt/<host>`，找不到再扫该目录。
2. cjpm 1.1.3 拒绝模块目录以外的 `src-dir`（`../src` 会失败）。脚本把 `mobile/shared/src` 拷到 **不提交** 的 `mobile/shared/.android-build/src`，再写 `cjpm.toml`：`output-type = "dynamic"`，`src-dir = "./src"`，并带上
   - `--target` 默认 `aarch64-linux-android`（该页：默认 API 26；更高 API 的示例是 `--target=aarch64-linux-android31`）
   - `--sysroot <sysroot>`
   - `-L <builtins 目录>`
   - `-B <prebuilt>/bin`，让 `cjc` 找到 NDK 的 `llvm-ar`。`cjpm` 期间还把这个 `bin` 接到 `PATH` 前面。
3. `cjpm build --target "$YILU_ANDROID_TARGET" -V`。`dynamic` 是 [cjpm 手册](https://docs.cangjie-lang.cn/cjnative/user_manual/tools/source_zh_cn/tools/cjpm_manual_cjnative_community.html) 里的动态库；对应的 `cjc` 标志是 `--output-type=dylib`，在 Linux 上产物是 `.so`（[cjc 编译选项](https://docs.cangjie-lang.cn/docs/1.0.3/user_manual/source_zh_cn/Appendix/compile_options.html)）。交叉编译页自己的 Android 示例是可执行文件（`cjc main.cj` 没有写 `--output-type`）。这里改成动态库，是为了让 APK 用 JNI 加载，源码仍是同一份 `yilu_zip`。
4. 把 `libyilu_zip*.so` 和运行时 `.so` 拷到 `android/app/src/main/jniLibs/arm64-v8a/`。运行时目录的文档示例（API 31）是 `$CANGJIE_HOME/runtime/lib/linux_android31_aarch64_cjnative`。脚本会先找 `linux_android<API>_aarch64_cjnative`，再找 `linux_android_aarch64_cjnative`。都不在就停下，并列出 `runtime/lib`。可用 `YILU_CJ_ANDROID_RUNTIME` 指到实际目录。
5. `libcangjie-runtime.so` 的 `DT_NEEDED` 包含 NDK 的 `libc++_shared.so`。脚本从 sysroot（或 NDK 里 aarch64 的那份）拷进 `jniLibs/arm64-v8a/`。
6. 写 `assets/cangjie_native_libs.txt`：先 `c++_shared`，再运行时库，再 `libyilu_zip*.so`（根库最后）。Kotlin 按这个顺序 `System.loadLibrary`，最后加载 `yilu_jni`。
7. `android/gradlew :app:assembleDebug`。CMake 用 `-L/-l` 链 `yilu_zip` 和 `cangjie-runtime`，这样 `DT_NEEDED` 是 `libyilu_zip.so` / `libcangjie-runtime.so`，不是编译机上的绝对路径。

APK：`android/app/build/outputs/apk/debug/app-debug.apk`。

更高 API 的例子（31 来自交叉编译页，不是本仓库测出来的）：

```bash
export YILU_ANDROID_TARGET=aarch64-linux-android31
android/scripts/build_debug.sh
```

装好 APK 之后，预期标题是「驿路巡点」，副标题 **涿郡·范阳 · id 1**。拖格子、撤销、重绘驿道都进仓颉。tip `4986524` 没有走到这一屏。本树补了运行时初始化，但没有在模拟器上复测，不要做通过记录。

## 运行时

Android 1.1.3 运行时是 aarch64 Linux ELF，不是 iOS 的 Mach-O。[`android_aarch64_cangjie.cmake`](https://github.com/cangjielanguage/cangjie_runtime/blob/v1.1.3/runtime/build/cmake/toolchain/android_aarch64_cangjie.cmake) 把 `OS` 设成 `linux`，并定义 `__ANDROID__`。每个仓颉 `.so` 链的是 [`aarch64_linux/Cjstart.S`](https://github.com/cangjielanguage/cangjie_runtime/blob/v1.1.3/runtime/src/arch/aarch64_linux/Cjstart.S)：`.init_array.0` 里的 `__CJ_Init_Start` 在 `dlopen` 时调用 `MRT_LibraryOnLoad(&__CJMetadataStart, 1)`。`__CJMetadataStart` 是该 `.so` 里 `.cjmetadata.rw.header` 的地址，不是 dyld 填出来的全局指针。没有 `os/Linux/Section.cpp`。

[`LoaderManager::LoadFile`](https://github.com/cangjielanguage/cangjie_runtime/blob/v1.1.3/runtime/src/LoaderManager.cpp) 写明 `MRT_LibraryOnLoad` 可以在运行时初始化之前调用，那时只把地址放进队列。`AddPreLoadedImageMetaAddr` 不去重。引导代码只调用 `CJ_MRT_CjRuntimeInit`，把第二次 `MRT_LibraryOnLoad` 留给已经跑过的 `.init_array`。`System.loadLibrary` 按 `cangjie_native_libs.txt` 加载时，这些构造函数先于 `yilu_jni` 的 `JNI_OnLoad`。本环境没有 tip `4986524` 的 `.so`，没有用 `readelf` 核对 `.init_array`；若复测时单例已经起来但包未注册，再查 `libyilu_zip.so` 里有没有 `__CJ_Init_Start`。

创建单例的是 `CJ_MRT_CjRuntimeInit`（非 Apple 上是 [`MRT_CjRuntimeInit` 的别名](https://github.com/cangjielanguage/cangjie_runtime/blob/v1.1.3/runtime/src/CjScheduler.cpp)）。符号在 `libcangjie-runtime.so` 里，版本为 `CJ_MRT_CjRuntimeInit@@CANGJIE`。壳在 `android/app/src/main/cpp/CangjieRuntimeBootstrap.c`：`JNI_OnLoad` 和每个 `yilu_*` JNI 入口都进 `yilu_ensure_cj_runtime()`，里面只用一次 `__sync_bool_compare_and_swap`。第二次 `MRT_CjRuntimeInit` 会 fatal（`don't support init again`）。CMake 用 `-lcangjie-runtime` 声明这个符号。

Kotlin 必须先按清单加载仓颉 `.so`，再加载 `yilu_jni`，这样 `JNI_OnLoad` 发生在元数据入队之后。

## 已知限制

- **SMOKE: FAIL。** tip `4986524` 已在 Mac AVD 上崩溃。本改动没有复测。看见 6×6 的涿郡·范阳之前不要标 PASSED。
- 只接范阳这一关。非空 `parityEdges` 会拒绝加载。
- 若 `cjpm` 没有产出 `libyilu_zip.so`，脚本会把 `target/` 里的文件名打出来并失败，而不是假装动态库已经链进 APK。
- 崩溃栈说明 `yilu_load_level_json` 这个符号已经进了 `.so`。其余 `yilu_*` 没有在本环境用 `nm` 逐个核对（这里没有 Android SDK / 仓颉 Android SDK）。
