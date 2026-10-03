package ohos_app_cangjie_entry

import std.collection.ArrayList

/*
 * Caption text width estimation and up-to-three-line wrapping for board chromeLine.
 *
 * Rationale:
 * There is no text-measure API in CJMP / Keels 0.2.2, so text width is estimated
 * from YiluSans-Regular font advances at 12vp (derived via fontTools and verified
 * to cover every character of every chapter's chromeLine).
 *
 * Font advance table at 12vp:
 *   Character   | Unicode | Advance (vp) | Rationale / Source
 *   ------------|---------|--------------|---------------------------------------------
 *   ' ' (space) | U+0020  | 2.69         | ASCII exception (space in " · " and "vs")
 *   'v'         | U+0076  | 6.25         | ASCII exception (ch8 "vs")
 *   's'         | U+0073  | 5.62         | ASCII exception (ch8 "vs")
 *   '/'         | U+002F  | 4.70         | ASCII exception (ch9 "街亭/空仓")
 *   '·'         | U+00B7  | 12.0         | Middle dot separator
 *   '…'         | U+2026  | 12.0         | Ellipsis
 *   (all other) | -       | 12.0         | CJK glyphs & full-width punctuation
 *                                        | ('：', '；', '，', '（', '）', '、', '→', '×')
 *
 * Truncation ruling:
 * - When a line is wider than availW, keep the longest prefix made of COMPLETE
 *   UNITS such that width(prefix) + 12.0 (ellipsis) <= availW, then append "…" (U+2026).
 * - Units: every single character is a unit EXCEPT a bracket group: an opening
 *   bracket '（' (U+FF08) or '(' through its matching closing '）' (U+FF09) or ')'
 *   (inclusive) is ONE unit that is either fully kept or fully dropped. If an opening
 *   bracket has no closing bracket after it, treat that opening bracket as a unit
 *   that must never be the last kept thing (it gets dropped together with everything
 *   after it).
 * - After choosing the prefix, back off (drop) trailing characters while the last
 *   kept character is any of: ' ', '·', '：' (U+FF1A), '；' (U+FF1B), '，' (U+FF0C),
 *   '、' (U+3001), ':', ';', ',', or an unmatched opening bracket '（', '('.
 *   Repeat until the last kept char is none of those (or prefix is empty), then append "…".
 *
 * Wrap ruling (design §3.2, CAPTION_AND_SLIDE_RULINGS_20261003):
 * - Whole caption fits availW -> single line.
 * - Otherwise split at the first " · " into two lines; if line 2 still exceeds
 *   availW (would need a third line), split the whole caption into " · "-separated
 *   segments: line 1 = segment 1, line 2 = segment 2, line 3 = all remaining
 *   segments re-joined with " · " (max 3 lines, each truncated on its own).
 *   With only 2 segments, stay at 2 lines (each truncated, as before).
 */

func runeAdvance(r: Rune): Float64 {
    if (r == r' ') {
        return 2.69
    } else if (r == r'v') {
        return 6.25
    } else if (r == r's') {
        return 5.62
    } else if (r == r'/') {
        return 4.70
    }
    return 12.0
}

func runesWidth(runes: Array<Rune>): Float64 {
    var total: Float64 = 0.0
    for (r in runes) {
        total += runeAdvance(r)
    }
    return total
}

func subRunes(runes: Array<Rune>, start: Int64, end: Int64): Array<Rune> {
    let list = ArrayList<Rune>()
    var i: Int64 = start
    while (i < end) {
        list.add(runes[i])
        i += 1
    }
    return list.toArray()
}

func findClosingBracket(runes: Array<Rune>, start: Int64): Int64 {
    var depth: Int64 = 0
    var j: Int64 = start
    while (j < runes.size) {
        let r = runes[j]
        if (r == r'（' || r == r'(') {
            depth += 1
        } else if (r == r'）' || r == r')') {
            depth -= 1
            if (depth == 0) {
                return j
            }
        }
        j += 1
    }
    return -1
}

func isBackoffRune(r: Rune): Bool {
    if (r == r' ' || r == r'·' || r == r'：' || r == r'；' || r == r'，' || r == r'、') {
        return true
    }
    if (r == r':' || r == r';' || r == r',' || r == r'（' || r == r'(') {
        return true
    }
    return false
}

func truncateRunes(runes: Array<Rune>, availW: Float64): Array<Rune> {
    if (runesWidth(runes) <= availW) {
        return runes
    }
    let ellipsisW: Float64 = 12.0

    // Find the longest prefix made of complete units whose width + ellipsisW <= availW.
    // A unit is either a matching bracket group (inclusive) or a single character.
    var currentW: Float64 = 0.0
    var keptEnd: Int64 = 0
    var idx: Int64 = 0
    while (idx < runes.size) {
        let uStart: Int64 = idx
        var uEnd: Int64 = idx + 1
        let r = runes[idx]
        if (r == r'（' || r == r'(') {
            let matchIdx = findClosingBracket(runes, idx)
            if (matchIdx >= 0) {
                uEnd = matchIdx + 1
            }
        }

        // Calculate width of this unit
        var unitW: Float64 = 0.0
        var u: Int64 = uStart
        while (u < uEnd) {
            unitW += runeAdvance(runes[u])
            u += 1
        }

        if (currentW + unitW + ellipsisW > availW + 1e-9) {
            break
        }
        currentW += unitW
        keptEnd = uEnd
        idx = uEnd
    }

    // Back off trailing characters
    var k: Int64 = keptEnd
    while (k > 0) {
        let r = runes[k - 1]
        if (isBackoffRune(r)) {
            k -= 1
        } else {
            break
        }
    }

    // Build prefix + '…'
    let result = ArrayList<Rune>()
    var i: Int64 = 0
    while (i < k) {
        result.add(runes[i])
        i += 1
    }
    result.add(r'…')
    return result.toArray()
}

public func captionTextWidth(s: String): Float64 {
    var total: Float64 = 0.0
    for (r in s.toRuneArray()) {
        total += runeAdvance(r)
    }
    return total
}

// Split runes into segments separated by " · " (space, middle dot U+00B7, space).
// The separator itself is not part of any segment; empty segments are kept.
func splitSegments(runes: Array<Rune>): ArrayList<Array<Rune>> {
    let segments = ArrayList<Array<Rune>>()
    var start: Int64 = 0
    var i: Int64 = 0
    while (i + 2 < runes.size) {
        if (runes[i] == r' ' && runes[i + 1] == r'·' && runes[i + 2] == r' ') {
            segments.add(subRunes(runes, start, i))
            start = i + 3
            i = start
        } else {
            i += 1
        }
    }
    segments.add(subRunes(runes, start, runes.size))
    return segments
}

public func captionWrap(line: String, availW: Float64): String {
    let runes = line.toRuneArray()
    if (runesWidth(runes) <= availW) {
        return line
    }

    // Find the first " · " separator (space, middle dot U+00B7, space)
    var splitIdx: Int64 = -1
    var i: Int64 = 0
    while (i + 2 < runes.size) {
        if (runes[i] == r' ' && runes[i + 1] == r'·' && runes[i + 2] == r' ') {
            splitIdx = i
            break
        }
        i += 1
    }

    if (splitIdx < 0) {
        let truncated = truncateRunes(runes, availW)
        return String(truncated)
    }

    let line1Runes = subRunes(runes, 0, splitIdx)
    let line2Runes = subRunes(runes, splitIdx + 3, runes.size)

    if (runesWidth(line2Runes) > availW) {
        // Three-line ruling (design §3.2): line 2 would overflow, so re-wrap
        // the whole caption by " · " segments: 1st segment, 2nd segment, then
        // all remaining segments re-joined with " · " on the third line.
        let segments = splitSegments(runes)
        if (segments.size >= 3) {
            let line3Runes = ArrayList<Rune>()
            var s: Int64 = 2
            while (s < segments.size) {
                if (s > 2) {
                    line3Runes.add(r' ')
                    line3Runes.add(r'·')
                    line3Runes.add(r' ')
                }
                for (r in segments[s]) {
                    line3Runes.add(r)
                }
                s += 1
            }
            let l1 = String(truncateRunes(segments[0], availW))
            let l2 = String(truncateRunes(segments[1], availW))
            let l3 = String(truncateRunes(line3Runes.toArray(), availW))
            return l1 + "\n" + l2 + "\n" + l3
        }
        // Only 2 segments: fall through to the two-line path below.
    }

    let line1Final = truncateRunes(line1Runes, availW)
    let line2Final = truncateRunes(line2Runes, availW)

    let line1 = String(line1Final)
    let line2 = String(line2Final)

    return line1 + "\n" + line2
}
