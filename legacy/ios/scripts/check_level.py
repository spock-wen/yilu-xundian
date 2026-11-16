#!/usr/bin/env python3
"""Compatibility entry. The check lives with the shared engine."""

import runpy
from pathlib import Path

runpy.run_path(
    str(Path(__file__).resolve().parents[3] / "engine/scripts/check_level.py"),
    run_name="__main__",
)
