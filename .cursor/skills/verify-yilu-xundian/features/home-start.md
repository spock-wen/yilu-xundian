# Home start

Home is the cold-start screen. The primary CTA `开始传书` enters play (chapter or first open road, depending on build). Secondary chrome includes `驿程` / chapter entry and the 关防 seal look.

## Sub-features

- `home-cold` shows title `驿路巡点` and CTA `开始传书` after launch.
- `home-start-tap` activates `开始传书` and leaves Home for the next flow screen.
- `home-evidence` captures fullscreen proof with title or CTA readable.

## How to get to it (user POV)

- Force-stop then launch the app (cold Home).
- From deeper screens, navigate back until Home if the build exposes back; otherwise relaunch.

## Driving it with control_yilu

Preconditions:

- `control_yilu.py doctor` passed.
- Ability stopped or on Home.

- **Cold launch.** Run `python3 tools/verify/control_yilu.py launch`. Home shows `驿路巡点` and `开始传书` (confirm via dumpLayout or screenshot).
- **Tap start.** Run `python3 tools/verify/control_yilu.py drive home-start`. Layout no longer centers only on Home CTA; chapter list or 驿程 / board flow appears.
- **Evidence.** Run `python3 tools/verify/control_yilu.py evidence --label home-start`. PNG under `artifacts/verify/<run-id>/` shows the post-tap screen fullscreen.

## Gotchas

- A warm process may resume mid-board. Prefer `cleanup` then `launch` for Home proofs.
- Coordinate fallbacks assume ~1080-wide phone emulator. Re-dump layout if the tap misses.
- Rules tests passing do not prove Home rendered.
