# control_yilu

Executable lever for `.cursor/skills/verify-yilu-xundian`.

```bash
python3 tools/verify/control_yilu.py doctor
python3 tools/verify/control_yilu.py proof-home
```

Live evidence lands in `artifacts/verify/<run-id>/` (JPEG + layout + `PROOF.md`) and survives `cleanup`. That tree is gitignored. Review-gate copies belong under `_ship/verify-proof/<run-id>/`.

`drive` fails closed when the recipe text is missing. `board-zhuo` taps `章节`, then `涿郡`, then station name `涿郡·涿` (not `可入`, not `驿程`). `撤销` / `重绘驿道` pixel fallbacks are the text centers in `_ship/verify-proof/20260916T092315Z/home-start.layout.json` (root `[0,0][1320,2856]`).
