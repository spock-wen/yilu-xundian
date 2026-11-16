#!/usr/bin/env python3
"""patch_ios_scene.py — patch the Keels-generated iOS host for the UIScene lifecycle.

Apple's TN3187 requires the UIScene lifecycle for apps built with the iOS 27
SDK. The Keels iOS host template creates its window in AppDelegate and ships
an Info.plist without UIApplicationSceneManifest, so the app crashes at launch
on iOS 27. This script patches the generated host in place:

  * adds UIApplicationSceneManifest to <ios_dir>/<name>/Info.plist
  * moves window / root-VC creation from AppDelegate into a new SceneDelegate
    (StageApplication config/launch lines stay in
     application:didFinishLaunchingWithOptions:, per CJMP project-setup.md)
  * registers SceneDelegate.h/.m in <name>.xcodeproj/project.pbxproj

--bars controls the status-bar / navigation-bar area of the generated host
(the "white band" fix; see app-ios-android/README.md):

  * hide (default)  paper(#F3E8D6) window background, forced light mode, hidden
           navigation bar using YiluNavigationController (preferredStatusBarStyle
           = UIStatusBarStyleDarkContent), root VC view painted paper.
           Must be paired with Cangjie safe-top/bottom padding (merged in the
           same batch); if YILU_SAFE_TOP is not set, content sits right below the
           status bar. Exports safeAreaInsets via setenv YILU_SAFE_TOP /
           YILU_SAFE_BOTTOM (1/100 logical points); timing fixed by Mac E2/E3/E8
           measurements (2026-10-04, iPhone 17 402x874 pt, iOS 27.0): window
           insets are 0 before makeKeyAndVisible, readable after — exported
           after makeKeyAndVisible+layoutIfNeeded (before the viewController
           view access that triggers viewDidLoad), again after the
           rootViewController assignment, and re-exported on
           viewSafeAreaInsetsDidChange / viewWillTransitionToSize completion /
           sceneDidBecomeActive.
  * paper           paper(#F3E8D6) window background, forced light mode,
           navigation bar kept but repainted opaque paper with no shadow
           hairline — Mac-measured colour-exact (ΔRGB 0 vs paper), content
           start identical to off (the 116pt band stays, just paper-coloured)
  * off             the original template behaviour (white window background)

Anchors are taken from the Keels engine sample project (same toolchain, same
shape: ObjC AppDelegate with a `window` property, main.m, minimal Info.plist)
and have been exercised against real `keels create` 0.2.2 output on Mac
(hide/paper/off all built, check-app OK). Every anchor is still checked and a
missing anchor makes the script exit 1 with
"Keels template changed: anchor X not found in FILE" — never a silent skip.

Subcommands:
  patch <ios_dir> [--name NAME]        apply the patch (idempotent)
  check-app <app_path> [--name NAME]   verify a built .app bundle
  selftest                             run the built-in test suite
  fixture-from-sample SRC DEST         copy a sample project as a rename
      --from-name OLD --name NEW       fixture (dir + xcodeproj + pbxproj text)

Python stdlib only.
"""

import argparse
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile

MARKER = "yilu-scene-patch"

SCENE_MANIFEST = {
    "UIApplicationSupportsMultipleScenes": False,
    "UISceneConfigurations": {
        "UIWindowSceneSessionRoleApplication": [
            {
                "UISceneConfigurationName": "Default Configuration",
                # Objective-C class name, no module prefix.
                "UISceneDelegateClassName": "SceneDelegate",
            }
        ]
    },
}

# Deterministic seed for new pbxproj object IDs (24-char uppercase hex).
PBX_ID_SEED = 0x7E5CE4E000000000000000A1


def die(msg):
    print("ERROR: %s" % msg, file=sys.stderr)
    sys.exit(1)


def anchor_error(anchor, path):
    die('Keels template changed: anchor %s not found in %s' % (anchor, path))


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_text(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ---------------------------------------------------------------------------
# Step 1: Info.plist
# ---------------------------------------------------------------------------

def patch_info_plist(plist_path, changed):
    with open(plist_path, "rb") as f:
        data = plistlib.load(f)
    if not isinstance(data, dict):
        die("unexpected Info.plist content (not a dict) in %s" % plist_path)
    if "UIApplicationSceneManifest" in data:
        print("  already patched: UIApplicationSceneManifest in %s" % plist_path)
        return
    data["UIApplicationSceneManifest"] = SCENE_MANIFEST
    with open(plist_path, "wb") as f:
        plistlib.dump(data, f, sort_keys=False)
    changed.append(plist_path)


# ---------------------------------------------------------------------------
# Step 2: AppDelegate.m
# ---------------------------------------------------------------------------

RE_BUNDLE_NAME = re.compile(
    r'^#define\s+BUNDLE_NAME\s+@"([^"]*)"', re.M)
RE_INSTANCE_NAME = re.compile(
    r'^([ \t]*)NSString\s*\*instanceName\s*=\s*\[NSString\s+stringWithFormat:@'
    r'"%@:%@:%@"\s*,\s*BUNDLE_NAME\s*,\s*@"entry"\s*,\s*@"EntryAbility"\];[ \t]*$',
    re.M)
RE_MAIN_VIEW = re.compile(
    r'^[ \t]*EntryEntryAbilityViewController\s*\*mainView\s*=\s*'
    r'\[\[EntryEntryAbilityViewController\s+alloc\]\s+'
    r'initWithInstanceName:instanceName\];[ \t]*$', re.M)
RE_SET_NAV = re.compile(
    r'^[ \t]*\[self\s+setNavRootVC:mainView\];[ \t]*$', re.M)

DIDFINISH_COMMENT = (
    "// %s: window and root VC are created in SceneDelegate "
    "scene:willConnectToSession:options:" % MARKER)

CONFIG_METHOD = """\
// %(m)s: UIScene lifecycle (TN3187) — supply the scene configuration.
- (UISceneConfiguration *)application:(UIApplication *)application configurationForConnectingSceneSession:(UISceneSession *)connectingSceneSession options:(UISceneConnectionOptions *)options {
    return [[UISceneConfiguration alloc] initWithName:@"Default Configuration" sessionRole:connectingSceneSession.role];
}

""" % {"m": MARKER}

# --bars 三种模式的公共片段（paper 色 #F3E8D6，与 CJMP 皮肤一致）。
PAPER_COLOR_DECL = (
    "    UIColor *paper = [UIColor colorWithRed:243.0/255.0 "
    "green:232.0/255.0 blue:214.0/255.0 alpha:1.0];")

# --bars hide 模式宏定义与 safeAreaInsets 导出钩子（C 函数 + 宏）。
# 单位 1/100 逻辑点，负数/NaN 记为 0；无任何硬编码 inset 数值常量。
# E2/E8 实测依据（2026-10-04 Mac，iPhone 17 402×874 pt，iOS 27.0，Xcode 27.0，
# 见 /workspace/cjmp-smoke/bios/E2_E3_E8_RESULTS.md）：app_didFinish 与
# scene_willConnect_pre 时 window.safeAreaInsets 为 0；makeKeyAndVisible 之后
# （整个 setNavRootVC:inScene: 返回后实测 =(62,0,34,0)；iPhone 16 为 59）已可读；
# vc.view.safeAreaInsets 在 viewDidLoad/viewWillAppear 仍为 0，要到
# viewSafeAreaInsetsDidChange 之后才非 0（hide 变体 =62/34），故一律读 window
# 而非根 VC view。E8 实测：仓颉 getVariable 能读到宿主 setenv
# （YILU_SAFE_TOP=6200，逐字节 ASCII 解析无误）。
HIDE_MACROS_AND_SAFE_EXPORT = """\
#ifndef YILU_SAFE_EXPORT
#define YILU_SAFE_EXPORT 1
#endif
#ifndef YILU_SAFE_TOP_FIXED_HUNDREDTHS
// Default undefined: dynamically exported from UIView.safeAreaInsets.
// Define to override with a fixed hundredths-of-a-point integer.
#endif
#ifndef YILU_SAFE_BOTTOM_FIXED_HUNDREDTHS
// Default undefined: dynamically exported from UIView.safeAreaInsets.
// Define to override with a fixed hundredths-of-a-point integer.
#endif

#if YILU_SAFE_EXPORT
static inline void yilu_export_safe_insets(UIView *v) {
    if (!v) {
        return;
    }
    UIEdgeInsets insets = v.safeAreaInsets;
    long top_h = 0;
#ifdef YILU_SAFE_TOP_FIXED_HUNDREDTHS
    top_h = (long)(YILU_SAFE_TOP_FIXED_HUNDREDTHS);
#else
    if (!isnan(insets.top) && insets.top > 0.0) {
        top_h = (long)(insets.top * 100.0 + 0.5);
    }
#endif

    long bottom_h = 0;
#ifdef YILU_SAFE_BOTTOM_FIXED_HUNDREDTHS
    bottom_h = (long)(YILU_SAFE_BOTTOM_FIXED_HUNDREDTHS);
#else
    if (!isnan(insets.bottom) && insets.bottom > 0.0) {
        bottom_h = (long)(insets.bottom * 100.0 + 0.5);
    }
#endif

    char buf[32];
    snprintf(buf, sizeof(buf), "%ld", top_h);
    setenv("YILU_SAFE_TOP", buf, 1);

    char buf2[32];
    snprintf(buf2, sizeof(buf2), "%ld", bottom_h);
    setenv("YILU_SAFE_BOTTOM", buf2, 1);
}
#endif
"""

# --bars hide 模式专用的 UINavigationController 子类定义（覆写深色内容状态栏）。
# viewSafeAreaInsetsDidChange / viewWillTransitionToSize: 两个补导出方法在
# #if YILU_SAFE_EXPORT 保护内，且整个类定义位于 yilu_export_safe_insets 的
# static inline 定义（HIDE_MACROS_AND_SAFE_EXPORT）之后，同一编译单元内可见。
# AppDelegate.m 在 keels 工程里是 Objective-C++（.mm）：static inline 同文件
# 使用不受名字修饰影响，block 语法合法。
YILU_NAVI_CONTROLLER_DECL = """\
@interface YiluNavigationController : UINavigationController
@end

@implementation YiluNavigationController
- (UIStatusBarStyle)preferredStatusBarStyle {
    return UIStatusBarStyleDarkContent;
}
- (UIViewController *)childViewControllerForStatusBarStyle {
    return nil;
}
- (BOOL)prefersStatusBarHidden {
    return NO;
}
#if YILU_SAFE_EXPORT
// E2 实测(2026-10-04 Mac, iPhone 17 402×874, iOS 27.0): vc.view.safeAreaInsets
// 在 viewDidLoad/viewWillAppear 仍为 0, viewSafeAreaInsetsDidChange 之后才非 0
// (hide 变体 =62/34), 此处变化后补导出。
- (void)viewSafeAreaInsetsDidChange {
    [super viewSafeAreaInsetsDidChange];
    yilu_export_safe_insets(self.view);
}
// 转屏/分屏等尺寸变化完成后补导出。
- (void)viewWillTransitionToSize:(CGSize)size withTransitionCoordinator:(id<UIViewControllerTransitionCoordinator>)coordinator {
    [super viewWillTransitionToSize:size withTransitionCoordinator:coordinator];
    [coordinator animateAlongsideTransition:nil completion:^(id<UIViewControllerTransitionCoordinatorContext> context) {
        yilu_export_safe_insets(self.view);
    }];
}
#endif
@end
"""

APP_DELEGATE_HIDE_HEADER = (
    "// %s: hide-mode status bar & safe area insets export\n"
    "%s\n"
    "%s\n"
) % (MARKER, HIDE_MACROS_AND_SAFE_EXPORT, YILU_NAVI_CONTROLLER_DECL)

IN_SCENE_METHOD_OFF = """\
    self.window = [[UIWindow alloc] initWithWindowScene:scene];
    self.window.backgroundColor = [UIColor whiteColor];
    [self.window makeKeyAndVisible];
    UINavigationController *navi = [[UINavigationController alloc]initWithRootViewController:viewController];
    [self setNaviAppearance:navi];
    self.window.rootViewController = navi;
"""

IN_SCENE_METHOD_PAPER = """\
%(paper_decl)s
    self.window = [[UIWindow alloc] initWithWindowScene:scene];
    self.window.backgroundColor = paper;
    [self.window makeKeyAndVisible];
    UINavigationController *navi = [[UINavigationController alloc]initWithRootViewController:viewController];
    self.window.overrideUserInterfaceStyle = UIUserInterfaceStyleLight;
    [self setNaviAppearance:navi];
    UINavigationBarAppearance *barsAppearance = [UINavigationBarAppearance new];
    [barsAppearance configureWithOpaqueBackground];
    barsAppearance.backgroundColor = paper;
    barsAppearance.shadowColor = [UIColor clearColor];
    navi.navigationBar.standardAppearance = barsAppearance;
    navi.navigationBar.scrollEdgeAppearance = barsAppearance;
    self.window.rootViewController = navi;
"""

IN_SCENE_METHOD_HIDE = """\
%(paper_decl)s
    self.window = [[UIWindow alloc] initWithWindowScene:scene];
    self.window.backgroundColor = paper;
    [self.window makeKeyAndVisible];
    [self.window layoutIfNeeded];
#if YILU_SAFE_EXPORT
    // E2 实测(2026-10-04 Mac, iPhone 17 402×874, iOS 27.0, Xcode 27.0):
    // app_didFinish 与 willConnect_pre 时 window.safeAreaInsets 为 0;
    // makeKeyAndVisible 之后已可读(rootViewController 赋值后实测 =(62,0,34,0),
    // iPhone 16 为 59);vc.view.safeAreaInsets 要到 viewSafeAreaInsetsDidChange
    // 之后才非 0, 故读 window 而非 vc.view;layoutIfNeeded 先让 window 布局落地。
    // E8 实测:仓颉 getVariable 可读到宿主 setenv(YILU_SAFE_TOP=6200,ASCII 解析无误)。
    yilu_export_safe_insets(self.window);
#endif
    // E3 实测(2026-10-04 Mac):模板 VC edgesForExtendedLayout=UIRectEdgeNone、
    // extendedLayoutIncludesOpaqueBars=1;hide 模式导航栏隐藏后 vc.view 全屏
    //(0,0,402,874),无白带,无需改 edgesForExtendedLayout。
    ((UIViewController *)viewController).view.backgroundColor = paper;
    YiluNavigationController *navi = [[YiluNavigationController alloc]initWithRootViewController:viewController];
    self.window.overrideUserInterfaceStyle = UIUserInterfaceStyleLight;
    navi.view.backgroundColor = paper;
    [navi setNavigationBarHidden:YES animated:NO];
    [self setNaviAppearance:navi];
    self.window.rootViewController = navi;
#if YILU_SAFE_EXPORT
    // E2 实测:rootViewController 赋值后 window.safeAreaInsets=(62,0,34,0) 已可读,
    // 此为实测已证明非 0 的时机,再导出一次兜底(首帧布局前仓颉 getVariable 可读到)。
    yilu_export_safe_insets(self.window);
#endif
"""


def in_scene_method(bars):
    """生成 setNavRootVC:inScene: 方法文本（含 MARKER 注释头与模式注释行）。

    off   —— 与 Keels 模板原文本逐字相同（window 背景 whiteColor）。
    paper —— window 背景改 paper，强制浅色模式；导航栏保留，但在
             setNaviAppearance 之后重设 standardAppearance/scrollEdgeAppearance
             为 opaque paper、无阴影细线。
    hide  —— window/navi/root-VC 背景改 paper，强制浅色模式，使用
             YiluNavigationController 隐藏导航栏并提供 UIStatusBarStyleDarkContent，
             并按 E2 实测时机导出 safe area inset：makeKeyAndVisible +
             layoutIfNeeded 之后一次（早于触发 viewDidLoad 的
             viewController.view.backgroundColor 访问）、rootViewController
             赋值之后一次；viewSafeAreaInsetsDidChange / viewWillTransitionToSize:
             / sceneDidBecomeActive: 再补读。
    """
    bodies = {"off": IN_SCENE_METHOD_OFF,
              "paper": IN_SCENE_METHOD_PAPER,
              "hide": IN_SCENE_METHOD_HIDE}
    if bars not in bodies:
        die("unknown --bars mode: %r" % bars)
    return """\
// %(m)s: UIScene lifecycle — the window belongs to a UIWindowScene.
// yilu-bars-patch: mode=%(bars)s (see app-ios-android/README.md)
- (void)setNavRootVC:(id)viewController inScene:(UIWindowScene *)scene {
%(body)s}

""" % {"m": MARKER, "bars": bars,
           "body": bodies[bars] % {"paper_decl": PAPER_COLOR_DECL}}


def insert_before_line(text, line_pred, block, anchor, path):
    """Insert `block` before the first line matching `line_pred` (a function
    line -> bool). `anchor` names the required anchor for error messages."""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line_pred(line):
            return "".join(lines[:i]) + block + "".join(lines[i:])
    anchor_error(anchor, path)


# 已打补丁方法里的模式注释行（用于检测模式冲突）。
RE_BARS_MODE = re.compile(r"//\s*yilu-bars-patch:\s*mode=(\w+)")

RE_EXPORT_CALL = re.compile(r"yilu_export_safe_insets\(")

# E2/E3 的旧 TODO 占位标记（拼接构造，避免本文件自身出现字面量）。
STALE_MARKERS = ("TODO(" + "E2)", "TODO(" + "E3)")


def _method_body(text, sig_needle):
    """提取 ObjC 方法体：从签名行起，到下一个列 0 的 '}'（含）为止。

    生成的方法体内部大括号都带缩进（4 空格），列 0 的 '}' 一定是方法收尾。
    找不到签名或收尾时返回 None。
    """
    i = text.find(sig_needle)
    if i < 0:
        return None
    j = text.find("\n}", i)
    if j < 0:
        return None
    return text[i:j]


def check_hide_inset_timing(adm_text):
    """hide 模式 AppDelegate.m 的 safe-inset 导出时序静态检查。返回 (ok, msg)。

    依据 E2/E3 实测（2026-10-04 Mac，iPhone 17 402×874，iOS 27.0；见
    /workspace/cjmp-smoke/bios/E2_E3_E8_RESULTS.md）：
      * setNavRootVC:inScene: 里所有 yilu_export_safe_insets( 调用都晚于
        makeKeyAndVisible；
      * 第一次导出晚于 makeKeyAndVisible、早于 viewController).view.backgroundColor
        （会触发 viewDidLoad 的访问），且 makeKeyAndVisible 与第一次导出之间
        有 layoutIfNeeded；
      * self.window.rootViewController = navi; 之后还有一次导出（实测已证明
        该时机 window.safeAreaInsets=(62,0,34,0)）；
      * YiluNavigationController 有 viewSafeAreaInsetsDidChange 并在其中调用
        导出（调 super）；有 viewWillTransitionToSize: 且其 completion 里调用
        导出（调 super）；
      * 文本里不得残留 E2/E3 的 TODO 占位标记。
    """
    errors = []
    body = _method_body(adm_text, "setNavRootVC:(id)viewController inScene:")
    if body is None:
        return False, "setNavRootVC:inScene: method not found"
    mk = body.find("makeKeyAndVisible")
    if mk < 0:
        errors.append("setNavRootVC:inScene: has no makeKeyAndVisible")
    exports = [m.start() for m in RE_EXPORT_CALL.finditer(body)]
    if not exports:
        errors.append("setNavRootVC:inScene: has no yilu_export_safe_insets call")
    if mk >= 0 and any(pos < mk for pos in exports):
        errors.append("export call before makeKeyAndVisible")
    bg = body.find("viewController).view.backgroundColor")
    if exports and mk >= 0 and exports[0] < mk:
        errors.append("first export not after makeKeyAndVisible")
    if exports and bg >= 0 and exports[0] > bg:
        errors.append("first export not before viewController).view.backgroundColor "
                      "(must precede the viewDidLoad-triggering view access)")
    if exports and mk >= 0 and "[self.window layoutIfNeeded]" not in body[mk:exports[0]]:
        errors.append("no [self.window layoutIfNeeded] between makeKeyAndVisible "
                      "and first export")
    rvc = body.find("self.window.rootViewController = navi;")
    if rvc >= 0 and not any(pos > rvc for pos in exports):
        errors.append("no export after self.window.rootViewController = navi;")
    vsaid = _method_body(adm_text, "- (void)viewSafeAreaInsetsDidChange")
    if vsaid is None:
        errors.append("YiluNavigationController: viewSafeAreaInsetsDidChange missing")
    else:
        if "[super viewSafeAreaInsetsDidChange]" not in vsaid:
            errors.append("viewSafeAreaInsetsDidChange does not call super")
        if not RE_EXPORT_CALL.search(vsaid):
            errors.append("viewSafeAreaInsetsDidChange does not export insets")
    vwt = _method_body(adm_text, "- (void)viewWillTransitionToSize:")
    if vwt is None:
        errors.append("YiluNavigationController: viewWillTransitionToSize: missing")
    else:
        if "[super viewWillTransitionToSize:" not in vwt:
            errors.append("viewWillTransitionToSize: does not call super")
        comp = vwt.find("completion:^")
        if comp < 0 or not RE_EXPORT_CALL.search(vwt[comp:]):
            errors.append("viewWillTransitionToSize: completion does not export insets")
    for marker in STALE_MARKERS:
        if marker in adm_text:
            errors.append("stale marker %s present" % marker)
    if errors:
        return False, "; ".join(dict.fromkeys(errors))
    return True, ("hide-mode inset timing OK: exports only after makeKeyAndVisible; "
                  "first export bracketed by layoutIfNeeded and "
                  "viewController).view.backgroundColor; re-export after "
                  "rootViewController; navi re-export hooks "
                  "(viewSafeAreaInsetsDidChange / viewWillTransitionToSize "
                  "completion) present; no stale E2/E3 markers")


def patch_app_delegate_m(m_path, changed, bars):
    src = read_text(m_path)

    # (a) BUNDLE_NAME value — required anchor (needed for SceneDelegate.m).
    m = RE_BUNDLE_NAME.search(src)
    if not m:
        anchor_error('#define BUNDLE_NAME @"..."', m_path)
    bundle_name = m.group(1)

    original = src

    # (b) Replace the three window/root-VC statements in didFinishLaunching.
    if DIDFINISH_COMMENT in src:
        print("  already patched: didFinishLaunching comment in %s" % m_path)
    else:
        m1 = RE_INSTANCE_NAME.search(src)
        m2 = RE_MAIN_VIEW.search(src)
        m3 = RE_SET_NAV.search(src)
        if not (m1 and m2 and m3):
            anchor_error(
                "instanceName/mainView/setNavRootVC statements in "
                "application:didFinishLaunchingWithOptions:", m_path)
        if not (m1.start() < m2.start() < m3.start()):
            anchor_error(
                "ordered instanceName/mainView/setNavRootVC statements in "
                "application:didFinishLaunchingWithOptions:", m_path)
        between = src[m1.end():m2.start()] + src[m2.end():m3.start()]
        if between.strip():
            anchor_error(
                "contiguous instanceName/mainView/setNavRootVC statements in "
                "application:didFinishLaunchingWithOptions:", m_path)
        indent = m1.group(1)
        src = (src[:m1.start()] + indent + DIDFINISH_COMMENT + "\n"
               + src[m3.end():])
        if "return YES;" not in src:
            anchor_error("return YES; in application:didFinishLaunchingWithOptions:", m_path)

    # (c) configurationForConnectingSceneSession before openURL.
    if "configurationForConnectingSceneSession" in src:
        print("  already patched: configurationForConnectingSceneSession in %s"
              % m_path)
    else:
        src = insert_before_line(
            src,
            lambda l: l.lstrip().startswith(
                "- (BOOL)application:(UIApplication *)app openURL:"),
            CONFIG_METHOD,
            "- (BOOL)application:(UIApplication *)app openURL:", m_path)

    # (d) YiluNavigationController and safe insets header (hide mode only), before @implementation AppDelegate.
    already_patched_nav = "setNavRootVC:(id)viewController inScene:" in src
    if bars == "hide" and not already_patched_nav:
        if "YiluNavigationController" in src:
            print("  already patched: YiluNavigationController in %s" % m_path)
        else:
            src = insert_before_line(
                src,
                lambda l: l.lstrip().startswith("@implementation AppDelegate"),
                APP_DELEGATE_HIDE_HEADER,
                "@implementation AppDelegate", m_path)

    # (e) setNavRootVC:inScene: before setNaviAppearance:.
    if already_patched_nav:
        print("  already patched: setNavRootVC:inScene: in %s" % m_path)
        # 已是补丁方法：若其中的 mode= 与本次请求不同，提示但不报错（幂等）。
        m = RE_BARS_MODE.search(src)
        if m and m.group(1) != bars:
            print("  NOTE: already patched with mode=%s, requested %s; "
                  "regenerate the host project to switch" % (m.group(1), bars))
    else:
        src = insert_before_line(
            src,
            lambda l: l.lstrip().startswith("- (void)setNaviAppearance:"),
            in_scene_method(bars),
            "- (void)setNaviAppearance:", m_path)

    if src != original:
        write_text(m_path, src)
        changed.append(m_path)
    return bundle_name


# ---------------------------------------------------------------------------
# Step 3: AppDelegate.h
# ---------------------------------------------------------------------------

H_DECLARATION = """\
// %s: UIScene lifecycle — scene-aware root VC setter.
- (void)setNavRootVC:(id)viewController inScene:(UIWindowScene *)scene;
""" % MARKER


def patch_app_delegate_h(h_path, changed):
    src = read_text(h_path)
    if "setNavRootVC:(id)viewController inScene:" in src:
        print("  already patched: inScene: declaration in %s" % h_path)
        return
    lines = src.splitlines(keepends=True)
    end_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "@end":
            end_idx = i
    if end_idx is None:
        anchor_error("final @end", h_path)
    src = "".join(lines[:end_idx]) + H_DECLARATION + "\n" + "".join(lines[end_idx:])
    write_text(h_path, src)
    changed.append(h_path)


# ---------------------------------------------------------------------------
# Step 4: SceneDelegate.h / SceneDelegate.m
# ---------------------------------------------------------------------------

def scene_delegate_h_text():
    return """\
//
// SceneDelegate.h
// %s: UIScene lifecycle delegate (TN3187). Original code written for CJMP.
//

#import <UIKit/UIKit.h>

@interface SceneDelegate : UIResponder <UIWindowSceneDelegate>

@property (strong, nonatomic) UIWindow *window;

@end
""" % MARKER


def scene_delegate_m_text(bundle_name, bars="hide"):
    if bars == "hide":
        return """\
//
// SceneDelegate.m
// %(m)s: UIScene lifecycle delegate (TN3187). Original code written for CJMP.
//

#import "SceneDelegate.h"
#import "AppDelegate.h"
#import "EntryEntryAbilityViewController.h"

#define BUNDLE_NAME @"%(b)s"

%(safe_export)s

@implementation SceneDelegate

- (void)scene:(UIScene *)scene willConnectToSession:(UISceneSession *)session options:(UISceneConnectionOptions *)connectionOptions {
    if (![scene isKindOfClass:[UIWindowScene class]]) {
        return;
    }
    NSString *instanceName = [NSString stringWithFormat:@"%%@:%%@:%%@",BUNDLE_NAME, @"entry", @"EntryAbility"];
    EntryEntryAbilityViewController *viewController = [[EntryEntryAbilityViewController alloc] initWithInstanceName:instanceName];
    [(AppDelegate *)UIApplication.sharedApplication.delegate setNavRootVC:viewController inScene:(UIWindowScene *)scene];
    self.window = ((AppDelegate *)UIApplication.sharedApplication.delegate).window;
}

- (void)sceneDidBecomeActive:(UIScene *)scene {
#if YILU_SAFE_EXPORT
    // E2 实测(2026-10-04 Mac):app_didFinish/willConnect 之前 inset 为 0,
    // makeKeyAndVisible 之后 window.safeAreaInsets=(62,0,34,0) 可读;此处补读兜底。
    yilu_export_safe_insets(self.window);
#endif
}

@end
""" % {"m": MARKER, "b": bundle_name, "safe_export": HIDE_MACROS_AND_SAFE_EXPORT}
    else:
        return """\
//
// SceneDelegate.m
// %(m)s: UIScene lifecycle delegate (TN3187). Original code written for CJMP.
//

#import "SceneDelegate.h"
#import "AppDelegate.h"
#import "EntryEntryAbilityViewController.h"

#define BUNDLE_NAME @"%(b)s"

@implementation SceneDelegate

- (void)scene:(UIScene *)scene willConnectToSession:(UISceneSession *)session options:(UISceneConnectionOptions *)connectionOptions {
    if (![scene isKindOfClass:[UIWindowScene class]]) {
        return;
    }
    NSString *instanceName = [NSString stringWithFormat:@"%%@:%%@:%%@",BUNDLE_NAME, @"entry", @"EntryAbility"];
    EntryEntryAbilityViewController *viewController = [[EntryEntryAbilityViewController alloc] initWithInstanceName:instanceName];
    [(AppDelegate *)UIApplication.sharedApplication.delegate setNavRootVC:viewController inScene:(UIWindowScene *)scene];
    self.window = ((AppDelegate *)UIApplication.sharedApplication.delegate).window;
}

@end
""" % {"m": MARKER, "b": bundle_name}


def write_scene_delegate(host_dir, bundle_name, changed, bars="hide"):
    h_path = os.path.join(host_dir, "SceneDelegate.h")
    m_path = os.path.join(host_dir, "SceneDelegate.m")
    if os.path.exists(h_path) and os.path.exists(m_path):
        print("  already patched: SceneDelegate.h/.m exist in %s" % host_dir)
        return
    write_text(h_path, scene_delegate_h_text())
    write_text(m_path, scene_delegate_m_text(bundle_name, bars))
    changed.append(h_path)
    changed.append(m_path)


# ---------------------------------------------------------------------------
# Step 5: project.pbxproj
# ---------------------------------------------------------------------------

RE_ID = re.compile(r"\b[0-9A-F]{24}\b")
RE_REF_H = re.compile(r"^[ \t]*[0-9A-F]{24} /\* AppDelegate\.h \*/ = \{isa = PBXFileReference;")
RE_REF_M = re.compile(r"^[ \t]*[0-9A-F]{24} /\* AppDelegate\.m \*/ = \{isa = PBXFileReference;")
RE_BUILD_M = re.compile(r"^[ \t]*[0-9A-F]{24} /\* AppDelegate\.m in Sources \*/ = \{isa = PBXBuildFile;")
RE_CHILD_H = re.compile(r"^[ \t]*[0-9A-F]{24} /\* AppDelegate\.h \*/,$")
RE_CHILD_M = re.compile(r"^[ \t]*[0-9A-F]{24} /\* AppDelegate\.m \*/,$")
RE_SRC_M = re.compile(r"^[ \t]*[0-9A-F]{24} /\* AppDelegate\.m in Sources \*/,$")


def new_pbx_ids(text, count=4):
    """Deterministic 24-char uppercase-hex IDs not present in `text`."""
    used = set(RE_ID.findall(text))
    ids = []
    candidate = PBX_ID_SEED
    while len(ids) < count:
        hexid = "%024X" % candidate
        if hexid not in used:
            ids.append(hexid)
        candidate += 1
    return ids


def patch_pbxproj(pbx_path, changed):
    src = read_text(pbx_path)
    if "SceneDelegate.m in Sources" in src:
        print("  already patched: SceneDelegate in %s" % pbx_path)
        return

    lines = src.splitlines(keepends=True)
    idx = {}
    for i, line in enumerate(lines):
        if "ref_h" not in idx and RE_REF_H.match(line):
            idx["ref_h"] = i
        elif "ref_m" not in idx and RE_REF_M.match(line):
            idx["ref_m"] = i
        elif "build_m" not in idx and RE_BUILD_M.match(line):
            idx["build_m"] = i
        elif "child_h" not in idx and RE_CHILD_H.match(line):
            idx["child_h"] = i
        elif "child_m" not in idx and RE_CHILD_M.match(line):
            idx["child_m"] = i
        elif "src_m" not in idx and RE_SRC_M.match(line):
            idx["src_m"] = i
    anchor_names = {
        "ref_h": "PBXFileReference line for AppDelegate.h",
        "ref_m": "PBXFileReference line for AppDelegate.m",
        "build_m": "PBXBuildFile line for AppDelegate.m in Sources",
        "child_h": "group children line '... /* AppDelegate.h */,'",
        "child_m": "group children line '... /* AppDelegate.m */,'",
        "src_m": "Sources phase line '... /* AppDelegate.m in Sources */,'",
    }
    for key, name in anchor_names.items():
        if key not in idx:
            anchor_error(name, pbx_path)

    # 4 fresh IDs (3 objects are created; the 4th keeps the sequence stable).
    id_h, id_m, id_build, _unused = new_pbx_ids(src, 4)

    def indent_of(i):
        line = lines[i]
        return line[:len(line) - len(line.lstrip("\t"))] or "\t\t"

    def newline(i, body):
        return "%s%s\n" % (indent_of(i), body)

    insertions = [
        (idx["ref_h"], newline(idx["ref_h"],
         '%s /* SceneDelegate.h */ = {isa = PBXFileReference; '
         'lastKnownFileType = sourcecode.c.h; path = SceneDelegate.h; '
         'sourceTree = "<group>"; };' % id_h)),
        (idx["ref_m"], newline(idx["ref_m"],
         '%s /* SceneDelegate.m */ = {isa = PBXFileReference; '
         'lastKnownFileType = sourcecode.c.objc; path = SceneDelegate.m; '
         'sourceTree = "<group>"; };' % id_m)),
        (idx["build_m"], newline(idx["build_m"],
         '%s /* SceneDelegate.m in Sources */ = {isa = PBXBuildFile; '
         'fileRef = %s /* SceneDelegate.m */; };' % (id_build, id_m))),
        (idx["child_h"], newline(idx["child_h"],
         '%s /* SceneDelegate.h */,' % id_h)),
        (idx["child_m"], newline(idx["child_m"],
         '%s /* SceneDelegate.m */,' % id_m)),
        (idx["src_m"], newline(idx["src_m"],
         '%s /* SceneDelegate.m in Sources */,' % id_build)),
    ]
    for i in sorted(insertions, key=lambda t: t[0], reverse=True):
        after, text = i
        lines.insert(after + 1, text)
    write_text(pbx_path, "".join(lines))
    changed.append(pbx_path)


# ---------------------------------------------------------------------------
# cmd: patch
# ---------------------------------------------------------------------------

def cmd_patch(ios_dir, name, bars):
    host_dir = os.path.join(ios_dir, name)
    pbx_path = os.path.join(ios_dir, "%s.xcodeproj" % name, "project.pbxproj")
    plist_path = os.path.join(host_dir, "Info.plist")
    adm_path = os.path.join(host_dir, "AppDelegate.m")
    adh_path = os.path.join(host_dir, "AppDelegate.h")
    for path, what in ((plist_path, "Info.plist"), (adm_path, "AppDelegate.m"),
                       (adh_path, "AppDelegate.h"), (pbx_path, "project.pbxproj")):
        if not os.path.isfile(path):
            die("expected file not found: %s (%s) — is <ios_dir> the generated "
                "ios directory?" % (path, what))

    changed = []
    patch_info_plist(plist_path, changed)
    bundle_name = patch_app_delegate_m(adm_path, changed, bars)
    patch_app_delegate_h(adh_path, changed)
    write_scene_delegate(host_dir, bundle_name, changed, bars)
    patch_pbxproj(pbx_path, changed)

    if changed:
        print("patch: %d file(s) changed:" % len(changed))
        for path in changed:
            print("  changed: %s" % path)
    else:
        print("patch: already patched — no changes made.")
    print("patch OK (%s)" % ios_dir)


# ---------------------------------------------------------------------------
# cmd: check-app
# ---------------------------------------------------------------------------

def cmd_check_app(app_path, name, expect_hide=False):
    plist_path = os.path.join(app_path, "Info.plist")
    if not os.path.isfile(plist_path):
        die("FAIL: Info.plist not found in %s" % app_path)
    with open(plist_path, "rb") as f:
        data = plistlib.load(f)

    manifest = data.get("UIApplicationSceneManifest")
    if not isinstance(manifest, dict):
        die("FAIL: %s Info.plist has no UIApplicationSceneManifest dict" % app_path)
    print("OK: UIApplicationSceneManifest present in %s" % plist_path)
    configs = manifest.get("UISceneConfigurations")
    if not isinstance(configs, dict):
        die("FAIL: UIApplicationSceneManifest has no UISceneConfigurations dict")
    roles = configs.get("UIWindowSceneSessionRoleApplication")
    if not isinstance(roles, list) or not roles:
        die("FAIL: UIWindowSceneSessionRoleApplication list is empty/missing")
    first = roles[0]
    if not isinstance(first, dict):
        die("FAIL: first UIWindowSceneSessionRoleApplication entry is not a dict")
    delegate = first.get("UISceneDelegateClassName")
    if not isinstance(delegate, str) or not delegate:
        die("FAIL: first UIWindowSceneSessionRoleApplication entry has no "
            "non-empty UISceneDelegateClassName")
    print("OK: scene delegate class = %s" % delegate)

    exe_name = data.get("CFBundleExecutable")
    if not isinstance(exe_name, str) or not exe_name:
        die("FAIL: Info.plist has no CFBundleExecutable")
    exe_path = os.path.join(app_path, exe_name)
    if not os.path.isfile(exe_path):
        die("FAIL: executable not found at %s" % exe_path)
    with open(exe_path, "rb") as f:
        exe_bytes = f.read()
    if delegate.encode("utf-8") not in exe_bytes:
        die("FAIL: class name %r not found in executable %s "
            "(was SceneDelegate.m compiled into the app?)"
            % (delegate, exe_path))
    print("OK: %s contains scene delegate class name" % exe_path)

    if expect_hide:
        if b"YiluNavigationController" not in exe_bytes:
            die("FAIL: class name 'YiluNavigationController' not found in executable %s "
                "(was hide-mode navigation controller compiled into the app?)"
                % exe_path)
        print("OK: %s contains YiluNavigationController class name" % exe_path)

    print("check-app OK (%s, name=%s)" % (app_path, name))


# ---------------------------------------------------------------------------
# cmd: fixture-from-sample
# ---------------------------------------------------------------------------

def cmd_fixture_from_sample(src_dir, dest_dir, from_name, name):
    src_host = os.path.join(src_dir, from_name)
    src_pbx = os.path.join(src_dir, "%s.xcodeproj" % from_name)
    for path in (src_host, src_pbx):
        if not os.path.isdir(path):
            die("sample path not found: %s" % path)
    dest_ios = os.path.join(dest_dir, "ios")
    os.makedirs(dest_ios, exist_ok=True)
    dest_host = os.path.join(dest_ios, name)
    if os.path.exists(dest_host):
        die("destination already exists: %s" % dest_host)
    shutil.copytree(src_host, dest_host)
    dest_pbx_dir = os.path.join(dest_ios, "%s.xcodeproj" % name)
    shutil.copytree(src_pbx, dest_pbx_dir)
    pbx_path = os.path.join(dest_pbx_dir, "project.pbxproj")
    src = read_text(pbx_path)
    write_text(pbx_path, src.replace(from_name, name))
    print("fixture-from-sample OK: %s -> %s (%s -> %s)"
          % (src_dir, dest_ios, from_name, name))


# ---------------------------------------------------------------------------
# cmd: selftest
# ---------------------------------------------------------------------------

FIXTURE_PLIST = {
    "CFBundleName": "$(PRODUCT_NAME)",
    "CFBundleIdentifier": "$(PRODUCT_BUNDLE_IDENTIFIER)",
}

FIXTURE_APPDELEGATE_H = """\
#import <UIKit/UIKit.h>

@interface AppDelegate : UIResponder <UIApplicationDelegate>

@property (nonatomic, strong) UIWindow *window;

@end
"""

FIXTURE_APPDELEGATE_M = """\
#import "AppDelegate.h"
#import "EntryEntryAbilityViewController.h"
#import <libkeels_ios/StageApplication.h>

#define BUNDLE_DIRECTORY @"keels"
#define BUNDLE_NAME @"com.yilu.xundian"

@implementation AppDelegate

- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)launchOptions {
    [StageApplication configModuleWithBundleDirectory:BUNDLE_DIRECTORY];
    [StageApplication launchApplication];

    NSString *instanceName = [NSString stringWithFormat:@"%@:%@:%@",BUNDLE_NAME, @"entry", @"EntryAbility"];
    EntryEntryAbilityViewController *mainView = [[EntryEntryAbilityViewController alloc] initWithInstanceName:instanceName];
    [self setNavRootVC:mainView];
    return YES;
}

- (BOOL)application:(UIApplication *)app openURL:(NSURL *)url options:(NSDictionary<NSString *,id> *)options {
    return YES;
}

- (void)setNavRootVC:(id)viewController {
    self.window = [[UIWindow alloc] initWithFrame:[UIScreen mainScreen].bounds];
    self.window.backgroundColor = [UIColor whiteColor];
    [self.window makeKeyAndVisible];
    UINavigationController *navi = [[UINavigationController alloc]initWithRootViewController:viewController];
    [self setNaviAppearance:navi];
    self.window.rootViewController = navi;
}

- (void)setNaviAppearance:(UINavigationController *)navi {
}

@end
"""

FIXTURE_PBXPROJ = """\
// !$*UTF8*$!
{
	archiveVersion = 1;
	classes = {
	};
	objectVersion = 50;
	objects = {

/* Begin PBXBuildFile section */
		F0AF1AD227D3684F008C55DD /* AppDelegate.m in Sources */ = {isa = PBXBuildFile; fileRef = F0AF1AD127D3684F008C55DD /* AppDelegate.m */; };
/* End PBXBuildFile section */

/* Begin PBXFileReference section */
		F0AF1AD027D3684F008C55DD /* AppDelegate.h */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.h; path = AppDelegate.h; sourceTree = "<group>"; };
		F0AF1AD127D3684F008C55DD /* AppDelegate.m */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.h; path = AppDelegate.m; sourceTree = "<group>"; };
/* End PBXFileReference section */

/* Begin PBXGroup section */
		F0AF1ACF27D3684F008C55DD /* xundian */ = {
			isa = PBXGroup;
			children = (
				F0AF1AD027D3684F008C55DD /* AppDelegate.h */,
				F0AF1AD127D3684F008C55DD /* AppDelegate.m */,
			);
			path = xundian;
			sourceTree = "<group>";
		};
/* End PBXGroup section */

/* Begin PBXSourcesBuildPhase section */
		F0AF1AC927D3684F008C55DD /* Sources */ = {
			isa = PBXSourcesBuildPhase;
			files = (
				F0AF1AD227D3684F008C55DD /* AppDelegate.m in Sources */,
			);
		};
/* End PBXSourcesBuildPhase section */
	};
	rootObject = F0AF1AC527D3684F008C55DD /* Project object */;
}
"""


def make_fixture(root, name="xundian"):
    ios_dir = os.path.join(root, "ios")
    host = os.path.join(ios_dir, name)
    os.makedirs(host)
    os.makedirs(os.path.join(ios_dir, "%s.xcodeproj" % name))
    with open(os.path.join(host, "Info.plist"), "wb") as f:
        plistlib.dump(FIXTURE_PLIST, f, sort_keys=False)
    write_text(os.path.join(host, "AppDelegate.h"), FIXTURE_APPDELEGATE_H)
    write_text(os.path.join(host, "AppDelegate.m"), FIXTURE_APPDELEGATE_M)
    write_text(os.path.join(ios_dir, "%s.xcodeproj" % name, "project.pbxproj"),
               FIXTURE_PBXPROJ)
    return ios_dir


def run_self(argv):
    return subprocess.run([sys.executable, __file__] + argv,
                          capture_output=True, text=True)


def selftest_assert(cond, msg):
    if not cond:
        die("selftest FAIL: %s" % msg)


def make_fake_app(root, with_manifest=True, with_class_bytes=True, with_hide_bytes=True):
    app = os.path.join(root, "xundian.app")
    os.makedirs(app)
    plist = {
        "CFBundleName": "xundian",
        "CFBundleIdentifier": "com.yilu.xundian",
        "CFBundleExecutable": "xundian",
    }
    if with_manifest:
        plist["UIApplicationSceneManifest"] = SCENE_MANIFEST
    with open(os.path.join(app, "Info.plist"), "wb") as f:
        plistlib.dump(plist, f, fmt=plistlib.FMT_BINARY, sort_keys=False)
    body = b"\xcf\xfa\xed\xfefake-macho"
    if with_class_bytes:
        body += b"\x00SceneDelegate\x00"
    if with_hide_bytes:
        body += b"\x00YiluNavigationController\x00"
    with open(os.path.join(app, "xundian"), "wb") as f:
        f.write(body)
    return app


def cmd_selftest():
    tmp = tempfile.mkdtemp(prefix="ios-scene-selftest-")
    try:
        # -- patch applies every edit ------------------------------------
        ios_dir = make_fixture(os.path.join(tmp, "a"))
        r = run_self(["patch", ios_dir, "--name", "xundian"])
        selftest_assert(r.returncode == 0,
                        "patch exit=%d stderr=%s" % (r.returncode, r.stderr))
        plist_path = os.path.join(ios_dir, "xundian", "Info.plist")
        with open(plist_path, "rb") as f:
            plist = plistlib.load(f)
        selftest_assert(plist.get("UIApplicationSceneManifest") == SCENE_MANIFEST,
                        "Info.plist manifest wrong")
        selftest_assert(plist.get("CFBundleName") == FIXTURE_PLIST["CFBundleName"],
                        "Info.plist lost existing keys")
        adm = read_text(os.path.join(ios_dir, "xundian", "AppDelegate.m"))
        selftest_assert("stringWithFormat" not in
                        adm.split("didFinishLaunchingWithOptions:", 1)[1].split("return YES;")[0],
                        "instanceName statement not removed")
        selftest_assert("initWithInstanceName:instanceName" not in adm.split("openURL:")[0],
                        "mainView statement not removed")
        selftest_assert("[self setNavRootVC:mainView];" not in adm,
                        "setNavRootVC:mainView statement not removed")
        selftest_assert("[StageApplication configModuleWithBundleDirectory:BUNDLE_DIRECTORY];" in adm,
                        "StageApplication config line lost")
        selftest_assert("[StageApplication launchApplication];" in adm,
                        "StageApplication launch line lost")
        selftest_assert("return YES;" in adm, "return YES; lost")
        selftest_assert("configurationForConnectingSceneSession" in adm,
                        "configurationForConnectingSceneSession missing")
        selftest_assert('initWithName:@"Default Configuration"' in adm,
                        "Default Configuration name missing")
        selftest_assert(adm.index("configurationForConnectingSceneSession")
                        < adm.index("- (BOOL)application:(UIApplication *)app openURL:"),
                        "config method not before openURL")
        selftest_assert("setNavRootVC:(id)viewController inScene:(UIWindowScene *)scene {" in adm,
                        "setNavRootVC:inScene: method missing")
        selftest_assert("[[UIWindow alloc] initWithWindowScene:scene]" in adm,
                        "initWithWindowScene missing")
        selftest_assert("[[UIWindow alloc] initWithFrame:[UIScreen mainScreen].bounds]" in adm,
                        "original setNavRootVC: body not preserved")
        selftest_assert(adm.index("setNavRootVC:(id)viewController inScene:")
                        < adm.index("- (void)setNaviAppearance:"),
                        "inScene method not before setNaviAppearance")
        adh = read_text(os.path.join(ios_dir, "xundian", "AppDelegate.h"))
        selftest_assert("- (void)setNavRootVC:(id)viewController inScene:(UIWindowScene *)scene;" in adh,
                        "AppDelegate.h declaration missing")
        selftest_assert(adh.rstrip().endswith("@end"), "AppDelegate.h @end not last")
        sdm = read_text(os.path.join(ios_dir, "xundian", "SceneDelegate.m"))
        selftest_assert('#import "SceneDelegate.h"' in sdm, "SceneDelegate.m imports")
        selftest_assert('#import "AppDelegate.h"' in sdm, "SceneDelegate.m imports")
        selftest_assert('#import "EntryEntryAbilityViewController.h"' in sdm,
                        "SceneDelegate.m imports")
        selftest_assert('#define BUNDLE_NAME @"com.yilu.xundian"' in sdm,
                        "SceneDelegate.m BUNDLE_NAME wrong")
        selftest_assert('stringWithFormat:@"%@:%@:%@",BUNDLE_NAME, @"entry", @"EntryAbility"' in sdm,
                        "SceneDelegate.m instanceName format wrong")
        selftest_assert("setNavRootVC:viewController inScene:(UIWindowScene *)scene" in sdm,
                        "SceneDelegate.m does not call setNavRootVC:inScene:")
        sdh = read_text(os.path.join(ios_dir, "xundian", "SceneDelegate.h"))
        selftest_assert("UIWindowSceneDelegate" in sdh and "UIWindow *window" in sdh,
                        "SceneDelegate.h interface wrong")
        pbx = read_text(os.path.join(ios_dir, "xundian.xcodeproj", "project.pbxproj"))
        selftest_assert("/* SceneDelegate.h */ = {isa = PBXFileReference; "
                        "lastKnownFileType = sourcecode.c.h;" in pbx,
                        "SceneDelegate.h PBXFileReference missing")
        selftest_assert("/* SceneDelegate.m */ = {isa = PBXFileReference; "
                        "lastKnownFileType = sourcecode.c.objc;" in pbx,
                        "SceneDelegate.m PBXFileReference missing")
        selftest_assert("/* SceneDelegate.m in Sources */ = {isa = PBXBuildFile;" in pbx,
                        "SceneDelegate.m PBXBuildFile missing")
        selftest_assert("/* SceneDelegate.m in Sources */," in pbx,
                        "SceneDelegate.m not in Sources phase files")
        selftest_assert("7E5CE4E000000000000000A1" in pbx, "deterministic ID seed missing")

        # -- 默认模式（不传 --bars）产出 hide --------------------------------
        m_def = RE_BARS_MODE.search(adm)
        selftest_assert(m_def is not None and m_def.group(1) == "hide",
                        "default --bars must be hide (mode comment: %r)"
                        % (m_def.group(1) if m_def else None))
        selftest_assert("YiluNavigationController" in adm,
                        "default (hide): YiluNavigationController missing")
        selftest_assert("UIStatusBarStyleDarkContent" in adm,
                        "default (hide): UIStatusBarStyleDarkContent missing")
        selftest_assert("setNavigationBarHidden:YES" in adm,
                        "default (hide): setNavigationBarHidden:YES missing")
        selftest_assert("243.0/255.0" in adm,
                        "default (hide): paper color missing")
        selftest_assert("yilu_export_safe_insets" in adm,
                        "default (hide): yilu_export_safe_insets missing in adm")
        selftest_assert('setenv("YILU_SAFE_TOP"' in adm,
                        "default (hide): setenv YILU_SAFE_TOP missing in adm")
        selftest_assert("snprintf" in adm,
                        "default (hide): snprintf missing in adm")
        selftest_assert("overrideUserInterfaceStyle" in adm,
                        "default (hide): forced light mode missing")
        selftest_assert(not re.search(r"top_h\s*=\s*[1-9]\d*", adm),
                        "default (hide): hardcoded number assigned to safe top")
        selftest_assert(not re.search(r"bottom_h\s*=\s*[1-9]\d*", adm),
                        "default (hide): hardcoded number assigned to safe bottom")
        selftest_assert(adm.count("{") == adm.count("}"),
                        "default (hide): AppDelegate.m braces unbalanced (%d vs %d)"
                        % (adm.count("{"), adm.count("}")))
        selftest_assert("sceneDidBecomeActive:" in sdm,
                        "default (hide): sceneDidBecomeActive missing in SceneDelegate.m")
        selftest_assert("yilu_export_safe_insets" in sdm,
                        "default (hide): yilu_export_safe_insets missing in SceneDelegate.m")
        selftest_assert(sdm.count("{") == sdm.count("}"),
                        "default (hide): SceneDelegate.m braces unbalanced (%d vs %d)"
                        % (sdm.count("{"), sdm.count("}")))
        # -- hide 导出时序（E2 实测固化）与旧 TODO 标记清除 ---------------
        ok, msg = check_hide_inset_timing(adm)
        selftest_assert(ok, "default (hide): inset timing check: %s" % msg)
        for marker in STALE_MARKERS:
            selftest_assert(marker not in adm,
                            "default (hide): stale %s in AppDelegate.m" % marker)
            selftest_assert(marker not in sdm,
                            "default (hide): stale %s in SceneDelegate.m" % marker)
        selftest_assert("layoutIfNeeded" in adm,
                        "default (hide): layoutIfNeeded missing in adm")
        with open(__file__, encoding="utf-8") as f:
            self_src = f.read()
        for marker in STALE_MARKERS:
            selftest_assert(marker not in self_src,
                            "patch_ios_scene.py source still contains %s" % marker)

        # -- patch is idempotent ------------------------------------------
        def snap(d):
            out = {}
            for base, _dirs, files in os.walk(d):
                for fn in files:
                    p = os.path.join(base, fn)
                    with open(p, "rb") as f:
                        out[p] = f.read()
            return out

        before = snap(ios_dir)
        r2 = run_self(["patch", ios_dir, "--name", "xundian"])
        selftest_assert(r2.returncode == 0, "second patch exit=%d" % r2.returncode)
        selftest_assert("no changes made" in r2.stdout + r2.stderr,
                        "second patch did not report no-changes: %r" % r2.stdout)
        selftest_assert(snap(ios_dir) == before, "second patch changed files")

        # -- --bars 三种模式的关键片段 ------------------------------------
        mode_dirs = {}
        for mode in ("off", "paper", "hide"):
            d = make_fixture(os.path.join(tmp, "bars-" + mode))
            r = run_self(["patch", d, "--name", "xundian", "--bars", mode])
            selftest_assert(r.returncode == 0,
                            "patch --bars %s exit=%d stderr=%s"
                            % (mode, r.returncode, r.stderr))
            mode_dirs[mode] = d
            adm_bars = read_text(os.path.join(d, "xundian", "AppDelegate.m"))
            sdm_bars = read_text(os.path.join(d, "xundian", "SceneDelegate.m"))
            selftest_assert("setNavRootVC:(id)viewController inScene:" in adm_bars,
                            "--bars %s: inScene method missing" % mode)
            selftest_assert(adm_bars.count("{") == adm_bars.count("}"),
                            "--bars %s: AppDelegate.m braces unbalanced" % mode)
            selftest_assert(sdm_bars.count("{") == sdm_bars.count("}"),
                            "--bars %s: SceneDelegate.m braces unbalanced" % mode)
            m = RE_BARS_MODE.search(adm_bars)
            selftest_assert(m is not None and m.group(1) == mode,
                            "--bars %s: mode comment wrong" % mode)
            if mode == "off":
                selftest_assert("whiteColor" in adm_bars,
                                "off: whiteColor missing")
                selftest_assert("setNavigationBarHidden" not in adm_bars,
                                "off: setNavigationBarHidden present")
                selftest_assert("YiluNavigationController" not in adm_bars,
                                "off: YiluNavigationController present in adm")
                selftest_assert("yilu_export_safe_insets" not in adm_bars,
                                "off: yilu_export_safe_insets present in adm")
                selftest_assert("UIStatusBarStyleDarkContent" not in adm_bars,
                                "off: UIStatusBarStyleDarkContent present in adm")
                selftest_assert("sceneDidBecomeActive:" not in sdm_bars,
                                "off: sceneDidBecomeActive present in SceneDelegate.m")
            elif mode == "paper":
                selftest_assert("243.0/255.0" in adm_bars,
                                "paper: paper color missing")
                selftest_assert("shadowColor" in adm_bars,
                                "paper: shadowColor missing")
                selftest_assert("setNavigationBarHidden:YES" not in adm_bars,
                                "paper: nav bar hidden")
                selftest_assert("YiluNavigationController" not in adm_bars,
                                "paper: YiluNavigationController present in adm")
                selftest_assert("yilu_export_safe_insets" not in adm_bars,
                                "paper: yilu_export_safe_insets present in adm")
                selftest_assert("UIStatusBarStyleDarkContent" not in adm_bars,
                                "paper: UIStatusBarStyleDarkContent present in adm")
                selftest_assert("sceneDidBecomeActive:" not in sdm_bars,
                                "paper: sceneDidBecomeActive present in SceneDelegate.m")
            else:
                selftest_assert("setNavigationBarHidden:YES" in adm_bars,
                                "hide: nav bar not hidden")
                selftest_assert("overrideUserInterfaceStyle" in adm_bars,
                                "hide: light mode missing")
                selftest_assert("YiluNavigationController" in adm_bars,
                                "hide: YiluNavigationController missing")
                selftest_assert("UIStatusBarStyleDarkContent" in adm_bars,
                                "hide: UIStatusBarStyleDarkContent missing")
                selftest_assert("243.0/255.0" in adm_bars,
                                "hide: paper color missing")
                selftest_assert("yilu_export_safe_insets" in adm_bars,
                                "hide: yilu_export_safe_insets missing in adm")
                selftest_assert('setenv("YILU_SAFE_TOP"' in adm_bars,
                                "hide: setenv YILU_SAFE_TOP missing in adm")
                selftest_assert("snprintf" in adm_bars,
                                "hide: snprintf missing in adm")
                selftest_assert(not re.search(r"top_h\s*=\s*[1-9]\d*", adm_bars),
                                "hide: hardcoded number assigned to safe top")
                selftest_assert(not re.search(r"bottom_h\s*=\s*[1-9]\d*", adm_bars),
                                "hide: hardcoded number assigned to safe bottom")
                selftest_assert("sceneDidBecomeActive:" in sdm_bars,
                                "hide: sceneDidBecomeActive missing in SceneDelegate.m")
                selftest_assert("yilu_export_safe_insets" in sdm_bars,
                                "hide: yilu_export_safe_insets missing in SceneDelegate.m")
                ok_bars, msg_bars = check_hide_inset_timing(adm_bars)
                selftest_assert(ok_bars,
                                "--bars hide: inset timing check: %s" % msg_bars)

        # -- 反例：时序违规的伪 AppDelegate.m 必须被判红 --------------------
        adm_hide = read_text(os.path.join(mode_dirs["hide"], "xundian",
                                          "AppDelegate.m"))
        good_head = ("    [self.window makeKeyAndVisible];\n"
                     "    [self.window layoutIfNeeded];\n"
                     "#if YILU_SAFE_EXPORT\n")
        bad_head = ("#if YILU_SAFE_EXPORT\n"
                    "    yilu_export_safe_insets(self.window);\n"
                    "#endif\n"
                    "    [self.window makeKeyAndVisible];\n")
        selftest_assert(good_head in adm_hide,
                        "counterexample head anchor missing in hide adm")
        bad_early = adm_hide.replace(good_head, bad_head, 1)
        selftest_assert(bad_early != adm_hide, "counterexample swap failed")
        ok, msg = check_hide_inset_timing(bad_early)
        selftest_assert(not ok and "before makeKeyAndVisible" in msg,
                        "counterexample (export before makeKeyAndVisible) not "
                        "detected: %s" % msg)
        export_stmt = "    yilu_export_safe_insets(self.window);\n"
        last = adm_hide.rfind(export_stmt)
        selftest_assert(last >= 0, "counterexample tail anchor missing")
        bad_tail = adm_hide[:last] + adm_hide[last + len(export_stmt):]
        ok, msg = check_hide_inset_timing(bad_tail)
        selftest_assert(not ok and "no export after" in msg,
                        "counterexample (no export after rootViewController) not "
                        "detected: %s" % msg)
        bad_nolayout = adm_hide.replace("    [self.window layoutIfNeeded];\n", "", 1)
        selftest_assert(bad_nolayout != adm_hide, "counterexample layout removal failed")
        ok, msg = check_hide_inset_timing(bad_nolayout)
        selftest_assert(not ok and "layoutIfNeeded" in msg,
                        "counterexample (no [self.window layoutIfNeeded]) not "
                        "detected: %s" % msg)
        bad_marker = adm_hide.replace(
            "#if YILU_SAFE_EXPORT\n",
            "#if YILU_SAFE_EXPORT\n    // %s: stale\n" % STALE_MARKERS[0], 1)
        selftest_assert(bad_marker != adm_hide, "counterexample marker insert failed")
        ok, msg = check_hide_inset_timing(bad_marker)
        selftest_assert(not ok and "stale marker" in msg,
                        "counterexample (stale E2 TODO marker) not detected: %s" % msg)

        # -- 同模式二次打补丁无变化（paper 为例） --------------------------
        d = mode_dirs["paper"]
        before_bars = snap(d)
        r = run_self(["patch", d, "--name", "xundian", "--bars", "paper"])
        selftest_assert(r.returncode == 0,
                        "paper re-patch exit=%d" % r.returncode)
        selftest_assert("no changes made" in r.stdout,
                        "paper re-patch did not report no-changes: %r" % r.stdout)
        selftest_assert(snap(d) == before_bars, "paper re-patch changed files")

        # -- 另一模式二次打补丁：打印 NOTE 且文件不变 -----------------------
        d = mode_dirs["hide"]
        before_switch = snap(d)
        r = run_self(["patch", d, "--name", "xundian", "--bars", "paper"])
        selftest_assert(r.returncode == 0,
                        "mode-switch re-patch exit=%d" % r.returncode)
        selftest_assert("NOTE: already patched with mode=hide, requested paper; "
                        "regenerate the host project to switch" in r.stdout + r.stderr,
                        "mode-switch NOTE missing: %r" % r.stdout)
        selftest_assert(snap(d) == before_switch,
                        "mode-switch re-patch changed files")

        # -- --bars 非法值：argparse 退出码 2 ------------------------------
        r = run_self(["patch", ios_dir, "--name", "xundian", "--bars", "bogus"])
        selftest_assert(r.returncode == 2,
                        "--bars bogus exit=%d (expected 2)" % r.returncode)

        # -- missing anchor -> exit 1 with anchor message ------------------
        ios2 = make_fixture(os.path.join(tmp, "b"))
        adm2 = os.path.join(ios2, "xundian", "AppDelegate.m")
        src = read_text(adm2).replace("- (void)setNaviAppearance:", "- (void)other:", 1)
        write_text(adm2, src)
        r3 = run_self(["patch", ios2, "--name", "xundian"])
        selftest_assert(r3.returncode == 1, "missing anchor exit=%d" % r3.returncode)
        selftest_assert("Keels template changed" in r3.stderr and "not found in" in r3.stderr,
                        "missing anchor message wrong: %r" % r3.stderr)

        # -- check-app good and bad ---------------------------------------
        app = make_fake_app(os.path.join(tmp, "app-ok"))
        rc = run_self(["check-app", app, "--name", "xundian"])
        selftest_assert(rc.returncode == 0 and "check-app OK" in rc.stdout,
                        "check-app OK case failed: %s%s" % (rc.stdout, rc.stderr))
        rc_hide = run_self(["check-app", app, "--name", "xundian", "--expect-hide"])
        selftest_assert(rc_hide.returncode == 0 and "contains YiluNavigationController" in rc_hide.stdout,
                        "check-app --expect-hide failed: %s%s" % (rc_hide.stdout, rc_hide.stderr))

        app_nohide = make_fake_app(os.path.join(tmp, "app-nohide"), with_hide_bytes=False)
        rc_nohide = run_self(["check-app", app_nohide, "--name", "xundian"])
        selftest_assert(rc_nohide.returncode == 0,
                        "check-app without --expect-hide should pass on nohide app")
        rc_fail_hide = run_self(["check-app", app_nohide, "--name", "xundian", "--expect-hide"])
        selftest_assert(rc_fail_hide.returncode == 1 and "FAIL" in rc_fail_hide.stderr,
                        "check-app with --expect-hide should fail on nohide app: %s%s" % (rc_fail_hide.stdout, rc_fail_hide.stderr))

        app_bad = make_fake_app(os.path.join(tmp, "app-noplist"),
                                with_manifest=False)
        rc = run_self(["check-app", app_bad, "--name", "xundian"])
        selftest_assert(rc.returncode == 1 and "FAIL" in rc.stderr,
                        "check-app no-manifest case should fail: %s%s" % (rc.stdout, rc.stderr))
        app_nosym = make_fake_app(os.path.join(tmp, "app-nosym"),
                                  with_class_bytes=False)
        rc = run_self(["check-app", app_nosym, "--name", "xundian"])
        selftest_assert(rc.returncode == 1 and "FAIL" in rc.stderr,
                        "check-app no-class-bytes case should fail: %s%s" % (rc.stdout, rc.stderr))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("selftest OK")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Patch the Keels iOS host for the UIScene lifecycle.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("patch", help="patch <ios_dir> (idempotent)")
    p.add_argument("ios_dir")
    p.add_argument("--name", default="xundian")
    p.add_argument("--bars", choices=["hide", "paper", "off"], default="hide",
                   help="status/nav bar treatment: hide, paper, or off "
                        "(default: hide)")

    p = sub.add_parser("check-app", help="verify a built .app bundle")
    p.add_argument("app_path")
    p.add_argument("--name", default="xundian")
    p.add_argument("--expect-hide", action="store_true",
                   help="assert YiluNavigationController is present in the executable (hide mode)")

    sub.add_parser("selftest", help="run the built-in test suite")

    p = sub.add_parser("fixture-from-sample",
                       help="copy a sample project as a rename fixture")
    p.add_argument("src_ios_dir")
    p.add_argument("dest_dir")
    p.add_argument("--from-name", default="testmarkdown")
    p.add_argument("--name", default="xundian")

    args = ap.parse_args(argv)
    if args.cmd == "patch":
        cmd_patch(args.ios_dir, args.name, args.bars)
    elif args.cmd == "check-app":
        cmd_check_app(args.app_path, args.name, args.expect_hide)
    elif args.cmd == "selftest":
        cmd_selftest()
    elif args.cmd == "fixture-from-sample":
        cmd_fixture_from_sample(args.src_ios_dir, args.dest_dir,
                                args.from_name, args.name)


if __name__ == "__main__":
    main()
