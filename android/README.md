# 驿路巡点 Android 壳

Kotlin 只画格子，并把触摸交给 `mobile/shared` 里的仓颉 Zip 引擎。不是把 Zip 重写成 Kotlin，也不是鸿蒙界面移植。JNI 见 `android/app/src/main/cpp/yilu_jni.c`，符号与 iOS 相同（`mobile/include/yilu_zip.h`）。

## SMOKE: BLOCKED

没有在模拟器或真机上安装或玩过这一盘。构建机上还没有可用的 Android NDK、Android SDK 和仓颉 Android SDK，本环境也没有 `cjpm` / `gradle`。下面的命令是这些装好之后的编译路径。`build_debug.sh` 成功时也只产出 debug APK，不安装、不启动。不要把冒烟标成通过。

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
2. 在 `mobile/shared/.android-build/cjpm.toml` 写一份 **不提交** 的 manifest：`output-type = "dynamic"`，并带上
   - `--target` 默认 `aarch64-linux-android`（该页：默认 API 26；更高 API 的示例是 `--target=aarch64-linux-android31`）
   - `--sysroot <sysroot>`
   - `-L <builtins 目录>`
3. `cjpm build --target "$YILU_ANDROID_TARGET" -V`。`dynamic` 是 [cjpm 手册](https://docs.cangjie-lang.cn/cjnative/user_manual/tools/source_zh_cn/tools/cjpm_manual_cjnative_community.html) 里的动态库；对应的 `cjc` 标志是 `--output-type=dylib`，在 Linux 上产物是 `.so`（[cjc 编译选项](https://docs.cangjie-lang.cn/docs/1.0.3/user_manual/source_zh_cn/Appendix/compile_options.html)）。交叉编译页自己的 Android 示例是可执行文件（`cjc main.cj` 没有写 `--output-type`）。这里改成动态库，是为了让 APK 用 JNI 加载，源码仍是同一份 `yilu_zip`。
4. 把 `libyilu_zip*.so` 和运行时 `.so` 拷到 `android/app/src/main/jniLibs/arm64-v8a/`。运行时目录的文档示例（API 31）是 `$CANGJIE_HOME/runtime/lib/linux_android31_aarch64_cjnative`。脚本会先找 `linux_android<API>_aarch64_cjnative`，再找 `linux_android_aarch64_cjnative`。都不在就停下，并列出 `runtime/lib`。可用 `YILU_CJ_ANDROID_RUNTIME` 指到实际目录。
5. 写 `assets/cangjie_native_libs.txt`（先运行时库，再 `libyilu_zip*.so`）。Kotlin 按这个顺序 `System.loadLibrary`，最后加载 `yilu_jni`。
6. `android/gradlew :app:assembleDebug`。

APK：`android/app/build/outputs/apk/debug/app-debug.apk`。

更高 API 的例子（31 来自交叉编译页，不是本仓库测出来的）：

```bash
export YILU_ANDROID_TARGET=aarch64-linux-android31
android/scripts/build_debug.sh
```

装好 APK 之后，预期标题是「驿路巡点」，副标题 **涿郡·范阳 · id 1**。拖格子、撤销、重绘驿道都进仓颉。这一步就是被挡住的冒烟，现在不要做通过记录。

## 已知限制

- **SMOKE: BLOCKED。** 没有 NDK / Android SDK / 仓颉 Android SDK 的构建机，也没有模拟器记录。
- 只接范阳这一关。非空 `parityEdges` 会拒绝加载。
- 若 `cjpm` 没有产出 `libyilu_zip.so`，脚本会把 `target/` 里的文件名打出来并失败，而不是假装动态库已经链进 APK。
- `@C` 符号名尚未在 Android `.so` 上用 `nm` 核对。
