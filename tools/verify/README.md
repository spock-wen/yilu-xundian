# control_yilu

Executable lever for `.cursor/skills/verify-yilu-xundian`.

```bash
python3 tools/verify/control_yilu.py doctor
python3 tools/verify/control_yilu.py proof-home
```

Live evidence lands in `artifacts/verify/<run-id>/` (JPEG + layout + `PROOF.md`) and survives `cleanup`. That tree is gitignored. Review-gate copies belong under `_ship/verify-proof/<run-id>/`.

Doctor claims in `.cursor/skills/verify-yilu-xundian/SKILL.md` must match the checks `cmd_doctor` actually runs (hdc on PATH, target listed, bundle installed, `tools/test_rules.py`, printed git SHA). An empty claim set or any claim doctor does not implement fails the contract, including a fixture that says doctor reports the ability process.

```bash
python3 tools/verify/test_skill_doctor_contract.py
python3 -m unittest discover -s tools/verify -p 'test_skill_doctor_contract.py' -t tools/verify
```

`home-start`, `chapter-list`, and `board-zhuo` fail closed when the recipe text is missing. `board-zhuo` taps `章节`, then `涿郡`, then station name `涿郡·涿`. Do not needle `可入` (chapter-list subtitle `开章可入` matches first) or `驿程` (footer `点开章入驿程` matches first); see `_ship/verify-proof/20260916T092315Z/chapter-list.layout.json`. `undo-redraw` does not fail closed: `撤销` / `重绘驿道` pixel fallbacks are the text centers in `home-start.layout.json` (root `[0,0][1320,2856]`, centers (411, 2632) and (1022, 2632)).

`launch` (and so `proof-home`) fails closed with exit 3 when `aa start` reports success but no `com.yilu.xundian` pid appears within `YILU_LAUNCH_PID_TIMEOUT` seconds (default 10). That is a stale mission stuck `INITIAL` on the target; uninstall and reinstall the HAP, then re-run.
