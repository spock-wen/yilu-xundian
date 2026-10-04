#!/usr/bin/env python3
"""check_build_defaults.py — 方案 B 的构建默认值静态检查。

PM / 设计师决定：
iOS 默认 hide（配合仓颉 safe-top/bottom padding，edge-to-edge）；默认值：

  * YILU_IOS_BARS     默认 hide（paper 保留可选、off 保留）
  * YILU_ANDROID_BARS 默认 off（STEP C4 仅显式 =on 才执行）

本脚本静态读取 build_from_repo.sh 与 patch_ios_scene.py，断言：
  a) 所有 `${YILU_IOS_BARS:-X}` 默认值 == hide，且 case 允许 hide|paper|off
  b) 所有 `${YILU_ANDROID_BARS:-X}` 默认值 == off，且 case 允许 on|off
  c) STEP D2 传给 patch_ios_scene.py 的 --bars 来自 `${YILU_IOS_BARS:-hide}`
  d) STEP C4 默认路径被跳过：存在 `if [ "${YILU_ANDROID_BARS:-off}" = "on" ]`
     门（patch_android_bars.py 调用只在其 on 分支内），且打印
     "skipping (default off"
  e) patch_ios_scene.py 的 --bars argparse default == "hide"（choices 含
     hide|paper|off）

--selftest：对一份把默认改回 paper/on、C4 门反转、D2 传 paper、argparse 默认
改回 paper 的合成 build_from_repo.sh / patch_ios_scene.py 能检出违规；对当前
仓库文件通过。只用 Python 标准库。
"""

import argparse
import os
import re
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
CJMP_DIR = os.path.dirname(SCRIPTS_DIR)

BUILD_SH = os.path.join(SCRIPTS_DIR, "build_from_repo.sh")
IOS_PY = os.path.join(SCRIPTS_DIR, "patch_ios_scene.py")

RE_IOS_DEFAULT = re.compile(r"\$\{YILU_IOS_BARS:-(\w+)\}")
RE_ANDROID_DEFAULT = re.compile(r"\$\{YILU_ANDROID_BARS:-(\w+)\}")
# STEP C4 的执行门：默认 off、显式 on 才进 patch 分支。
ANDROID_GATE = 'if [ "${YILU_ANDROID_BARS:-off}" = "on" ]; then'
# STEP D2 传参。
IOS_D2_ARG = '--bars "${YILU_IOS_BARS:-hide}"'
RE_IOS_ARGPARSE = re.compile(
    r'add_argument\(\s*"--bars",\s*choices=\[(?:"hide",\s*"paper",\s*"off"|'
    r'"paper",\s*"hide",\s*"off"|"off",\s*"paper",\s*"hide"[^]]*)\]\s*,\s*'
    r'default="hide"', re.S)


def check_defaults(build_sh_text, ios_py_text):
    """返回 (ok, msg)。build_sh_text / ios_py_text 是两份源文本。"""
    errors = []

    # a) YILU_IOS_BARS 默认 hide + case 允许 hide|paper|off
    ios_defaults = RE_IOS_DEFAULT.findall(build_sh_text)
    if not ios_defaults:
        errors.append("build_from_repo.sh: no ${YILU_IOS_BARS:-...} default found")
    for d in ios_defaults:
        if d != "hide":
            errors.append("build_from_repo.sh: YILU_IOS_BARS default is '%s', "
                          "expected hide (B3)" % d)
    if not re.search(r"hide\|paper\|off\)", build_sh_text):
        errors.append("build_from_repo.sh: YILU_IOS_BARS case must allow "
                      "hide|paper|off")

    # b) YILU_ANDROID_BARS 默认 off + case 允许 on|off
    android_defaults = RE_ANDROID_DEFAULT.findall(build_sh_text)
    if not android_defaults:
        errors.append("build_from_repo.sh: no ${YILU_ANDROID_BARS:-...} "
                      "default found")
    for d in android_defaults:
        if d != "off":
            errors.append("build_from_repo.sh: YILU_ANDROID_BARS default is "
                          "'%s', expected off (J27)" % d)
    if not re.search(r"\bon\|off\)", build_sh_text):
        errors.append("build_from_repo.sh: YILU_ANDROID_BARS case must allow "
                      "on|off")

    # c) STEP D2 --bars 传 ${YILU_IOS_BARS:-hide}
    if IOS_D2_ARG not in build_sh_text:
        errors.append("build_from_repo.sh: STEP D2 must pass '%s' to "
                      "patch_ios_scene.py" % IOS_D2_ARG)

    # d) STEP C4：默认（未设变量）路径跳过
    gate_idx = build_sh_text.find(ANDROID_GATE)
    if gate_idx < 0:
        errors.append("build_from_repo.sh: STEP C4 gate '%s' not found" %
                      ANDROID_GATE)
    else:
        # 注释里也会提到脚本名，只认真正的调用写法。
        call_idx = build_sh_text.find('"$SCRIPT_DIR/patch_android_bars.py"')
        if call_idx < 0:
            errors.append("build_from_repo.sh: STEP C4 never calls "
                          "patch_android_bars.py")
        else:
            else_idx = build_sh_text.find("else", gate_idx)
            fi_idx = build_sh_text.find("fi", gate_idx)
            branch_end = else_idx if 0 <= else_idx < fi_idx else fi_idx
            if not (gate_idx < call_idx < branch_end):
                errors.append(
                    "build_from_repo.sh: patch_android_bars.py call must sit "
                    "inside the YILU_ANDROID_BARS=on branch (between '%s' and "
                    "its else/fi)" % ANDROID_GATE)
    if "skipping (default off" not in build_sh_text:
        errors.append('build_from_repo.sh: STEP C4 skip branch must print '
                      '"skipping (default off"')

    # e) patch_ios_scene.py --bars argparse default == hide
    if not RE_IOS_ARGPARSE.search(ios_py_text):
        errors.append('patch_ios_scene.py: --bars argparse must be '
                      'choices=[hide,paper,off] with default="hide" (B3)')

    if errors:
        return False, "\n    ".join(errors)
    return True, ("YILU_IOS_BARS default hide (hide|paper|off); "
                  "YILU_ANDROID_BARS default off (on|off); "
                  "STEP D2 passes ${YILU_IOS_BARS:-hide}; "
                  "STEP C4 skipped on the default path (patch only in the "
                  "on branch); patch_ios_scene.py --bars default=hide")


def selftest():
    with open(BUILD_SH, encoding="utf-8") as f:
        good_build = f.read()
    with open(IOS_PY, encoding="utf-8") as f:
        good_ios = f.read()

    # 当前仓库文件必须通过
    ok, msg = check_defaults(good_build, good_ios)
    assert ok, "selftest: current files must pass, got: %s" % msg

    def expect_fail(build_text, ios_text, needle, tag):
        ok, msg = check_defaults(build_text, ios_text)
        assert not ok and needle in msg, \
            "selftest: %s must be detected (needle %r): %s" % (tag, needle, msg)

    # ① iOS 默认改回 paper → 检出
    bad = good_build.replace("${YILU_IOS_BARS:-hide}", "${YILU_IOS_BARS:-paper}")
    assert bad != good_build
    expect_fail(bad, good_ios, "YILU_IOS_BARS default is 'paper'", "ios default paper")

    # ② Android 默认改回 on → 检出
    bad = good_build.replace("${YILU_ANDROID_BARS:-off}",
                             "${YILU_ANDROID_BARS:-on}")
    assert bad != good_build
    expect_fail(bad, good_ios, "YILU_ANDROID_BARS default is 'on'",
                "android default on")

    # ③ STEP D2 传回 paper → 检出
    bad = good_build.replace(IOS_D2_ARG, '--bars "${YILU_IOS_BARS:-paper}"')
    assert bad != good_build
    expect_fail(bad, good_ios, "STEP D2", "D2 passes paper")

    # ④ C4 门反转（= "off" ] 才执行）→ 检出（门缺失）
    bad = good_build.replace(ANDROID_GATE,
                             'if [ "${YILU_ANDROID_BARS:-off}" = "off" ]; then')
    assert bad != good_build
    expect_fail(bad, good_ios, "STEP C4 gate", "C4 gate inverted")

    # ⑤ patch 调用移出 on 分支（复制一份调用插在 C4 门之前）→ 检出
    gate_i = good_build.find(ANDROID_GATE)
    stray_call = ('  if ! "$PY" "$SCRIPT_DIR/patch_android_bars.py" patch '
                  '"$ACT"; then echo x; fi\n')
    bad = good_build[:gate_i] + stray_call + good_build[gate_i:]
    expect_fail(bad, good_ios, "inside the YILU_ANDROID_BARS=on branch",
                "C4 call outside on branch")

    # ⑥ skipping 日志被删 → 检出
    bad = good_build.replace("skipping (default off", "skipping now (off")
    assert bad != good_build
    expect_fail(bad, good_ios, "skipping (default off", "skip log removed")

    # ⑦ patch_ios_scene.py argparse 默认改回 paper → 检出
    bad_ios = good_ios.replace('choices=["hide", "paper", "off"], default="hide"',
                               'choices=["hide", "paper", "off"], default="paper"')
    assert bad_ios != good_ios
    expect_fail(good_build, bad_ios, 'default="hide"', "argparse default paper")

    print("selftest OK")


def main():
    ap = argparse.ArgumentParser(
        description="Static check of the build-script bars defaults "
                    "(YILU_IOS_BARS=hide / YILU_ANDROID_BARS=off).")
    ap.add_argument("--selftest", action="store_true",
                    help="run the built-in test suite and exit")
    ap.add_argument("--build-sh", default=BUILD_SH,
                    help="path to build_from_repo.sh")
    ap.add_argument("--ios-py", default=IOS_PY,
                    help="path to patch_ios_scene.py")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        print("check_build_defaults: selftest ALL PASS")
        return

    for path in (args.build_sh, args.ios_py):
        if not os.path.isfile(path):
            sys.exit("check_build_defaults: file not found: %s" % path)
    with open(args.build_sh, encoding="utf-8") as f:
        build_text = f.read()
    with open(args.ios_py, encoding="utf-8") as f:
        ios_text = f.read()
    ok, msg = check_defaults(build_text, ios_text)
    print("%s build_defaults: %s" % ("PASS" if ok else "FAIL", msg))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
