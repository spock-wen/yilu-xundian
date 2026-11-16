# API 依据（未编造 `@ohos.*` / ArkTS-only）

> 从根 README 迁出（2026-11-16 整理）。


全部对照 [openharmony/docs_cangjie](https://gitcode.com/openharmony/docs_cangjie) 的仓颉文档，**不是** ArkTS 文档。

| 用法 | 依据 |
| --- | --- |
| Empty Ability 树：`entry/src/main/cangjie/{ability_stage,index,main_ability}.cj` + `entry/cjpm.toml` + `module.json5` | [cj-quick-start-first-cangjie-app.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/cj-start/start/quick-start/cj-quick-start-first-cangjie-app.md) |
| `import kit.ArkUI.*` + `import ohos.arkui.state_macro_manage.*`；`@Entry` `@Component` `@State` | 同上 `index.cj` 初始代码；Canvas 指南同套 import |
| `kit.AbilityKit.*`、`UIAbility`、`windowStage.loadContent("EntryView")` | [cj-application-window-stage.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/windowmanager/cj-application-window-stage.md) |
| `RenderingContextSettings(antialias: true)` 再 `CanvasRenderingContext2D(settings)`（无 `new`） | [cj-drawing-customization-on-canvas.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/arkui-cj/cj-drawing-customization-on-canvas.md) |
| 颜色 `0XF3E8D6` 等 token 整数，坐标 `Float64` vp（`50.0`） | 同上示例 `0XF5DC62`、`fillRect(50.0, 50.0, …)`；色值来自设计师手稿 |
| `Text.fontFamily("serif")` / `"sans-serif"` | [cj-text-input-text.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/reference/arkui-cj/cj-text-input-text.md) `func fontFamily`。非棋盘文案仍用系统 generic family |
| `Divider` / `Blank` / `Stack` / `.rotate(angle:)` / `.border` / `.layoutWeight` | docs_cangjie 对应通用属性与容器页 |
| `lineWidth` / `strokeStyle` / `fillStyle` / `font` 是 **属性**：`this.context.lineWidth = 2.0` | [cj-canvas-drawing-canvasrenderingcontext2d.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/reference/arkui-cj/cj-canvas-drawing-canvasrenderingcontext2d.md)（`prop lineWidth` / `prop font`） |
| 棋盘驿站数字：`Path2D` + `moveTo` / `lineTo` / `arc` + `stroke(path)`，单位 **vp**（与驿站圆同一套） | [cj-canvas-drawing-path2d.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/reference/arkui-cj/cj-canvas-drawing-path2d.md) `moveTo`/`lineTo`/`arc`「默认单位：vp」；[cj-canvas-drawing-canvasrenderingcontext2d.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/reference/arkui-cj/cj-canvas-drawing-canvasrenderingcontext2d.md) `func stroke(Path2D)`。字形高 = 直径 × 0.60（教程 40vp → 24vp）。`fillText` / `font` 的 `px` 与 `vp`、以及 `vp2px` 在真机上未能放大墨像素（教程站 1 的 180×180 裁切相对 e90cacf 为 0 px diff），因此数字不用 font |
| 首次绘制在 `onReady`；`clearRect` / `fillRect` / `beginPath` / `moveTo` / `lineTo` / `stroke` / `fill` / `fillText` / `arc` | 上述两篇 Canvas 文档 |
| 底栏「撤销」「重绘驿道」：可点击 `Row` + 24vp Canvas；弧用 `Path2D()` + `stroke(path)`，三角箭头用当前路径 `fill()`；`lineWidth` 是属性。不用 `Button("撤销")` | [cj-canvas-drawing-canvasrenderingcontext2d.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/reference/arkui-cj/cj-canvas-drawing-canvasrenderingcontext2d.md) 的 `func stroke(Path2D)`、`func fill()`。HarmonyOS 6.1.1 默认 Button 仍带 start icon，缺字形会变成方块。几何见 `tools/bar_icons.py`（手稿甲） |
| `onTouch({ event => match (event.eventType) { case TouchType.Down => … } })`；点 `event.touches[0].x` / `.y` | [cj-common-events-touch-screen-event.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/arkui-cj/cj-common-events-touch-screen-event.md) 的**代码示例**。字段是 `event.eventType`（类型定义见 `cj-common-types.md` 的 `TouchEvent.eventType`），**不是** ArkTS 的 `event.type`（该页散文里的 `event.type` 与示例不一致，以代码与类型定义为准） |
| `ArrayList.add` / `remove(at:)` / `size` | [仓颉 1.1.3 ArrayList](https://cj-docs.gitcode.com/zh/1.1.3/dev-guide/source_zh_cn/collections/collection_arraylist.html) |

明确 **没有** 使用：

- 过时 `import ohos.component.*` / `ohos.state_manage.*`
- 未在官方 Canvas 页出现的 `import ohos.arkui.component.Canvas`
- ArkTS `event.type`、`new CanvasRenderingContext2D`
- OffscreenCanvas / XComponent / Component3D
- 未核对的 `@ohos.*` 包

用户提到的 Beat Roguelike 仓库 https://gitcode.com/yunitia/qwe 当前页面无可用 Canvas 源码，**没有抄游戏代码**。

