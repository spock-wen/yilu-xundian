# 用 DevEco 编译运行鸿蒙版

> 从根 README 迁出（2026-11-16 整理）。DevEco 工程文件（`entry/`、`AppScope/`、`hvigor/`、`build-profile.json5`、`hvigorfile.ts`、`oh-package.json5`）必须留在仓库根，否则 DevEco 打不开，所以没有挪动。



仓颉 HAP **必须**用与 DevEco 锁步的仓颉插件。插件 5.x 不能装在 DevEco 6.0.1 上。仓颉 SDK 1.1.3 见 [cangjie-lang.cn/download/1.1.3](https://cangjie-lang.cn/download/1.1.3)。入门流程见仓颉官网《HarmonyOS 应用开发入门指导》：报名 → 安装匹配的 DevEco + 仓颉插件 → **[Cangjie] Empty Ability**。

### 推荐：先建官方空工程再铺源码

这是官方创建路径，也最不容易和本机 SDK / hvigor 插件版本打架。

1. 安装 **DevEco Studio**，用 **Plugins → Install Plugin from Disk** 安装 **与该 DevEco 同号** 的仓颉插件，重启 IDE。
2. `File → New → Create Project` → Application → **[Cangjie] Empty Ability**。仓颉目前只提供 Phone。
3. 工程名 / 显示名填 **驿路巡点**，bundle name 建议 `com.yilu.xundian`。
4. 等工程同步结束（仓颉 SDK 默认在 macOS `$HOME/.cangjie-sdk`、Windows `%USERPROFILE%\.cangjie-sdk`）。
5. 用本仓库覆盖生成工程里的：
   - `entry/src/main/cangjie/`
   - `entry/cjpm.toml`
   - `entry/src/main/resources/`
   - `entry/src/main/module.json5`（或只改 `label` / `icon`）
   - `AppScope/app.json5` 的 `bundleName` / `label`
   - `AppScope/resources/base/element/string.json`（`app_name` = 驿路巡点）
6. 若走 x86 模拟器，确认 `entry/build-profile.json5` 含：

```json5
"cangjieOptions": {
  "path": "./cjpm.toml",
  "abiFilters": ["arm64-v8a", "x86_64"]
}
```

（出处：上述官方第一应用目录把 `cjpm.toml` 放在 `entry/`；x86 过滤器见仓颉 Empty Ability 构建说明。默认只编 `arm64-v8a`。）

7. 配置签名，选 Phone 模拟器或真机，Run。
8. **不要**添加 IAP / 登录 / Game Service。

### 直接打开本仓库

也可以 `File → Open` 本仓库。首次同步时 DevEco 可能改写：

- `build-profile.json5` 的 `compatibleSdkVersion`（请改成你本机 HarmonyOS SDK）
- `hvigor/hvigor-config.json5` 里的仓颉 hvigor 支持包版本
- `local.properties`（SDK 路径，已 gitignore）

这些文件因本机插件而异，不要从网上抄一个对不上的 `cangjie-build-support-*.tgz` 版本。仓颉插件会在本机提供 `@ohos/cangjie-build-support`，该本机路径不要提交进 `hvigor/hvigor-config.json5`（仓库里保持 `dependencies: {}`）。

