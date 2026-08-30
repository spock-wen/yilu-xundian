package ohos_app_cangjie_entry

import kit.AbilityKit.*

/* Official Empty Ability UIAbility. loadContent uses the @Entry class name.
   WindowStage comes from kit.AbilityKit (docs_cangjie window-stage guide). */
class MainAbility <: UIAbility {
    public func onCreate(want: Want, launchParam: LaunchParam): Unit {
    }

    public func onWindowStageCreate(windowStage: WindowStage): Unit {
        windowStage.loadContent("EntryView")
    }
}
