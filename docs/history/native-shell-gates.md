# 原生壳（iOS / Android）门禁与冒烟记录

> 从根 README 第 9 行迁出（2026-11-16 整理），文字未改，只把路径更新到整理后的位置。
> 这些是 2026-09 底 / 10 月初原生 UIKit / Kotlin 壳的记录；这两套壳已被 `app-ios-android/`（CJMP / Keels）取代，现位于 `legacy/`。

iOS 壳见 [legacy/ios/README.md](../../legacy/ios/README.md)。Android 壳见 [legacy/android/README.md](../../legacy/android/README.md)。两边共用 [engine/shared](../../engine/shared) 里的仓颉 Zip 引擎，不是把规则重写成 Swift 或 Kotlin。**iOS 模拟器冒烟 PASSED**（tip `eaf7aed`，进入涿郡·范阳 id 1；截图目录 `qa-shots/ios-shell-eaf7aed-gate`，本检出不含该目录）。**Android** 把程序员 Mac 冒烟和测试门禁分开记，都在 tip `f25f813`（`f25f813d81388b550fd336f3b819b93117f214c5`）。**程序员 Mac 冒烟 PASSED**（AVD `grokdump`，进入涿郡·范阳 id 1，6×6 可见；目录 `_smoke/android-fanyang-f25f813-resmoke-*`、`qa-shots/android-shell-f25f813-gate/`，本检出可不含）。**测试门禁 PASS**（全屏目录 `qa-shots/android-shell-f25f813-tester`，本检出可不含）。更早 tip `4986524` 因缺少 `CJ_MRT_CjRuntimeInit` 为 FAIL。见 [legacy/android/README.md](../../legacy/android/README.md)。
