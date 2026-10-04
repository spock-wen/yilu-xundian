#!/usr/bin/env python3
"""patch_android_bars.py — 给 Keels 生成的 Android 宿主把系统栏染成 paper 色。

背景：CJMP Android 无 iOS 那种白带，但系统状态栏(48.8dp)与导航栏(24dp)
是黑色，与纸色棋盘格格不入（见 investigate-top-whiteband 调查结论）。
宿主侧退路方案（SPEC A1）：statusBarColor/navigationBarColor = #F3E8D6
(paper) + 浅色图标（LIGHT_STATUS_BAR / LIGHT_NAVIGATION_BAR 即深色字形）。

注意（J27 方案 A）：build_from_repo.sh 的 STEP C4 默认**跳过**本脚本
（YILU_ANDROID_BARS 默认 off）——Mac 实测 API35 模拟器（A411 挖孔）上本补丁
零视觉效果：dumpsys 证实 flags 生效，但黑块 128px 是 mDisplayCutout inset
（> statusBars 63px），在应用窗口之外，setStatusBarColor 画不到那里。仅当
显式 YILU_ANDROID_BARS=on 时执行；真正消除黑块需 edge-to-edge（方案 B，另议）。

本脚本在 EntryEntryAbilityActivity.java 的类末尾（最后一个非空行必须恰好
是类的闭合 "}"）之前插入 onPostCreate 覆写。

与其他补丁的关系（都改同一个文件，任意顺序应用都必须成功）：
  * STEP C2（build_from_repo.sh 内联的 onBackPressed 追加）用的是
    onCreate 里的三行锚点 —— 本补丁只在类尾部插入，不碰那三行；
  * STEP C3（patch_android_filesdir.py 的 setenv 注入）在 setInstanceName
    行之前插入 —— 同样与本补丁的区域不相交。

锚点缺失/歧义时以 "Keels template changed: anchor ... not found/ambiguous"
退出 1 —— 绝不静默跳过。补丁幂等。

子命令：
  patch <EntryEntryAbilityActivity.java>   打补丁（幂等）
  check <EntryEntryAbilityActivity.java>   只校验已打补丁
  selftest                                跑内置测试

只用 Python 标准库。
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

MARKER = "yilu-bars-patch"

# STEP C2 的三行锚点（build_from_repo.sh / patch_android_filesdir.py 同款）
# —— 本补丁不得破坏它；C3 的单行锚点 setInstanceName 是它的第一行。
C2_NEEDLE = (
    '        setInstanceName("com.yilu.xundian:entry:EntryAbility:");\n'
    '        super.onCreate(savedInstanceState);\n'
    '    }\n'
)

# STEP C3 的单行锚点 —— 同上，补丁后必须恰好仍是 1 次。
C3_ANCHOR = '        setInstanceName("com.yilu.xundian:entry:EntryAbility:");\n'

# 要插入的 onPostCreate 方法（全限定名，不需要加 import；插在类末尾）。
BARS_METHOD = """
    // %s: 系统栏跟随 paper 色（SPEC A1 退路：statusBarColor/navigationBarColor = #F3E8D6 + 深色字形）
    @Override
    protected void onPostCreate(android.os.Bundle savedInstanceState) {
        super.onPostCreate(savedInstanceState);
        try {
            android.view.Window w = getWindow();
            w.setStatusBarColor(0xFFF3E8D6);
            w.setNavigationBarColor(0xFFF3E8D6);
            if (android.os.Build.VERSION.SDK_INT >= 29) {
                w.setNavigationBarContrastEnforced(false);
            }
            android.view.View d = w.getDecorView();
            int f = d.getSystemUiVisibility();
            if (android.os.Build.VERSION.SDK_INT >= 23) { f |= 0x00002000; } // SYSTEM_UI_FLAG_LIGHT_STATUS_BAR
            if (android.os.Build.VERSION.SDK_INT >= 26) { f |= 0x00000010; } // SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
            d.setSystemUiVisibility(f);
        } catch (Throwable t) {
            android.util.Log.e("xundian", "system bar patch failed", t);
        }
    }
""" % MARKER

ONPOST_CREATE = "onPostCreate("
ONPOST_DECL = "protected void onPostCreate("
SUPER_ONPOST = "super.onPostCreate(savedInstanceState);"


def die(msg):
    print("ERROR: %s" % msg, file=sys.stderr)
    sys.exit(1)


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_text(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def is_patched(src):
    """是否已打补丁：MARKER 存在且 onPostCreate 覆写在文件里。"""
    return MARKER in src and ONPOST_CREATE in src


def find_class_close(src):
    """返回最后一个非空行的下标；它 strip 后必须恰好是 '}'，否则 -1。

    这就是类（也是文件）的闭合括号 —— 插入点在它之前。
    """
    lines = src.splitlines(keepends=True)
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():
            return i if lines[i].strip() == "}" else -1
    return -1


# ---------------------------------------------------------------------------
# cmd: patch
# ---------------------------------------------------------------------------

def cmd_patch(path):
    if not os.path.isfile(path):
        die("file not found: %s — is it EntryEntryAbilityActivity.java "
            "from the Keels-generated Android host?" % path)
    src = read_text(path)
    if is_patched(src):
        print("already patched")
        print("patch OK (%s)" % path)
        return
    # 已有别的 onPostCreate（非本补丁）：再插入一个会编译失败，绝不覆盖。
    if ONPOST_CREATE in src:
        die("Keels template changed: onPostCreate already defined in %s" % path)
    idx = find_class_close(src)
    if idx < 0:
        die("Keels template changed: anchor final class closing brace "
            "not found/ambiguous in %s" % path)
    lines = src.splitlines(keepends=True)
    write_text(path, "".join(lines[:idx]) + BARS_METHOD + "".join(lines[idx:]))

    # 重新读文件校验，防止写入意外破坏结构。
    after = read_text(path)
    if not is_patched(after):
        die("post-patch verify failed: marker/onPostCreate missing in %s" % path)
    if after.count(ONPOST_DECL) != 1 or SUPER_ONPOST not in after:
        die("post-patch verify failed: onPostCreate malformed in %s" % path)
    if after.count(C2_NEEDLE) != 1:
        die("post-patch verify failed: STEP C2 anchor not intact in %s" % path)
    if after.count(C3_ANCHOR) != 1:
        die("post-patch verify failed: STEP C3 anchor not intact in %s" % path)
    if find_class_close(after) < 0 or not after.rstrip().endswith("}"):
        die("post-patch verify failed: class closing brace lost in %s" % path)
    print("patched: onPostCreate system-bar (paper #F3E8D6) injected")
    print("patch OK (%s)" % path)


# ---------------------------------------------------------------------------
# cmd: check
# ---------------------------------------------------------------------------

def cmd_check(path):
    if not os.path.isfile(path):
        die("file not found: %s" % path)
    if not is_patched(read_text(path)):
        die("not patched (no %s onPostCreate) in %s" % (MARKER, path))
    print("check OK (%s)" % path)


# ---------------------------------------------------------------------------
# cmd: selftest
# ---------------------------------------------------------------------------

# 内置最小 Activity 样例（与 Keels 生成的结构同形：package / import /
# StageActivity 子类 / onCreate 含三行锚点；与 patch_android_filesdir.py
# 的 fixture 同源）。
FIXTURE_ACTIVITY = """\
package com.yilu.xundian;

import android.os.Bundle;
import ohos.stage.ability.adapter.StageActivity;

public class EntryEntryAbilityActivity extends StageActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        setInstanceName("com.yilu.xundian:entry:EntryAbility:");
        super.onCreate(savedInstanceState);
    }
}
"""

# build_from_repo.sh STEP C2 追加的 onBackPressed 方法（脚本里没有可导入的
# Python 副本，这里内联一份等价文本，用于模拟 C2）。
C2_METHOD = '''
    @Override
    public void onBackPressed() {
        // Keels 0.2.2: ACE never routes page onBackPress on Android; default
        // super() finishes the app on the first back press. Forward to the
        // runtime first; if unconsumed, keep the app alive in background.
        try {
            java.lang.reflect.Field f =
                ohos.stage.ability.adapter.StageActivity.class.getDeclaredField("windowView");
            f.setAccessible(true);
            Object wv = f.get(this);
            if (wv != null && (Boolean) wv.getClass().getMethod("backPressed").invoke(wv)) {
                return;
            }
        } catch (Throwable t) {
            android.util.Log.e("xundian", "backPressed forward failed", t);
        }
        moveTaskToBack(true);
    }
'''

# STEP C3 就是同目录的 patch_android_filesdir.py —— 直接调用真实脚本。
FILESDIR_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "patch_android_filesdir.py")


def make_fixture(root):
    """在临时目录里生成一份 EntryEntryAbilityActivity.java，返回路径。"""
    d = os.path.join(root, "android", "app", "src", "main", "java",
                     "com", "yilu", "xundian")
    os.makedirs(d)
    path = os.path.join(d, "EntryEntryAbilityActivity.java")
    write_text(path, FIXTURE_ACTIVITY)
    return path


def apply_c2(path):
    """模拟 build_from_repo.sh STEP C2：三行锚点后追加 onBackPressed。"""
    src = read_text(path)
    assert src.count(C2_NEEDLE) == 1
    write_text(path, src.replace(C2_NEEDLE, C2_NEEDLE + C2_METHOD, 1))


def apply_c3(path):
    """模拟 STEP C3：调用真实的 patch_android_filesdir.py。"""
    r = subprocess.run([sys.executable, FILESDIR_PY, "patch", path],
                       capture_output=True, text=True)
    assert r.returncode == 0, "C3 (filesdir) patch failed: %s%s" % (r.stdout, r.stderr)


def run_self(argv):
    return subprocess.run([sys.executable, __file__] + argv,
                          capture_output=True, text=True)


def selftest_assert(cond, msg):
    if not cond:
        die("selftest FAIL: %s" % msg)


def assert_three_patches_coexist(path, tag):
    """C2+C3+bars 都在同一文件上时应共存：三块标记齐全且结构完好。"""
    src = read_text(path)
    selftest_assert("backPressed forward failed" in src,
                    "%s: C2 method lost" % tag)
    selftest_assert("yilu-filesdir-patch" in src and
                    "android.system.Os.setenv" in src,
                    "%s: C3 setenv lost" % tag)
    selftest_assert(MARKER in src and ONPOST_CREATE in src,
                    "%s: bars method lost" % tag)
    selftest_assert(src.count(ONPOST_DECL) == 1,
                    "%s: onPostCreate appears more than once" % tag)
    selftest_assert(src.count(C2_NEEDLE) == 1,
                    "%s: C2 anchor not intact" % tag)
    selftest_assert(src.count(C3_ANCHOR) == 1,
                    "%s: C3 anchor not intact" % tag)
    selftest_assert(src.rstrip().endswith("}"),
                    "%s: final closing brace lost" % tag)
    selftest_assert('package com.yilu.xundian;' in src,
                    "%s: fixture body lost" % tag)


def cmd_selftest():
    if not os.path.isfile(FILESDIR_PY):
        die("selftest FAIL: patch_android_filesdir.py not found next to me: %s"
            % FILESDIR_PY)
    tmp = tempfile.mkdtemp(prefix="android-bars-selftest-")
    try:
        # -- ① 首次 patch 成功且结构正确 ----------------------------------
        act = make_fixture(os.path.join(tmp, "a"))
        r = run_self(["patch", act])
        selftest_assert(r.returncode == 0,
                        "patch exit=%d stderr=%s" % (r.returncode, r.stderr))
        src = read_text(act)
        selftest_assert(MARKER in src, "marker missing")
        selftest_assert("w.setStatusBarColor(0xFFF3E8D6)" in src,
                        "setStatusBarColor missing")
        selftest_assert("w.setNavigationBarColor(0xFFF3E8D6)" in src,
                        "setNavigationBarColor missing")
        selftest_assert(src.rstrip().endswith("}"),
                        "final closing brace lost")
        selftest_assert(src.index(ONPOST_CREATE)
                        > src.index("class EntryEntryAbilityActivity"),
                        "method not inside class body")
        selftest_assert(src.count(C2_NEEDLE) == 1, "C2 anchor not intact")
        selftest_assert(src.count(C3_ANCHOR) == 1, "C3 anchor not intact")
        selftest_assert('package com.yilu.xundian;' in src,
                        "fixture body lost")

        # -- ② 二次 patch 幂等（字节不变、退出码 0）----------------------
        before = open(act, "rb").read()
        r2 = run_self(["patch", act])
        selftest_assert(r2.returncode == 0, "second patch exit=%d" % r2.returncode)
        selftest_assert("already patched" in r2.stdout,
                        "second patch did not say already patched: %r" % r2.stdout)
        selftest_assert(open(act, "rb").read() == before,
                        "second patch changed the file")

        # -- check 子命令：已打补丁返回 0，未打补丁退出 1 ----------------
        rc = run_self(["check", act])
        selftest_assert(rc.returncode == 0 and "check OK" in rc.stdout,
                        "check on patched file failed: %s%s" % (rc.stdout, rc.stderr))
        act_un = make_fixture(os.path.join(tmp, "a-unpatched"))
        rc_un = run_self(["check", act_un])
        selftest_assert(rc_un.returncode == 1,
                        "check on unpatched file exit=%d" % rc_un.returncode)

        # -- ③ 锚点缺失（最后一个非空行不是 "}"）→ 退出 1 ----------------
        act3 = make_fixture(os.path.join(tmp, "c"))
        write_text(act3, read_text(act3).rstrip("\n") + "\n// extra trailing line\n")
        r3 = run_self(["patch", act3])
        selftest_assert(r3.returncode == 1, "missing anchor exit=%d" % r3.returncode)
        selftest_assert("Keels template changed" in r3.stderr
                        and "final class closing brace" in r3.stderr,
                        "missing anchor message wrong: %r" % r3.stderr)

        # -- ④ 锚点歧义（类闭合 "}" 后还有代码）→ 退出 1 -----------------
        act4 = make_fixture(os.path.join(tmp, "d"))
        write_text(act4, read_text(act4).rstrip("\n") + "\nclass Extra {}\n")
        r4 = run_self(["patch", act4])
        selftest_assert(r4.returncode == 1, "ambiguous anchor exit=%d" % r4.returncode)
        selftest_assert("Keels template changed" in r4.stderr,
                        "ambiguous anchor message wrong: %r" % r4.stderr)

        # -- ⑤ 已有非本补丁的 onPostCreate → 退出 1 ----------------------
        act5 = make_fixture(os.path.join(tmp, "e"))
        write_text(act5, read_text(act5).replace(
            "    }\n}",
            "    }\n\n    @Override\n"
            "    protected void onPostCreate(Bundle b) {\n"
            "        super.onPostCreate(b);\n    }\n}"))
        r5 = run_self(["patch", act5])
        selftest_assert(r5.returncode == 1, "dup onPostCreate exit=%d" % r5.returncode)
        selftest_assert("Keels template changed" in r5.stderr
                        and "onPostCreate already defined" in r5.stderr,
                        "dup onPostCreate message wrong: %r" % r5.stderr)

        # -- ⑥ 文件不存在 → 退出 1 ---------------------------------------
        r6 = run_self(["patch", os.path.join(tmp, "nope.java")])
        selftest_assert(r6.returncode == 1, "missing file exit=%d" % r6.returncode)

        # -- ⑦ 与 C2/C3 两种先后顺序都要能工作 ----------------------------
        # ⑦a C2 → C3 → bars
        act7a = make_fixture(os.path.join(tmp, "f"))
        apply_c2(act7a)
        apply_c3(act7a)
        r7a = run_self(["patch", act7a])
        selftest_assert(r7a.returncode == 0,
                        "patch after C2+C3 exit=%d stderr=%s"
                        % (r7a.returncode, r7a.stderr))
        assert_three_patches_coexist(act7a, "C2->C3->bars")
        rc7a = run_self(["check", act7a])
        selftest_assert(rc7a.returncode == 0, "check after C2->C3->bars failed")

        # ⑦b bars → C2 → C3（C2/C3 的锚点在 bars 打过之后仍 count==1）
        act7b = make_fixture(os.path.join(tmp, "g"))
        r7b = run_self(["patch", act7b])
        selftest_assert(r7b.returncode == 0,
                        "patch before C2/C3 exit=%d stderr=%s"
                        % (r7b.returncode, r7b.stderr))
        src7b = read_text(act7b)
        selftest_assert(src7b.count(C2_NEEDLE) == 1,
                        "C2 needle count != 1 after bars patch")
        apply_c2(act7b)
        apply_c3(act7b)
        assert_three_patches_coexist(act7b, "bars->C2->C3")
        rc7b = run_self(["check", act7b])
        selftest_assert(rc7b.returncode == 0, "check after bars->C2->C3 failed")
        rc7b3 = subprocess.run([sys.executable, FILESDIR_PY, "check", act7b],
                               capture_output=True, text=True)
        selftest_assert(rc7b3.returncode == 0,
                        "filesdir check after bars->C2->C3 failed: %s%s"
                        % (rc7b3.stdout, rc7b3.stderr))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("selftest OK")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Inject onPostCreate system-bar coloring (paper #F3E8D6, "
                    "light icons) into the Keels-generated "
                    "EntryEntryAbilityActivity.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("patch", help="patch <Activity.java> (idempotent)")
    p.add_argument("java_file")

    p = sub.add_parser("check", help="verify the patch is present")
    p.add_argument("java_file")

    sub.add_parser("selftest", help="run the built-in test suite")

    args = ap.parse_args(argv)
    if args.cmd == "patch":
        cmd_patch(args.java_file)
    elif args.cmd == "check":
        cmd_check(args.java_file)
    elif args.cmd == "selftest":
        cmd_selftest()


if __name__ == "__main__":
    main()
