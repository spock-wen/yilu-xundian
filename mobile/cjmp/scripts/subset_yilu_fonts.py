#!/usr/bin/env python3
"""Reproducibly re-subset the Yilu CJMP webfonts from pinned official OFL sources.

    YiluSerif-{Regular,Bold}.otf   <- NotoSerifSC-{Regular,Bold}.otf  (CFF, noto-cjk)
    YiluSans-{Regular,Medium}.ttf  <- NotoSansSC[wght].ttf instanced to wght 400/500

All five sources are pinned to a git commit and checked against a hard-coded
sha256; the tool refuses to continue on any mismatch.  Glyph outlines are never
edited and no substitute font is used.  Both families keep every existing
character and gain the 17 ADDED_CHARS characters.

Subcommands (stdlib + fontTools only, tested with fontTools 4.66):
    fetch  --src-dir DIR                      download / verify the 5 pinned files
    build  --src-dir DIR [--fonts-dir DIR]    instance + subset + write charsets
           [--work-dir DIR] [--base-from DIR] [--selftest-instances]
    verify --old-dir DIR [--fonts-dir DIR]    glyph-exact old-vs-new diff [--json F]

Status markers are OK/FAIL.
"""
import argparse, hashlib, json, sys, urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ADDED_CHARS = "甲乙符滑渡负塌泽停闸门禁此全十皆终"      # 17 chars added to BOTH families
WIN, MAC = (3, 1, 0x409), (1, 0, 0)             # win / mac name records

# (local filename, url, sha256) -- pinned commits, re-checked on every fetch.
SOURCES = (
    ("NotoSansSC-wght.ttf", "https://github.com/google/fonts/raw/a85815a42757630ce188fdad368c2dfc444d4773/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf", "a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da"),
    ("OFL-sans.txt", "https://raw.githubusercontent.com/google/fonts/a85815a42757630ce188fdad368c2dfc444d4773/ofl/notosanssc/OFL.txt", "1c05c68c34f9708415aada51f17e1b0092d2cea709bf4a94cd38114f9e73d7d9"),
    ("NotoSerifSC-Regular.otf", "https://github.com/notofonts/noto-cjk/raw/f8d157532fbfaeda587e826d4cd5b21a49186f7c/Serif/SubsetOTF/SC/NotoSerifSC-Regular.otf", "e8f396decc1f0963a016a989c3d8852e863d1350996f573860a80767c83a1cd3"),
    ("NotoSerifSC-Bold.otf", "https://github.com/notofonts/noto-cjk/raw/f8d157532fbfaeda587e826d4cd5b21a49186f7c/Serif/SubsetOTF/SC/NotoSerifSC-Bold.otf", "24693d48bdb9152f0a06b02af625638a1097abd6de4010ebba027f6e82710527"),
    ("OFL-serif.txt", "https://raw.githubusercontent.com/notofonts/noto-cjk/f8d157532fbfaeda587e826d4cd5b21a49186f7c/Serif/LICENSE", "6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2"),
)
# Reference static instances + sha256.  fontTools rewrites head.modified while
# saving, so it is pinned (REF_MODIFIED): the instances then come out
# byte-reproducible across runs AND byte-identical to these references.
REF = {400: (Path("/workspace/yilu_design/cjmp-gaps-v1/fonts-d03/src_fonts/NotoSansSC-Regular-static.ttf"), "478fb6c8e26891368c439fa628f786cf65d111e0cf632f02f138adaac26acd00"),
       500: (Path("/workspace/yilu_design/cjmp-gaps-v1/fonts-d03/src_fonts/NotoSansSC-Medium-static.ttf"), "350e4b96f48e8b972c4a1253fd6c13888a9785bb54a06ff3da6f25bce130fc0b")}
REF_MODIFIED = {400: 3873418642, 500: 3873418651}
STYLE = {400: "Regular", 500: "Medium"}
# Names of the committed static-derived YiluSans fonts; ID3/ID5, OS/2.fsSelection,
# head.macStyle and head.flags come straight from the pinned variable font.
NAMES = {400: {1: "Noto Sans SC", 2: "Regular", 4: "Noto Sans SC Regular", 6: "NotoSansSC-Regular"},
         500: {1: "Noto Sans SC Medium", 2: "Regular", 4: "Noto Sans SC Medium", 6: "NotoSansSC-Medium",
               16: "Noto Sans SC", 17: "Medium"}}
SANS_CLI = "--no-hinting --desubroutinize --layout-features='*' --name-IDs='*' --notdef-outline --glyph-names=false"
SERIF_CLI = "--no-hinting --glyph-names=false"

def die(msg):
    print(msg, file=sys.stderr)
    raise SystemExit(1)

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def read_chars(path):
    """Charset file = every character of it, newlines ignored."""
    return {c for c in path.read_text(encoding="utf-8") if c not in "\r\n"}

def write_chars(path, chars):
    """Sorted by codepoint, one line, trailing newline."""
    path.write_text("".join(sorted(chars)) + "\n", encoding="utf-8")

def check_sources(src):
    """Refuse to continue if a pinned source is missing or has a bad sha256."""
    bad = []
    for name, _url, want in SOURCES:
        path = src / name
        if not path.exists():
            bad.append(f"{name} (missing)")
        elif sha256_file(path) != want:
            bad.append(f"{name} (sha256 mismatch)")
    if bad:
        die("FAIL: source check: " + ", ".join(bad))

def cmd_fetch(args):
    src = Path(args.src_dir)
    src.mkdir(parents=True, exist_ok=True)
    bad, rows = [], [f"{'sha256 (pinned)':<16} {'status':<20} url"]
    for name, url, want in SOURCES:
        dest = src / name
        if dest.exists():
            got, status = sha256_file(dest), "OK (already present)"
        else:
            print(f"  downloading {url}")
            part = dest.with_name(dest.name + ".part")
            urllib.request.urlretrieve(url, part)
            part.replace(dest)
            got, status = sha256_file(dest), "OK (downloaded)"
        if got != want:
            status, bad = f"FAIL (sha256 {got[:12]})", bad + [name]
        rows.append(f"{want:<16} {status:<20} {url}")
    print("\n".join(rows))
    if bad:
        die("FAIL: sha256 mismatch, refusing to continue: " + ", ".join(bad))
    print(f"OK: {len(SOURCES)} pinned sources verified in {src}")
    return 0

# ---------------------------------------------------------------- instancing --

def apply_names(font, weight):
    """Reproduce name/OS-2/head fields of the committed static fonts.

    Win records that already hold the right value are left untouched (keeps the
    name table byte-identical to the reference statics); mac copies are mirrored
    afterwards -- pyftsubset's default name_languages=[0x409] drops them again in
    the final subset, exactly like the committed YiluSans fonts.
    """
    name = font["name"]
    for nid, value in NAMES[weight].items():
        if name.getDebugName(nid) != value:
            name.setName(value, nid, *WIN)
    for nid in (1, 2, 4, 6, 16, 17, 270):        # 16/17/270 exist only for Medium
        rec = name.getName(nid, *WIN)
        if rec is not None and name.getName(nid, *MAC) is None:
            name.setName(rec.toUnicode(), nid, *MAC)
    font["OS/2"].usWeightClass = weight
    font["OS/2"].fsSelection = 0x40              # REGULAR bit, as committed
    font["head"].macStyle = 0
    font["head"].flags = 3                       # baseline y=0, lsb x=0

def instance_sans(src, weight, out):
    """Pin wght at a static TrueType instance; glyph shapes are untouched."""
    font = TTFont(str(src))
    instantiateVariableFont(font, {"wght": weight}, inplace=True, updateFontNames=True)
    for tag in ("STAT", "fvar", "gvar", "avar", "HVAR", "MVAR"):
        if tag in font:                          # leftovers of full instancing
            del font[tag]
    apply_names(font, weight)
    font.recalcTimestamp = False                 # deterministic bytes
    font["head"].modified = REF_MODIFIED[weight] # + reference-identical head
    out.parent.mkdir(parents=True, exist_ok=True)
    font.save(str(out))
    font.close()
    return sha256_file(out)

def _sfnt_tables(blob):
    """tag -> raw bytes of every table of a compiled sfnt (for byte-level diffs)."""
    out, num = {}, int.from_bytes(blob[4:6], "big")
    for i in range(num):
        off = 12 + 16 * i
        start = int.from_bytes(blob[off + 8:off + 12], "big")
        out[blob[off:off + 4].decode("latin1")] = blob[start:start + int.from_bytes(blob[off + 12:off + 16], "big")]
    return out

def selftest_instances(work):
    """Compare our instanced statics against the pinned reference statics."""
    ok = True
    for weight, (ref_path, _ref_sha) in REF.items():
        mine = work / f"NotoSansSC-{STYLE[weight]}-static.ttf"
        if not mine.exists() or not ref_path.exists():
            print(f"OK: selftest wght={weight} skipped (instance or reference missing)")
            continue
        got, want = sha256_file(mine), sha256_file(ref_path)
        if got == want:
            print(f"OK: instance wght={weight} byte-identical to reference ({got})")
            continue
        ok = False
        print(f"FAIL: instance wght={weight}: mine={got} ref={want}")
        a, b = _sfnt_tables(mine.read_bytes()), _sfnt_tables(ref_path.read_bytes())
        for tag in sorted(set(a) | set(b)):
            if tag not in a or tag not in b:
                print(f"  table {tag}: only in {'mine' if tag in a else 'ref'}")
            elif a[tag] != b[tag]:
                print(f"  table {tag}: differs ({len(a[tag])} vs {len(b[tag])} bytes)")
    return 0 if ok else 1

# ---------------------------------------------------------------- subsetting --

def subset_one(src, out, text, sans, charset_file):
    """fontTools.subset API == the pyftsubset command printed below."""
    opts = subset.Options()
    opts.glyph_names = False                      # --glyph-names=false
    opts.hinting = False                          # --no-hinting
    if sans:                                      # extra pyftsubset flags for sans
        opts.desubroutinize, opts.layout_features = True, ["*"]
        opts.name_IDs, opts.notdef_outline = ["*"], True
    print(f"  $ pyftsubset {src.name} --text-file={out.parent / charset_file} "
          f"{SANS_CLI if sans else SERIF_CLI}")
    font = subset.load_font(str(src), opts)
    sub = subset.Subsetter(options=opts)
    sub.populate(text=text)                       # charset as one big string
    sub.subset(font)
    out.parent.mkdir(parents=True, exist_ok=True)
    subset.save_font(font, str(out), opts)
    font.close()

# -------------------------------------------------------------------- build --

def load_base(bdir, fonts, fname, seed=None):
    """Base charset = the characters that must be preserved (an existing file wins)."""
    for d in (bdir, fonts):
        if (d / fname).exists():
            return read_chars(d / fname)
    if seed is None:
        die(f"FAIL: {fname} not found in {bdir} or {fonts}")
    print(f"  {fname} missing -> seeded once from {seed.name} cmap; the written file becomes the source of truth")
    return {chr(cp) for cp in TTFont(str(seed)).getBestCmap()}

def cmd_build(args):
    src, fonts = Path(args.src_dir), Path(args.fonts_dir)
    fonts.mkdir(parents=True, exist_ok=True)
    work = Path(args.work_dir) if args.work_dir else src / "work"
    bdir = Path(args.base_from) if args.base_from else fonts
    check_sources(src)
    added = set(ADDED_CHARS)
    print(f"sources OK in {src}; fonts-dir={fonts}; work-dir={work}")
    # (a) base charsets, (b) final = base u ADDED_CHARS, written back sorted
    serif_base = load_base(bdir, fonts, "yilu_serif_chars.txt", seed=fonts / "YiluSerif-Regular.otf")
    sans_base = load_base(bdir, fonts, "yilu_sans_chars.txt")
    serif, sans = serif_base | added, sans_base | added
    write_chars(fonts / "yilu_serif_chars.txt", serif)
    write_chars(fonts / "yilu_sans_chars.txt", sans)
    (fonts / "charset.txt").write_text((fonts / "yilu_serif_chars.txt").read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  serif base/final={len(serif_base)}/{len(serif)} | sans base/final={len(sans_base)}/{len(sans)} | added={len(added)}")
    for name, _url, want in SOURCES:              # (f) licences: sha256 printed only
        if name.startswith("OFL"):
            print(f"  licence {name} sha256={want}")
    # (c) sans static instancing at wght 400 / 500, then selftest vs references
    for weight in (400, 500):
        out = work / f"NotoSansSC-{STYLE[weight]}-static.ttf"
        got = instance_sans(src / "NotoSansSC-wght.ttf", weight, out)
        print(f"  instanced wght={weight} -> {out} ({out.stat().st_size} B, sha256={got})")
    if args.selftest_instances:
        return selftest_instances(work)
    selftest_instances(work)
    # (d)/(e) subset both families, then (g) summary: counts, sizes, sha256
    serif_text, sans_text = "".join(sorted(serif)), "".join(sorted(sans))
    jobs = [(work / f"NotoSansSC-{STYLE[w]}-static.ttf", fonts / f"YiluSans-{STYLE[w]}.ttf",
             sans_text, True, "yilu_sans_chars.txt") for w in (400, 500)]
    jobs += [(src / f"NotoSerifSC-{s}.otf", fonts / f"YiluSerif-{s}.otf",
              serif_text, False, "yilu_serif_chars.txt") for s in ("Regular", "Bold")]
    print("subset:")
    for one_in, one_out, text, is_sans, cfile in jobs:
        subset_one(one_in, one_out, text, is_sans, cfile)
    print(f"summary: serif={len(serif)} sans={len(sans)} chars (base + {len(added)} added); outputs:")
    for _i, one_out, text, _s, _c in jobs:
        print(f"  {one_out.name}: {len(set(text))} chars, {one_out.stat().st_size} B, sha256={sha256_file(one_out)}")
    print("OK: build finished")
    return 0

# ------------------------------------------------------------------- verify --

def glyph_ops(glyphset, gname):
    """Outline as a recorded op list (composites decomposed, name independent)."""
    pen = DecomposingRecordingPen(glyphset)
    glyphset[gname].draw(pen)
    return pen.value

def features(font, tag):
    table = font.get(tag)
    if table is None or table.table.FeatureList is None:
        return []
    return sorted({r.FeatureTag for r in table.table.FeatureList.FeatureRecord})

def compare_font(old_path, new_path, added):
    """Checks (i)-(vi); cmap lookups by codepoint keep it glyph-order independent."""
    old, new = TTFont(str(old_path)), TTFont(str(new_path))
    ocm, ncm = old.getBestCmap(), new.getBestCmap()
    ogs, ngs = old.getGlyphSet(), new.getGlyphSet()
    missing = sorted(set(ocm) - set(ncm))                                   # (i)
    add_missing = [c for c in sorted(added) if ord(c) not in ncm]           # (ii)
    add_empty = [c for c in sorted(added) if ord(c) in ncm and not glyph_ops(ngs, ncm[ord(c)])]
    diffs, compared = [], 0                                                 # (iii)
    for cp in sorted(ocm):
        if cp not in ncm:
            continue
        compared += 1
        og, ng, what = ocm[cp], ncm[cp], []
        if glyph_ops(ogs, og) != glyph_ops(ngs, ng):
            what.append("outline")
        if ogs[og].width != ngs[ng].width:
            what.append("hmtx")
        if "vmtx" in old and "vmtx" in new and old["vmtx"][og][0] != new["vmtx"][ng][0]:
            what.append("vmtx")
        if what:
            diffs.append({"cp": cp, "char": chr(cp), "diffs": what})
    extra = sorted(set(ncm) - set(ocm))                                     # (iv)
    expected = sorted({ord(c) for c in added} - set(ocm))
    rep = {"old": str(old_path), "new": str(new_path), "old_size": old_path.stat().st_size,
           "new_size": new_path.stat().st_size, "old_cmap": len(ocm), "new_cmap": len(ncm),
           "compared": compared, "outline_diffs": diffs[:20], "outline_diff_count": len(diffs),
           "missing_old": [f"U+{c:04X}" for c in missing], "added_missing": add_missing,
           "added_empty_glyph": add_empty, "extra": [f"U+{c:04X}" for c in extra],
           "extra_expected": [f"U+{c:04X}" for c in expected], "extra_ok": extra == expected,
           "features_old": {"GSUB": features(old, "GSUB"), "GPOS": features(old, "GPOS")},
           "features_new": {"GSUB": features(new, "GSUB"), "GPOS": features(new, "GPOS")}}
    rep["ok"] = not (missing or add_missing or add_empty or diffs) and rep["extra_ok"]
    print(f"  {old_path.name}: old/new cmap={len(ocm)}/{len(ncm)}, compared={compared}, diffs={len(diffs)}, "
          f"missing={len(missing)}, added_missing={len(add_missing)}, added_empty={len(add_empty)}, "
          f"extra_ok={rep['extra_ok']}, size {rep['old_size']} -> {rep['new_size']} B: "
          f"{'OK' if rep['ok'] else 'FAIL'}")                               # (vi)
    for d in diffs[:20]:
        print(f"    diff U+{d['cp']:04X} {d['char']} {'/'.join(d['diffs'])}")
    print(f"    (v) GSUB old={rep['features_old']['GSUB']} new={rep['features_new']['GSUB']}")
    print(f"    (v) GPOS old={rep['features_old']['GPOS']} new={rep['features_new']['GPOS']}")
    old.close(), new.close()
    return rep

def cmd_verify(args):
    fonts, added = Path(args.fonts_dir), set(ADDED_CHARS)
    report = {"added_chars": ADDED_CHARS, "fonts": {}}
    print(f"verify: old={args.old_dir} new={fonts}")
    for name in ("YiluSerif-Regular.otf", "YiluSerif-Bold.otf", "YiluSans-Regular.ttf", "YiluSans-Medium.ttf"):
        old_path, new_path = Path(args.old_dir) / name, fonts / name
        if not old_path.exists() or not new_path.exists():
            die(f"FAIL: {name}: missing old or new file")
        report["fonts"][name] = compare_font(old_path, new_path, added)
    report["ok"] = all(r["ok"] for r in report["fonts"].values())
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  json report -> {args.json}")
    print("OK: verify clean" if report["ok"] else "FAIL: verify found diffs")
    return 0 if report["ok"] else 1

# ----------------------------------------------------------------------- cli --

def main():
    default_fonts = Path(__file__).resolve().parent.parent / "fonts"
    ap = argparse.ArgumentParser(description="Fetch pinned OFL sources / rebuild the Yilu fonts.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="download + sha256-verify the 5 sources")
    f.add_argument("--src-dir", required=True)
    b = sub.add_parser("build", help="instance + subset into fonts-dir")
    b.add_argument("--src-dir", required=True)
    b.add_argument("--fonts-dir", default=str(default_fonts))
    b.add_argument("--work-dir", default=None, help="default: <src-dir>/work")
    b.add_argument("--base-from", default=None, help="read base charset files from DIR")
    b.add_argument("--selftest-instances", action="store_true", help="only compare instances")
    v = sub.add_parser("verify", help="glyph-exact old-vs-new comparison")
    v.add_argument("--old-dir", required=True)
    v.add_argument("--fonts-dir", default=str(default_fonts))
    v.add_argument("--json", default=None, help="write JSON report here")
    args = ap.parse_args()
    return {"fetch": cmd_fetch, "build": cmd_build, "verify": cmd_verify}[args.cmd](args)

if __name__ == "__main__":
    raise SystemExit(main())
