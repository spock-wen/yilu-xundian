# Proof log — verify-yilu-xundian (run 20260916T092315Z)

Harness: `python3 tools/verify/control_yilu.py`
Target: `127.0.0.1:5555` (emulator)
Bundle: `com.yilu.xundian`
Git SHA: `05842db` (branch `feat/verify-yilu-xundian` / PR #21)
Host: Mac DevEco hdc

## Commands run

```bash
python3 tools/verify/control_yilu.py doctor          # PASS (bundle + tools/test_rules.py)
python3 tools/verify/control_yilu.py proof-home      # launch → drive home-start → evidence → cleanup
# same run-id reused:
python3 tools/verify/control_yilu.py launch
python3 tools/verify/control_yilu.py drive chapter-list
python3 tools/verify/control_yilu.py evidence --label chapter-list
python3 tools/verify/control_yilu.py cleanup
```

`chapter-list` **was run in the same session family** (same run-id after home-start).

## Artifacts (tracked under `_ship/verify-proof/`)

| file | what it shows |
| --- | --- |
| `home-start.jpeg` | Fullscreen after tapping `开始传书` (left Home CTA path) |
| `chapter-list.jpeg` | Fullscreen chapter list after tapping `章节` |
| `home-start.layout.json` / `chapter-list.layout.json` | uitest dumpLayout companions |

## Feature coverage this run

- [x] home-start (proof-home)
- [x] chapter-list
- [ ] board-zhuo / undo-redraw / progress-lock / full clear DFS (P1 gaps)

Evidence survives `cleanup` (ability force-stop only).
