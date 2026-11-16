#!/usr/bin/env python3
"""patch_android_filesdir.py — 给 Keels 生成的 Android 宿主注入 YILU_FILES_DIR 环境变量。

背景：仓颉侧进度存档用 std.fs 后端（app-ios-android/lib/progress_io.cj 的
FileProgressBackend），它通过 std.env.getVariable("YILU_FILES_DIR") 找 app 私有
files 目录。但 Android 进程里没有现成的环境变量指向该目录（也不能指望 HOME），
所以必须由 Java 宿主在 onCreate 里、仓颉运行时启动之前 setenv。

本脚本在 EntryEntryAbilityActivity.java 的 onCreate 中、setInstanceName(...) 这一行
之前插入：

    android.system.Os.setenv("YILU_FILES_DIR", getFilesDir().getAbsolutePath(), true);

锚点取自 build_from_repo.sh STEP C2 使用的同一区域。注意 C2 会在
setInstanceName + super.onCreate + "}" 这三行文本之后追加 onBackPressed 方法，
因此本脚本：
  * 只用单行 setInstanceName 作锚点（三行锚点会不会已被 C2 改过是不可依赖的）；
  * 在锚点行之前插入，保证 C2 的三行锚点在打补丁后仍完整存在；
  * 不依赖 C2 是否已执行（两种先后顺序都验证过，见 selftest ⑥）。

锚点缺失或出现多次时以 "Keels template changed: anchor ... not found/ambiguous"
退出 1 —— 绝不静默跳过。

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

MARKER = "yilu-filesdir-patch"

# 单行锚点：必须恰好出现 1 次（build_from_repo.sh STEP C2 用的三行锚点包含此行）。
ANCHOR = '        setInstanceName("com.yilu.xundian:entry:EntryAbility:");\n'

# STEP C2 的三行锚点 —— 本补丁不得破坏它（C2 靠它追加 onBackPressed）。
C2_NEEDLE = (
    '        setInstanceName("com.yilu.xundian:entry:EntryAbility:");\n'
    '        super.onCreate(savedInstanceState);\n'
    '    }\n'
)

# 要插入的 setenv 块（全限定名，不需要加 import；插在 ANCHOR 之前即 super 之前）。
SETENV_BLOCK = """\
        // %(m)s: 把 app 私有 files 目录经环境变量交给仓颉侧（进度存档 std.fs 后端）
        try {
            android.system.Os.setenv("YILU_FILES_DIR", getFilesDir().getAbsolutePath(), true);
        } catch (Throwable t) {
            android.util.Log.e("xundian", "setenv YILU_FILES_DIR failed", t);
        }
""" % {"m": MARKER}

SENV = 'android.system.Os.setenv("YILU_FILES_DIR", getFilesDir().getAbsolutePath(), true)'
SUPER_ONCREATE = "super.onCreate(savedInstanceState);"


def die(msg):
    print("ERROR: %s" % msg, file=sys.stderr)
    sys.exit(1)


def anchor_error(anchor, path):
    die('Keels template changed: anchor %s not found/ambiguous in %s'
        % (anchor, path))


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_text(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def is_patched(src):
    """是否已打补丁：MARKER 存在且 setenv 位于 super.onCreate 之前。"""
    if MARKER not in src:
        return False
    if SENV not in src or SUPER_ONCREATE not in src:
        return False
    return src.index(SENV) < src.index(SUPER_ONCREATE)


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
    if src.count(ANCHOR) != 1:
        anchor_error('setInstanceName("com.yilu.xundian:entry:EntryAbility:") '
                     'line in onCreate', path)
    # 插在锚点行之前（即 super.onCreate 之前）；三行 C2 锚点保持原样。
    write_text(path, src.replace(ANCHOR, SETENV_BLOCK + ANCHOR, 1))

    # 重新读文件校验，防止写入意外破坏结构。
    after = read_text(path)
    if MARKER not in after or SENV not in after:
        die("post-patch verify failed: marker/setenv missing in %s" % path)
    if not (after.index(SENV) < after.index(SUPER_ONCREATE)):
        die("post-patch verify failed: setenv not before super.onCreate in %s"
            % path)
    if after.count(C2_NEEDLE) != 1:
        die("post-patch verify failed: STEP C2 anchor not intact in %s" % path)
    print("patched: YILU_FILES_DIR setenv injected into onCreate")
    print("patch OK (%s)" % path)


# ---------------------------------------------------------------------------
# cmd: check
# ---------------------------------------------------------------------------

def cmd_check(path):
    if not os.path.isfile(path):
        die("file not found: %s" % path)
    if not is_patched(read_text(path)):
        die("not patched (no %s setenv before super.onCreate) in %s"
            % (MARKER, path))
    print("check OK (%s)" % path)


# ---------------------------------------------------------------------------
# cmd: selftest
# ---------------------------------------------------------------------------

# 内置最小 Activity 样例（与 Keels 生成的结构同形：package / import /
# StageActivity 子类 / onCreate 含三行锚点）。
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

# build_from_repo.sh STEP C2 追加的 onBackPressed 方法（原样照抄，用于模拟 C2）。
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


def run_self(argv):
    return subprocess.run([sys.executable, __file__] + argv,
                          capture_output=True, text=True)


def selftest_assert(cond, msg):
    if not cond:
        die("selftest FAIL: %s" % msg)


def cmd_selftest():
    tmp = tempfile.mkdtemp(prefix="android-filesdir-selftest-")
    try:
        # -- ① 首次 patch 成功且结构正确 ----------------------------------
        act = make_fixture(os.path.join(tmp, "a"))
        r = run_self(["patch", act])
        selftest_assert(r.returncode == 0,
                        "patch exit=%d stderr=%s" % (r.returncode, r.stderr))
        src = read_text(act)
        selftest_assert(MARKER in src, "marker missing")
        selftest_assert(SENV in src, "setenv missing")
        selftest_assert(src.index(SENV) < src.index(SUPER_ONCREATE),
                        "setenv not before super.onCreate")
        selftest_assert(src.index(SETENV_BLOCK) < src.index(ANCHOR),
                        "block not before setInstanceName")
        selftest_assert(src.count(C2_NEEDLE) == 1, "C2 anchor not intact")
        selftest_assert('package com.yilu.xundian;' in src,
                        "fixture body lost")
        selftest_assert("getFilesDir().getAbsolutePath()" in src,
                        "getFilesDir call missing")

        # -- ② 二次 patch 幂等（字节不变、退出码 0）----------------------
        before = open(act, "rb").read()
        r2 = run_self(["patch", act])
        selftest_assert(r2.returncode == 0, "second patch exit=%d" % r2.returncode)
        selftest_assert("already patched" in r2.stdout,
                        "second patch did not say already patched: %r" % r2.stdout)
        selftest_assert(open(act, "rb").read() == before,
                        "second patch changed the file")

        # -- check 子命令对已打补丁文件应通过 ----------------------------
        rc = run_self(["check", act])
        selftest_assert(rc.returncode == 0 and "check OK" in rc.stdout,
                        "check on patched file failed: %s%s" % (rc.stdout, rc.stderr))

        # -- ③ 锚点缺失（setInstanceName 行被改）→ 退出 1 ----------------
        act3 = make_fixture(os.path.join(tmp, "c"))
        write_text(act3, read_text(act3).replace(
            'setInstanceName("com.yilu.xundian:entry:EntryAbility:");',
            'setInstanceName("com.yilu.other:entry:Other:");'))
        r3 = run_self(["patch", act3])
        selftest_assert(r3.returncode == 1, "missing anchor exit=%d" % r3.returncode)
        selftest_assert("Keels template changed" in r3.stderr,
                        "missing anchor message wrong: %r" % r3.stderr)

        # -- ④ 锚点出现两次 → 退出 1 -------------------------------------
        act4 = make_fixture(os.path.join(tmp, "d"))
        write_text(act4, read_text(act4).replace(
            "    }\n}", ANCHOR.rstrip("\n") + "\n    }\n}"))
        r4 = run_self(["patch", act4])
        selftest_assert(r4.returncode == 1, "double anchor exit=%d" % r4.returncode)
        selftest_assert("Keels template changed" in r4.stderr,
                        "double anchor message wrong: %r" % r4.stderr)

        # -- ⑤ 文件不存在 → 退出 1 ---------------------------------------
        r5 = run_self(["patch", os.path.join(tmp, "nope.java")])
        selftest_assert(r5.returncode == 1, "missing file exit=%d" % r5.returncode)

        # -- ⑥ 与 C2 两种先后顺序都要能工作 -------------------------------
        # ⑥a 先 C2 后本补丁
        act6a = make_fixture(os.path.join(tmp, "e"))
        apply_c2(act6a)
        r6a = run_self(["patch", act6a])
        selftest_assert(r6a.returncode == 0,
                        "patch after C2 exit=%d stderr=%s" % (r6a.returncode, r6a.stderr))
        src6a = read_text(act6a)
        selftest_assert("backPressed forward failed" in src6a, "C2 method lost")
        selftest_assert(src6a.index(SENV) < src6a.index(SUPER_ONCREATE),
                        "setenv not before super.onCreate (after C2)")
        selftest_assert(src6a.index(SETENV_BLOCK) < src6a.index(ANCHOR),
                        "block not before setInstanceName (after C2)")

        # ⑥b 先本补丁后 C2（C2 的三行锚点仍 count==1 且能追加）
        act6b = make_fixture(os.path.join(tmp, "f"))
        r6b = run_self(["patch", act6b])
        selftest_assert(r6b.returncode == 0,
                        "patch before C2 exit=%d stderr=%s" % (r6b.returncode, r6b.stderr))
        src6b = read_text(act6b)
        selftest_assert(src6b.count(C2_NEEDLE) == 1,
                        "C2 needle count != 1 after filesdir patch")
        apply_c2(act6b)
        src6b2 = read_text(act6b)
        selftest_assert("backPressed forward failed" in src6b2,
                        "C2 append failed after filesdir patch")
        selftest_assert(src6b2.index(SENV) < src6b2.index(SUPER_ONCREATE),
                        "setenv not before super.onCreate (C2 later)")
        rc6 = run_self(["check", act6b])
        selftest_assert(rc6.returncode == 0, "check after C2-later failed")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("selftest OK")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Inject android.system.Os.setenv(YILU_FILES_DIR, ...) into "
                    "the Keels-generated EntryEntryAbilityActivity.onCreate.")
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
