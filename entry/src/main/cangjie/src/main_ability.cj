package ohos_app_cangjie_entry

import ohos.window.WindowStage
import kit.AbilityKit.*

/* Empty Ability UIAbility. loadContent uses the @Entry class name EntryView.
   Source: official Cangjie Empty Ability / OpenHarmony wrapper samples. */
class MainAbility <: UIAbility {
    public func onCreate(want: Want, launchParam: LaunchParam): Unit {
    }

    public func onWindowStageCreate(windowStage: WindowStage): Unit {
        windowStage.loadContent("EntryView")
    }
}
