# control_yilu

Executable lever for `.cursor/skills/verify-yilu-xundian`.

```bash
python3 tools/verify/control_yilu.py doctor
python3 tools/verify/control_yilu.py proof-home
```

Live evidence lands in `artifacts/verify/<run-id>/` (JPEG + layout + `PROOF.md`) and survives `cleanup`. That tree is gitignored. Review-gate copies belong under `_ship/verify-proof/<run-id>/`.
