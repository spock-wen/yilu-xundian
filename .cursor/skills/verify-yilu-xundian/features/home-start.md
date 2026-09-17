# Home start

Home is the cold-start screen. The primary CTA `开始传书` opens the current patrol board (`startPlay()` → `openLevel(cleared)`; fresh install = `涿郡·涿`). It does not open 章节 or 驿程. Secondary chrome is a bordered `章节` row (chapter list) and a muted `驿程` link (global station list), plus the 关防 seal look.

## Sub-features

- `home-cold` shows title `驿路巡点` and CTA `开始传书` after launch.
- `home-start-tap` activates `开始传书` and opens the current board.
- `home-evidence` captures fullscreen JPEG of that board (title or bottom chrome readable).

## How to get to it (user POV)

- Force-stop then launch the app (cold Home).
- From deeper screens, navigate back until Home if the build exposes back; otherwise relaunch.

## Driving it with control_yilu

Preconditions:

- `control_yilu.py doctor` passed.
- Ability stopped or on Home.

- **Cold launch.** Run `python3 tools/verify/control_yilu.py launch`. Home shows `驿路巡点` and `开始传书` (confirm via dumpLayout or screenshot).
- **Tap start.** Run `python3 tools/verify/control_yilu.py drive home-start`. Home CTA is gone; board chrome is present (`涿郡·涿` on a fresh install, plus `撤销` / `重绘驿道`).
- **Evidence.** Run `python3 tools/verify/control_yilu.py evidence --label home-start`. JPEG under `artifacts/verify/<run-id>/home-start.jpeg` (ship copy: `_ship/verify-proof/<run-id>/`) shows the post-tap board fullscreen.

## Gotchas

- A warm process may resume mid-board. Prefer `cleanup` then `launch` for Home proofs.
- Coordinate fallbacks assume ~1080-wide phone emulator. Re-dump layout if the tap misses.
- Rules tests passing do not prove Home rendered.
