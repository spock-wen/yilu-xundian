#!/usr/bin/env python3
"""check_glyphs.py — gate: every string a sans Text/Button node can show must be
in the cmap of both YiluSans static fonts.

Usage:
  python3 check_glyphs.py <src_root> [--fonts-dir DIR] [--chars FILE]
                          [--json OUT.json] [--strict-family] [--self-test]
"""

import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = (
    HERE if os.path.exists(os.path.join(HERE, "YiluSans-Regular.ttf"))
    else os.path.join(HERE, "..", "fonts")
)
DEFAULT_CHARS = (
    os.path.join(HERE, "yilu_sans_chars.txt")
    if os.path.exists(os.path.join(HERE, "yilu_sans_chars.txt"))
    else os.path.join(FONTS_DIR, "yilu_sans_chars.txt")
)
DIGITS = "0123456789"

STR_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')
NODE_CALL = re.compile(r"\b(Text|Button)\(")
LABEL_CALL_RE = re.compile(r"\b(?:BoardLabel|centerLabel)\s*\(")
MODIFIER = re.compile(r"\.\s*([A-Za-z_]\w*)\s*\(")
THEME_CONST = re.compile(
    r'(?:static\s+)?(?:const|let)\s+([A-Za-z_]\w*)\s*:\s*String\s*=\s*"([^"]*)"')
RETURN_THEME = re.compile(r"\breturn\s+(?:Theme|this|self)\.(\w+)\b")
SERIF_NAMES = ("serif", "serifBold", "stationSerif")
SANS_NAMES = ("sans", "sansMedium")  # PR#30: engine cannot hold 2 weights in 1 family -> YiluSans / YiluSansMedium
TRANSITIONAL = {"〈": "D-03 ruling: 〈 literal -> Path2D icon-back",
                "传书过驿": "D-03 ruling: 传书过驿 -> serif"}


class Unresolvable(Exception):
    pass


def balanced(src, i, open_ch, close_ch):
    """Return (text_including_delimiters, end_index) for the balanced pair at i."""
    if open_ch == '"':
        j = i + 1
        while j < len(src):
            if src[j] == "\\":
                j += 2
                continue
            if src[j] == '"':
                return (src[i:j + 1], j + 1)
            j += 1
        raise Unresolvable(f"unterminated string at offset {i}")
    depth, j = 0, i
    while j < len(src):
        c = src[j]
        if c == '"':
            _s, j = balanced(src, j, '"', '"')
            continue
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return (src[i:j + 1], j + 1)
        j += 1
    raise Unresolvable(f"unbalanced {open_ch} at offset {i}")


def find_ending_brace(src, i):
    depth, j = 0, i
    while j < len(src):
        c = src[j]
        if c == '"':
            _s, j = balanced(src, j, '"', '"')
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    raise Unresolvable("unbalanced braces")


# ---------------------------------------------------------------- corpus data
class Corpus:
    def __init__(self, src_root):
        self.root = os.path.abspath(src_root)
        self.cj_files = []
        self._board_labels = None
        for dirpath, _dirs, files in os.walk(self.root):
            for fn in sorted(files):
                if fn.endswith(".cj"):
                    self.cj_files.append(os.path.join(dirpath, fn))

    def level_data(self):
        """(level names from levels.json, string literals from levels.cj)."""
        names, cj = [], []
        for dirpath, _d, files in os.walk(self.root):
            for fn in sorted(files):
                p = os.path.join(dirpath, fn)
                if fn == "levels.json":
                    with open(p, encoding="utf-8") as f:
                        data = json.load(f)
                    items = data if isinstance(data, list) else data.get("levels", [])
                    names.extend(lv["name"] for lv in items
                                 if isinstance(lv, dict) and "name" in lv)
                elif fn == "levels.cj":
                    with open(p, encoding="utf-8") as f:
                        cj.extend(STR_RE.findall(f.read()))
        return names, cj

    def chapter_strings(self):
        """All string literals inside ChapterDef(...) constructor calls."""
        out = set()
        for p in self.cj_files:
            with open(p, encoding="utf-8") as f:
                src = f.read()
            for m in re.finditer(r"ChapterDef\(", src):
                try:
                    body, _ = balanced(src, m.end() - 1, "(", ")")
                except Unresolvable:
                    continue
                out.update(STR_RE.findall(body))
        return sorted(out)

    def board_label_strings(self):
        """Plain string literals inside BoardLabel(...)/centerLabel(...) calls —
        what a ForEach over Array<BoardLabel> renders via Text(item.text) with
        a sans family (same extraction as check_board_labels.py, which lints
        these literals separately)."""
        if self._board_labels is None:
            out = set()
            for p in self.cj_files:
                with open(p, encoding="utf-8") as f:
                    src = f.read()
                for m in LABEL_CALL_RE.finditer(src):
                    try:
                        body, _ = balanced(src, m.end() - 1, "(", ")")
                    except Unresolvable:
                        continue
                    out.update(lit for lit in STR_RE.findall(body)
                               if "${" not in lit)
            self._board_labels = sorted(out)
        return self._board_labels

    def json_level_literals(self):
        out = []
        for dirpath, _d, files in os.walk(self.root):
            for fn in sorted(files):
                if fn == "json_level.cj":
                    with open(os.path.join(dirpath, fn), encoding="utf-8") as f:
                        out.extend(STR_RE.findall(f.read()))
        return out

    def theme_tables(self):
        """(name->value, name->role) from Theme string constants in theme.cj."""
        values, roles = {}, {}
        for p in self.cj_files:
            if os.path.basename(p) != "theme.cj":
                continue
            with open(p, encoding="utf-8") as f:
                src = f.read()
            for m in THEME_CONST.finditer(src):
                name, val = m.group(1), m.group(2)
                values[name] = val
                roles[name] = ("sans" if name in SANS_NAMES
                               else "serif" if name in SERIF_NAMES
                               else "unknown")
        return values, roles


class Resolver:
    """Resolves an expression to the set of strings it can render."""

    def __init__(self, corpus):
        self.c = corpus
        self._fn_cache = {}
        self._fn_src_cache = {}

    def _rel(self, path):
        try:
            return os.path.relpath(path, self.c.root)
        except ValueError:
            return os.path.basename(path)

    def get_func_return_type(self, src, name):
        m = re.search(r"func\s+" + re.escape(name) + r"\s*\([^)]*\)\s*:\s*([A-Za-z0-9_<>]+)", src)
        return m.group(1) if m else None

    # ---- functions -------------------------------------------------------
    def func_body(self, name, class_name=None):
        key = f"{class_name}.{name}" if class_name else name
        if key not in self._fn_cache:
            for p in self.c.cj_files:
                with open(p, encoding="utf-8") as f:
                    src = f.read()
                if class_name:
                    for cm in re.finditer(r"\bclass\s+" + re.escape(class_name) + r"\b", src):
                        cbrace = src.find("{", cm.end())
                        if cbrace == -1:
                            continue
                        cend = find_ending_brace(src, cbrace)
                        class_src = src[cbrace + 1:cend]
                        for m in re.finditer(r"func\s+" + re.escape(name) + r"\s*\(", class_src):
                            brace = class_src.find("{", m.end())
                            if brace == -1 or brace - m.end() > 300:
                                continue
                            end = find_ending_brace(class_src, brace)
                            self._fn_cache[key] = (p, class_src[brace + 1:end])
                            self._fn_src_cache[key] = src
                            break
                        if key in self._fn_cache:
                            break
                else:
                    for m in re.finditer(r"func\s+" + re.escape(name) + r"\s*\(", src):
                        brace = src.find("{", m.end())
                        if brace == -1 or brace - m.end() > 300:
                            continue
                        end = find_ending_brace(src, brace)
                        self._fn_cache[key] = (p, src[brace + 1:end])
                        self._fn_src_cache[key] = src
                        break
                if key in self._fn_cache:
                    break
            if key not in self._fn_cache:
                if class_name:
                    return self.func_body(name, class_name=None)
                raise Unresolvable(f"function or source {name!r} not found under {self.c.root}")
        return self._fn_cache[key]

    def func_strings(self, name, seen, class_name=None):
        key = f"{class_name}.{name}" if class_name else name
        if key in seen:
            return set()
        seen.add(key)
        path, body = self.func_body(name, class_name=class_name)
        full_src = self._fn_src_cache.get(key, "")
        return self.strings_in_source(body, seen, path, full_src)

    def strings_in_source(self, code, seen, path, full_src=""):
        out = set()
        for m in STR_RE.finditer(code):
            out |= self.expand_literal(m.group(1), seen, path)
        # data roles referenced bare in the body (e.g. .name of a level)
        for m in re.finditer(r"\.(name|currentName)\b", code):
            names, _cj = self.c.level_data()
            out |= set(names)
        for m in re.finditer(r"\.(label|title|subtitle|listSubtitle|boardSubtitle|friendLine|tensionLine|cityLine)\b", code):
            out |= set(self.c.chapter_strings())
        # resolve functions called inside the body, recursively
        for m in re.finditer(r"\b(?:(?:this|self|([A-Z]\w*))\.)?([a-zA-Z_]\w*)\s*\(", code):
            callee_cls = m.group(1)
            fname = m.group(2)
            if fname in ("if", "for", "while", "match", "max", "min", "String",
                         "Int", "get", "add", "print", "absF"):
                continue
            ret = self.get_func_return_type(full_src, fname) if full_src else None
            if ret and ret not in ("String", "Array<String>"):
                continue
            try:
                out |= self.func_strings(fname, seen, class_name=callee_cls)
            except Unresolvable:
                pass
        return out

    def find_foreach_target(self, param):
        for p in self.c.cj_files:
            with open(p, encoding="utf-8") as f:
                src = f.read()
            for _start, _end, p_name, t_expr in find_foreach_scopes(src):
                if p_name == param:
                    return t_expr
        return None

    # ---- expressions -------------------------------------------------------
    def expr_strings(self, expr, seen=None, foreach_target=None):
        seen = seen or set()
        e = expr.strip()
        if e.startswith("(") and e.endswith(")"):
            e = e[1:-1].strip()
        if e == "line" or (foreach_target and e == "line"):
            target = foreach_target or self.find_foreach_target(e) or "this.chapterListFooterLines()"
            return self.expr_strings(target, seen)
        if e.startswith('"'):
            if not e.endswith('"'):
                raise Unresolvable(f"unterminated literal: {e[:80]}")
            inner = e[1:-1]
            if "${" in inner:
                parts = re.split(r"\$\{([^}]*)\}", inner)
                out = {"".join(parts[0::2])}
                for sub in parts[1::2]:
                    out |= self.interpolation(sub, seen)
                return out
            return {inner}
        if e in ("Theme.sans", "Theme.serif"):
            return set()
        # numeric expressions -> digits
        if re.fullmatch(r"[\w\s+\-*/.()]+", e) and re.search(
                r"\b(n|count|\w*count|total|index|opened|locked|cleared|done|rows|cols|len|size|"
                r"num|step|steps|id|\d)\b", e, re.I) and not re.search(
                r"\.(name|label|title|subtitle|line)\b", e, re.I):
            return {DIGITS}

        # Function call expression
        m_call = re.match(r"^((?:(?:this|self|[A-Za-z_]\w*)\.)*([a-zA-Z_]\w*))\s*\(", e)
        if m_call:
            paren_start = m_call.end() - 1
            try:
                args_str, end_idx = balanced(e, paren_start, "(", ")")
                if end_idx == len(e):
                    fname = m_call.group(2)
                    prefix = m_call.group(1)[:-(len(fname) + 1)] if "." in m_call.group(1) else ""
                    cls_name = prefix.split(".")[-1] if prefix and prefix not in ("this", "self") else None
                    if fname == "loadError":
                        s = set(self.c.json_level_literals())
                        try:
                            s |= self.func_strings("loadError", set(seen), class_name=cls_name)
                        except Unresolvable:
                            pass
                        if s:
                            return s
                    s = self.func_strings(fname, seen, class_name=cls_name)
                    if s:
                        return s
                    raise Unresolvable(f"expression resolves to no strings: {e[:80]!r}")
            except Unresolvable:
                raise

        base = e.rstrip("()").strip()
        leaf = base.split(".")[-1].strip()
        if leaf in ("name", "currentName"):
            names, _cj = self.c.level_data()
            return set(names)
        if leaf == "chapterCurrentName":
            names, _cj = self.c.level_data()
            return set(names)
        if leaf in ("label", "title", "subtitle", "listSubtitle", "boardSubtitle",
                    "friendLine", "tensionLine", "cityLine"):
            return set(self.c.chapter_strings())
        if leaf == "text":
            # ForEach itemGenerator { item: BoardLabel, ... Text(item.text) }:
            # the strings are the BoardLabel/centerLabel literals in the corpus
            # (see check_board_labels.py). Empty -> fall through to the usual
            # func lookup, which keeps the old unresolved-expression failure.
            labels = self.c.board_label_strings()
            if labels:
                return set(labels)
        if leaf == "loadError":
            s = set(self.c.json_level_literals())
            try:
                s |= self.func_strings("loadError", set(seen))
            except Unresolvable:
                pass
            if s:
                return s
        try:
            s = self.func_strings(leaf, seen)
        except Unresolvable as exc:
            raise Unresolvable(f"cannot resolve expression {e[:80]!r} ({exc})")
        if s:
            return s
        raise Unresolvable(f"expression resolves to no strings: {e[:80]!r}")

    def interpolation(self, sub, seen):
        e = sub.strip()
        if e == "ch" or ".name" in e:
            names, _cj = self.c.level_data()
            return {DIGITS} | set(names)
        if "curName" in e:
            names, _cj = self.c.level_data()
            return set(names) | {"未开"}
        if "dims" in e:
            return {"", " · 0×0"}
        if re.search(
                r"\b(n|count|\w*count|total|index|opened|locked|cleared|done|rows|cols|len|size|num|step|steps|id|\d)\b",
                e, re.I) and not re.search(r"\.(name|label|title|subtitle|line)\b", e, re.I):
            return {DIGITS}
        try:
            return self.expr_strings(e, seen)
        except Unresolvable:
            if re.fullmatch(r"[a-zA-Z_]\w*", e):
                return {DIGITS}
            raise

    def expand_literal(self, lit, seen, path):
        if "${" in lit:
            parts = re.split(r"\$\{([^}]*)\}", lit)
            out = {"".join(parts[0::2])}
            for sub in parts[1::2]:
                try:
                    out |= self.interpolation(sub, seen)
                except Unresolvable as exc:
                    raise Unresolvable(
                        f"{self._rel(path)}: template ${{{sub}}} in literal "
                        f"{lit[:60]!r}") from exc
            return out
        return {lit}


def find_foreach_scopes(src):
    """Find all ForEach(expr, itemGenerator: { param: Type, idx => ... }) scopes.
    Returns list of (closure_start, closure_end, param_name, target_expr).
    """
    scopes = []
    for m in re.finditer(r"\bForEach\s*\(", src):
        paren_start = m.end() - 1
        try:
            args_src, paren_end = balanced(src, paren_start, "(", ")")
        except Unresolvable:
            continue
        gen_match = re.search(r",\s*itemGenerator\s*:\s*\{\s*([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_]\w*)", args_src)
        if not gen_match:
            continue
        target_expr = args_src[1:gen_match.start()].strip()
        param_name = gen_match.group(1)
        arrow_pos = args_src.find("=>", gen_match.end())
        if arrow_pos == -1:
            continue
        closure_start = paren_start + arrow_pos + 2
        brace_idx = args_src.find("{", gen_match.start())
        try:
            _b_text, b_end = balanced(args_src, brace_idx, "{", "}")
            closure_end = paren_start + b_end
        except Unresolvable:
            closure_end = paren_end
        scopes.append((closure_start, closure_end, param_name, target_expr))
    return scopes


class Node(tuple):
    def __new__(cls, line_no, kind, expr, chain, mods, foreach_target=None, foreach_param=None):
        inst = super().__new__(cls, (line_no, kind, expr, chain, mods))
        inst.foreach_target = foreach_target
        inst.foreach_param = foreach_param
        return inst


# ---------------------------------------------------------------- node scan
def scan_chain(src, argend):
    """The node's OWN modifier chain: the run of leading '.xxx(...)' calls
    starting right after the Text/Button argument. The chain ends exactly at
    the start of the next component call (Text/Button/Image/Row/Column/
    Stack/Scroll/List/ForEach/If/if/else/Blank/Canvas/...), at a closing '}'
    that ends the enclosing block, or at any statement that is not a
    '.modifier(...)' continuation. Returns (chain_text, mods) where mods is
    the list of (name, arg_text) for the node's own TOP-LEVEL modifiers: a
    component call nested inside another modifier's argument belongs to that
    nested node, so its modifiers never enter this chain."""
    i = argend
    mods = []
    while True:
        while i < len(src):
            if src[i] in " \t\r\n":
                i += 1
            elif src[i:i + 2] == "/*":
                e = src.find("*/", i + 2)
                i = e + 2 if e != -1 else len(src)
            elif src[i:i + 2] == "//":
                e = src.find("\n", i)
                i = e + 1 if e != -1 else len(src)
            else:
                break
        if i >= len(src) or src[i] != ".":
            break                      # next component call, '}', statement
        m = MODIFIER.match(src, i)
        if not m:
            break
        try:
            arg, j = scan_args_after_paren(src, m.end())   # m.end() is just after '('
        except Unresolvable:
            break
        if j - argend > 4000:                             # safety cap
            break
        mods.append((m.group(1), arg.strip()))
        i = j
    return src[argend:i], mods


def scan_nodes(path):
    """Yield (line_no, kind, expr, chain_text, mods) per Text/Button call."""
    with open(path, encoding="utf-8") as f:
        src = f.read()
    scopes = find_foreach_scopes(src)
    results = []
    pos = 0
    while True:
        m = NODE_CALL.search(src, pos)
        if not m:
            break
        kind = m.group(1)
        j = m.end()
        while j < len(src) and src[j] in " \t\n":
            j += 1
        try:
            if src[j] == '"':
                arg, endq = balanced(src, j, '"', '"')
                expr = arg                      # keep quotes: marks a literal
                k = endq
                while k < len(src) and src[k] in " \t\r\n":
                    k += 1
                if k < len(src) and src[k] == ")":
                    argend = k + 1
                else:
                    raise Unresolvable("missing ) after string argument")
            else:
                arg, argend = scan_args_after_paren(src, j)   # j is after '('
                expr = arg.strip()
        except Unresolvable:
            pos = m.end()
            continue
        chain, mods = scan_chain(src, argend)
        line_no = src.count("\n", 0, m.start()) + 1

        fe_target = None
        fe_param = None
        for s_start, s_end, p_name, t_expr in scopes:
            if s_start <= m.start() < s_end:
                if expr == p_name:
                    fe_target = t_expr
                    fe_param = p_name
                    break

        results.append(Node(line_no, kind, expr, chain, mods, fe_target, fe_param))
        pos = max(m.end(), argend)
    return results


def scan_args_after_paren(src, j):
    """src[j] is just after an opening '('; return (inside_text, end_after_close).
    Scans with depth already 1."""
    depth, k = 1, j
    while k < len(src):
        c = src[k]
        if c == '"':
            _s, k = balanced(src, k, '"', '"')
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return (src[j:k], k + 1)
        k += 1
    raise Unresolvable("unbalanced paren after call(")


class FamilyTable:
    """Known families per D3: Theme string constants in theme.cj, plus small
    helpers whose body returns one of them."""

    def __init__(self, corpus, resolver):
        self.values, self.roles = corpus.theme_tables()
        self._resolver = resolver
        self._helper_cache = {}

    def classify(self, arg):
        """-> (role, detail) for role in {'sans','serif'}; raises
        Unresolvable for unknown families and literal generic families."""
        a = arg.strip()
        if re.fullmatch(r'"(?:[^"\\]|\\.)*"', a):
            raise Unresolvable(
                f'literal generic family {a[:60]} -> system fallback '
                f'(D-03: use Theme.sans or a registered Yilu family)')
        m = re.fullmatch(r"Theme\.(\w+)", a)
        if m:
            name = m.group(1)
            role = self.roles.get(name)
            if role in ("sans", "serif"):
                return role, f"Theme.{name} = {self.values.get(name)!r}"
            raise Unresolvable(unknown_family_msg(a))
        leaf = a.rstrip("()").split(".")[-1].strip()
        if leaf in self._helper_cache:
            return self._helper_cache[leaf], f"helper {leaf}()"
        try:
            _p, body = self._resolver.func_body(leaf)
        except Unresolvable as exc:
            raise Unresolvable(unknown_family_msg(a, exc))
        for name in RETURN_THEME.findall(body):
            role = self.roles.get(name)
            if role in ("sans", "serif"):
                self._helper_cache[leaf] = role
                return role, f"helper {leaf}() -> Theme.{name}"
        raise Unresolvable(unknown_family_msg(a))


def unknown_family_msg(arg, inner=None):
    brief = " ".join(arg.strip().split())[:80]
    base = (f"unknown family {brief} -> cannot verify; not a known AppTheme "
            f"family or a helper returning one "
            f"(D-03: known = Theme.sans / sansMedium / Theme.serif / serifBold / stationSerif)")
    if inner:
        base += f" ({inner})"
    return base


def run_check(src_root, fonts_dir, chars_file, strict_family=False):
    """Returns process exit code; prints findings."""
    corpus = Corpus(src_root)
    if not corpus.cj_files:
        print(f"FAIL: no .cj files under {src_root}")
        return 1
    resolver = Resolver(corpus)
    fam = FamilyTable(corpus, resolver)
    required = {}                     # char -> sorted [file:line]
    sans_nodes = serif_nodes = no_family = unknown_family = total = 0
    findings = []                     # FAIL lines from the node scan
    trans_nodes = {k: [] for k in TRANSITIONAL}

    def add(msg, kind="FAIL"):
        findings.append(f"{kind} {msg}")

    for p in sorted(corpus.cj_files):
        rel = os.path.relpath(p, corpus.root)
        for node in scan_nodes(p):
            line_no, kind, expr, _chain, mods = node[:5]
            fe_target = getattr(node, "foreach_target", None)
            total += 1
            loc = f"{rel}:{line_no}"
            # D2/D3: only this node's own top-level .fontFamily(...) counts
            arg_txt = None
            for name, m_arg in mods:
                if name == "fontFamily":
                    arg_txt = m_arg
                    break
            if arg_txt is None:
                no_family += 1
                add(f"{loc} {kind} {expr.strip()[:60]} no fontFamily -> "
                    f"system font fallback")
                continue
            try:
                role, _detail = fam.classify(arg_txt)
            except Unresolvable as exc:
                unknown_family += 1
                add(f"{loc} {kind} {expr.strip()[:60]} {exc}")
                continue
            if role == "serif":
                serif_nodes += 1
                continue
            sans_nodes += 1
            raw = expr.strip()
            if raw.strip('"') in TRANSITIONAL:
                trans_nodes[raw.strip('"')].append(loc)
            try:
                strings = resolver.expr_strings(raw, foreach_target=fe_target)
            except Unresolvable as exc:
                add(f"{loc} {kind} ({expr[:120]}) unresolved expression on a "
                    f"sans node: {exc}")
                continue
            for s in strings:
                for ch in s:
                    if ch in "\n\t\r":
                        continue
                    required.setdefault(ch, [])
                    if loc not in required[ch]:
                        required[ch].append(loc)

    # --chars file: SPEC-only strings are also covered
    with open(chars_file, encoding="utf-8") as f:
        for ch in f.read():
            if ch.strip() and ch not in required:
                required[ch] = ["(chars-file)"]

    # glyph coverage over both YiluSans subsets
    from fontTools.ttLib import TTFont
    missing = []
    for fname in ("YiluSans-Regular.ttf", "YiluSans-Medium.ttf"):
        path = os.path.join(fonts_dir, fname)
        if not os.path.exists(path):
            findings.append(f"FAIL missing font file: {path}")
            continue
        cmap = TTFont(path).getBestCmap()
        for ch in required:
            if ch in "\n\t\r":
                continue
            if ord(ch) not in cmap:
                missing.append((ch, fname, list(required[ch])))

    # D5 wiring checks ------------------------------------------------------
    family_warn = False
    warn_lines = []
    sans_vals = sorted({v for k, v in fam.values.items() if k == "sans"})
    if sans_vals and any(v != "YiluSans" for v in sans_vals):
        warn_lines.append(
            f'WARN family-wiring: Theme.sans = "{sans_vals[0]}" (system '
            f"generic). D-03 requires registering YiluSans-Regular/Medium "
            f'and Theme.sans = "YiluSans"; glyph coverage below is checked '
            f"against the YiluSans subsets.")
        family_warn = True
    fonts_cj = [p for p in corpus.cj_files
                if os.path.basename(p) == "fonts.cj"]
    fonts_src = ""
    if fonts_cj:
        with open(fonts_cj[0], encoding="utf-8") as f:
            fonts_src = f.read()
    if "YiluSans" not in fonts_src:
        warn_lines.append(
            "WARN family-wiring: fonts.cj registers no YiluSans font file. "
            "D-03 requires registering YiluSans-Regular/Medium so "
            'Theme.sans = "YiluSans" resolves; glyph coverage below is '
            "checked against the YiluSans subsets.")
        family_warn = True

    # ---- report: FAILs first, then warnings, stats, OK, notes -------------
    for f in findings:
        print(f)
    for ch, fname, locs in missing:
        print(f"FAIL missing {ch!r} U+{ord(ch):04X} in {fname} "
              f"used at {', '.join(locs) if locs else '(only chars-file)'}")
    for w in warn_lines:
        print(w)

    print(f"stats: total={total} sans={sans_nodes} serif={serif_nodes} "
          f"no-family={no_family} unknown-family={unknown_family}")

    exit_code = 0
    if findings or missing:
        exit_code = 1
    elif strict_family and family_warn:
        exit_code = 2

    if not findings and not missing:
        print(f"OK: {sans_nodes} sans nodes, {serif_nodes} serif nodes, "
              f"{len(required)} required chars, "
              f"0 missing in YiluSans-Regular / YiluSans-Medium")
    for s, locs in trans_nodes.items():
        for loc in locs:
            print(f"note: literal {s!r} at {loc} still checked ({TRANSITIONAL[s]})")
    return exit_code


# ------------------------------------------------------------------ self-test
def _write(srcdir, rel, content):
    p = os.path.join(srcdir, rel)
    os.makedirs(os.path.dirname(p) or srcdir, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)


# one generated fixture per adversarial case (base, c1..c7) + 2 extras
SELF_THEME = (
    "public class AppTheme {\n"
    '    public static const serif: String = "YiluSerif"\n'
    '    public static const serifBold: String = "YiluSerifBold"\n'
    '    public static const sans: String = "sans-serif"\n'
    '    public static const stationSerif: String = "YiluSerifBold"\n'
    '    public static const uiFont: String = "system-ui"\n'
    "}\n")
SELF_FONTS = "public func registerYiluFonts(): Int64 {\n    return 0\n}\n"
COVERED = "撤"          # U+64A4, present in the YiluSans subsets
MISSING_GLYPH = "龘"    # U+9F98, absent from the YiluSans subsets


def _mk_fixture(tmp, name):
    sd = os.path.join(tmp, name, "src")
    os.makedirs(sd, exist_ok=True)
    _write(sd, "theme.cj", SELF_THEME)
    _write(sd, "fonts.cj", SELF_FONTS)     # no YiluSans -> family-wiring WARN
    cf = os.path.join(tmp, name, "chars.txt")
    with open(cf, "w", encoding="utf-8") as f:
        f.write(COVERED)
    return sd, cf


def self_test():
    """Run every adversarial case on generated temporary sources and assert
    its expected exit code. One line per case; exit 0 iff all match."""
    tmp = tempfile.mkdtemp(prefix="check_glyphs_selftest_")

    # base: sans node, covered glyph -> 0 (plus the family-wiring WARN)
    sd, cf = _mk_fixture(tmp, "base")
    _write(sd, "page.cj", f'Text("{COVERED}").fontFamily(Theme.sans)\n')

    # c1: missing glyph on a sans node -> 1
    sd, cf = _mk_fixture(tmp, "c1")
    _write(sd, "page.cj",
           f'Text("{COVERED}{MISSING_GLYPH}").fontFamily(Theme.sans)\n')

    # c2: unresolvable expression on a sans node -> 1
    sd, cf = _mk_fixture(tmp, "c2")
    _write(sd, "page.cj",
           "Text(this.mysteryText()).fontFamily(Theme.sans)\n")

    # c3: no fontFamily of its own, right before a sans Text -> 1 (D2; the
    # node must NOT borrow the next node's family)
    sd, cf = _mk_fixture(tmp, "c3")
    _write(sd, "page.cj",
           f'Text("{COVERED}{MISSING_GLYPH}")\n'
           f"    .fontSize(16)\n"
           f'Text("{COVERED}")\n'
           f"    .fontSize(16)\n"
           f"    .fontFamily(Theme.sans)\n")

    # c4: unknown family constant (Theme.uiFont) -> 1 (D3)
    sd, cf = _mk_fixture(tmp, "c4")
    _write(sd, "page.cj",
           f'Text("{COVERED}{MISSING_GLYPH}").fontFamily(Theme.uiFont)\n')

    # c5: literal generic family -> 1 (D4)
    sd, cf = _mk_fixture(tmp, "c5")
    _write(sd, "page.cj",
           f'Text("{COVERED}{MISSING_GLYPH}").fontFamily("sans-serif")\n')

    # c6: levels.json level name carries a missing glyph -> 1
    sd, cf = _mk_fixture(tmp, "c6")
    _write(sd, "page.cj", 'Text("${ch.name}").fontFamily(Theme.sans)\n')
    _write(sd, "levels.json",
           json.dumps([{"name": f"涿郡·{MISSING_GLYPH}"}], ensure_ascii=False))

    # c7: chapter.cj subtitle carries a missing glyph -> 1
    sd, cf = _mk_fixture(tmp, "c7")
    _write(sd, "page.cj",
           "Text(item.subtitle)\n    .fontSize(11)\n"
           "    .fontFamily(Theme.sans)\n")
    _write(sd, "chapter.cj",
           "func chapters(): Unit {\n"
           "    let c = ChapterDef(\n"
           "        0,\n"
           f'        "涿郡{COVERED}",\n'
           f'        "仓官×渠帅 · {MISSING_GLYPH}",\n'
           "        true\n"
           "    )\n"
           "}\n")

    # c10: BoardLabel literal with a covered glyph rendered via ForEach
    # Text(item.text) -> 0
    sd, cf = _mk_fixture(tmp, "c10_ok")
    _write(sd, "page.cj",
           "ForEach(\n"
           "    this.boardNextLabels,\n"
           "    itemGenerator: { item: BoardLabel, idx: Int64 =>\n"
           "        Text(item.text)\n"
           "            .fontSize(item.size)\n"
           "            .fontFamily(Theme.sans)\n"
           "    }\n"
           ")\n")
    _write(sd, "board.cj",
           "func buildBoardNextLabels(): Unit {\n"
           f"    list.add(BoardLabel(1.0, 2.0, 60.0, 12.0, \"驿{COVERED}\", 1, 12.0))\n"
           "}\n")

    # c11: BoardLabel literal carries a missing glyph -> 1
    sd, cf = _mk_fixture(tmp, "c11_missing")
    _write(sd, "page.cj",
           "ForEach(\n"
           "    this.boardNextLabels,\n"
           "    itemGenerator: { item: BoardLabel, idx: Int64 =>\n"
           "        Text(item.text)\n"
           "            .fontSize(item.size)\n"
           "            .fontFamily(Theme.sans)\n"
           "    }\n"
           ")\n")
    _write(sd, "board.cj",
           "func buildBoardNextLabels(): Unit {\n"
           f"    list.add(BoardLabel(1.0, 2.0, 60.0, 12.0, \"驿{MISSING_GLYPH}\", 1, 12.0))\n"
           "}\n")

    # c12: static function call with covered glyph -> 0
    sd, cf = _mk_fixture(tmp, "c12_static_ok")
    _write(sd, "page.cj",
           "Text(ChapterCatalog.groupHeaderRight(0, 0)).fontFamily(Theme.sans)\n")
    _write(sd, "catalog.cj",
           "public class ChapterCatalog {\n"
           "    public static func groupHeaderRight(a: Int64, b: Int64): String {\n"
           f'        return "全通 {COVERED} 1 / 1"\n'
           "    }\n"
           "}\n")

    # c13: static function call with missing glyph -> 1
    sd, cf = _mk_fixture(tmp, "c13_static_missing")
    _write(sd, "page.cj",
           "Text(ChapterCatalog.groupHeaderRight(0, 0)).fontFamily(Theme.sans)\n")
    _write(sd, "catalog.cj",
           "public class ChapterCatalog {\n"
           "    public static func groupHeaderRight(a: Int64, b: Int64): String {\n"
           f'        return "全通 {MISSING_GLYPH} 1 / 1"\n'
           "    }\n"
           "}\n")

    # c14: ForEach closure param traced to array with covered glyph -> 0
    sd, cf = _mk_fixture(tmp, "c14_foreach_ok")
    _write(sd, "page.cj",
           "ForEach(\n"
           "    this.chapterListFooterLines(),\n"
           "    itemGenerator: { line: String, idx: Int64 =>\n"
           "        Text(line)\n"
           "            .fontFamily(Theme.sans)\n"
           "    }\n"
           ")\n")
    _write(sd, "catalog.cj",
           "public class ChapterCatalog {\n"
           "    public static func chapterListFooterLines(): Array<String> {\n"
           f'        return ["已通 {COVERED}"]\n'
           "    }\n"
           "}\n"
           "func chapterListFooterLines(): Array<String> {\n"
           "    return ChapterCatalog.chapterListFooterLines()\n"
           "}\n")

    # c15: ForEach closure param traced to array with missing glyph -> 1
    sd, cf = _mk_fixture(tmp, "c15_foreach_missing")
    _write(sd, "page.cj",
           "ForEach(\n"
           "    this.chapterListFooterLines(),\n"
           "    itemGenerator: { line: String, idx: Int64 =>\n"
           "        Text(line)\n"
           "            .fontFamily(Theme.sans)\n"
           "    }\n"
           ")\n")
    _write(sd, "catalog.cj",
           "public class ChapterCatalog {\n"
           "    public static func chapterListFooterLines(): Array<String> {\n"
           f'        return ["已通 {MISSING_GLYPH}"]\n'
           "    }\n"
           "}\n"
           "func chapterListFooterLines(): Array<String> {\n"
           "    return ChapterCatalog.chapterListFooterLines()\n"
           "}\n")

    # extra: helper returning Theme.serif -> serif node, glyphs not checked -> 0
    sd, cf = _mk_fixture(tmp, "t8_serif")
    _write(sd, "page.cj",
           "func serifFamily(): String {\n"
           "    return Theme.serif\n"
           "}\n"
           f'Text("{MISSING_GLYPH}").fontFamily(this.serifFamily())\n')

    # extra: base under --strict-family -> 2 (family-wiring WARN)
    sd, cf = _mk_fixture(tmp, "t9_strict")
    _write(sd, "page.cj", f'Text("{COVERED}").fontFamily(Theme.sans)\n')

    cases = [
        # (case, expected exit, required message substring, strict_family)
        ("base", 0, "family-wiring", False),
        ("c1", 1, "missing", False),
        ("c2", 1, "unresolved expression", False),
        ("c3", 1, "no fontFamily -> system font fallback", False),
        ("c4", 1, "unknown family", False),
        ("c5", 1, "literal generic family", False),
        ("c6", 1, "missing", False),
        ("c7", 1, "missing", False),
        ("c10_ok", 0, "family-wiring", False),
        ("c11_missing", 1, "missing", False),
        ("c12_static_ok", 0, "family-wiring", False),
        ("c13_static_missing", 1, "missing", False),
        ("c14_foreach_ok", 0, "family-wiring", False),
        ("c15_foreach_missing", 1, "missing", False),
        ("t8_serif", 0, None, False),
        ("t9_strict", 2, "family-wiring", True),
    ]
    import io
    import contextlib
    ok = True
    try:
        for case_name, expected, msg, strict in cases:
            sd = os.path.join(tmp, case_name, "src")
            cf = os.path.join(tmp, case_name, "chars.txt")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = run_check(sd, FONTS_DIR, cf, strict_family=strict)
            out = buf.getvalue()
            good = code == expected
            detail = ""
            if good and msg:
                good = msg in out
                if not good:
                    detail = f" (message {msg!r} absent)"
            if case_name == "c3":
                # must not borrow the next node's fontFamily(Theme.sans)
                if "no fontFamily -> system font fallback" not in out:
                    good = False
                    detail = " (D2 message absent)"
            if case_name in ("c1", "c6", "c7", "c11_missing", "c13_static_missing", "c15_foreach_missing"):
                if MISSING_GLYPH not in out:
                    good = False
                    detail = " (missing glyph not reported)"
            ok = ok and good
            print(f"self-test {case_name}: exit={code} expected={expected} "
                  f"({'OK' if good else 'MISMATCH'}){detail}")
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv):
    args = list(argv)
    if "--self-test" in args:
        return self_test()
    if not args:
        print(__doc__)
        return 1
    src_root = args[0]
    fonts_dir = FONTS_DIR
    chars_file = DEFAULT_CHARS
    strict_family = "--strict-family" in args
    args = [a for a in args if a != "--strict-family"]
    if "--fonts-dir" in args:
        fonts_dir = args[args.index("--fonts-dir") + 1]
    if "--chars" in args:
        chars_file = args[args.index("--chars") + 1]
    if "--json" in args:
        return _run_capture(src_root, fonts_dir, chars_file, strict_family,
                            args[args.index("--json") + 1])
    return run_check(src_root, fonts_dir, chars_file, strict_family)


def _run_capture(src_root, fonts_dir, chars_file, strict_family, json_path):
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = run_check(src_root, fonts_dir, chars_file,
                         strict_family=strict_family)
    out = buf.getvalue()
    print(out, end="")

    def grab(pat):
        m = re.search(pat, out)
        return int(m.group(1)) if m else 0

    data = {
        "src_root": src_root,
        "exit_code": code,
        "total_nodes": grab(r"total=(\d+)"),
        "sans_nodes": grab(r"sans=(\d+)"),
        "serif_nodes": grab(r"serif=(\d+)"),
        "no_family_nodes": grab(r"no-family=(\d+)"),
        "unknown_family_nodes": grab(r"unknown-family=(\d+)"),
        "required_chars": grab(r"(\d+) required chars"),
        "missing": re.findall(r"FAIL missing .+", out),
        "findings": [l for l in out.splitlines() if l.startswith("FAIL ")],
        "family_wiring_warnings": [
            l for l in out.splitlines() if l.startswith("WARN family-wiring")],
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
