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

Anchors are taken from the Keels engine sample project (same toolchain, same
shape: ObjC AppDelegate with a `window` property, main.m, minimal Info.plist).
The real `keels create` output is UNCONFIRMED: every anchor is checked and a
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

IN_SCENE_METHOD = """\
// %(m)s: UIScene lifecycle — the window belongs to a UIWindowScene.
- (void)setNavRootVC:(id)viewController inScene:(UIWindowScene *)scene {
    self.window = [[UIWindow alloc] initWithWindowScene:scene];
    self.window.backgroundColor = [UIColor whiteColor];
    [self.window makeKeyAndVisible];
    UINavigationController *navi = [[UINavigationController alloc]initWithRootViewController:viewController];
    [self setNaviAppearance:navi];
    self.window.rootViewController = navi;
}

""" % {"m": MARKER}


def insert_before_line(text, line_pred, block, anchor, path):
    """Insert `block` before the first line matching `line_pred` (a function
    line -> bool). `anchor` names the required anchor for error messages."""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line_pred(line):
            return "".join(lines[:i]) + block + "".join(lines[i:])
    anchor_error(anchor, path)


def patch_app_delegate_m(m_path, changed):
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

    # (d) setNavRootVC:inScene: before setNaviAppearance:.
    if "setNavRootVC:(id)viewController inScene:" in src:
        print("  already patched: setNavRootVC:inScene: in %s" % m_path)
    else:
        src = insert_before_line(
            src,
            lambda l: l.lstrip().startswith("- (void)setNaviAppearance:"),
            IN_SCENE_METHOD,
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


def scene_delegate_m_text(bundle_name):
    return """\
//
// SceneDelegate.m
// %s: UIScene lifecycle delegate (TN3187). Original code written for CJMP.
//

#import "SceneDelegate.h"
#import "AppDelegate.h"
#import "EntryEntryAbilityViewController.h"

#define BUNDLE_NAME @"%s"

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
""" % (MARKER, bundle_name)


def write_scene_delegate(host_dir, bundle_name, changed):
    h_path = os.path.join(host_dir, "SceneDelegate.h")
    m_path = os.path.join(host_dir, "SceneDelegate.m")
    if os.path.exists(h_path) and os.path.exists(m_path):
        print("  already patched: SceneDelegate.h/.m exist in %s" % host_dir)
        return
    write_text(h_path, scene_delegate_h_text())
    write_text(m_path, scene_delegate_m_text(bundle_name))
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

def cmd_patch(ios_dir, name):
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
    bundle_name = patch_app_delegate_m(adm_path, changed)
    patch_app_delegate_h(adh_path, changed)
    write_scene_delegate(host_dir, bundle_name, changed)
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

def cmd_check_app(app_path, name):
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


def make_fake_app(root, with_manifest=True, with_class_bytes=True):
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

    p = sub.add_parser("check-app", help="verify a built .app bundle")
    p.add_argument("app_path")
    p.add_argument("--name", default="xundian")

    sub.add_parser("selftest", help="run the built-in test suite")

    p = sub.add_parser("fixture-from-sample",
                       help="copy a sample project as a rename fixture")
    p.add_argument("src_ios_dir")
    p.add_argument("dest_dir")
    p.add_argument("--from-name", default="testmarkdown")
    p.add_argument("--name", default="xundian")

    args = ap.parse_args(argv)
    if args.cmd == "patch":
        cmd_patch(args.ios_dir, args.name)
    elif args.cmd == "check-app":
        cmd_check_app(args.app_path, args.name)
    elif args.cmd == "selftest":
        cmd_selftest()
    elif args.cmd == "fixture-from-sample":
        cmd_fixture_from_sample(args.src_ios_dir, args.dest_dir,
                                args.from_name, args.name)


if __name__ == "__main__":
    main()
