#!/usr/bin/env python3
"""半印勘合 interlude — not a Zip board.

Mirrors entry/src/main/cangjie/game/kanhe.cj.
Designer copy from Notion「桑氏传粮 故事草稿」§失散插章 (2026-08-31):
https://app.notion.com/p/3cd04f19afd1812094dcc28d05d49eae
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from kanhe import (  # noqa: E402
    COPY_JOINED,
    COPY_LEFT,
    COPY_RETURN,
    COPY_RIGHT,
    COPY_SEAL,
    KanheGame,
)


class KanheAlignTests(unittest.TestCase):
    def test_starts_misaligned_sliding(self) -> None:
        game = KanheGame()
        self.assertEqual(game.phase, 0)
        self.assertFalse(game.is_aligned())
        self.assertGreater(abs(game.right_y - game.left_y), game.ALIGN_TOL)
        self.assertEqual(game.miss, 0)

    def test_release_while_apart_is_miss_not_win(self) -> None:
        game = KanheGame()
        game.down(game.left_x + 20.0, game.left_y + 20.0)
        won = game.up()
        self.assertFalse(won)
        self.assertEqual(game.phase, 0)
        self.assertEqual(game.miss, 1)

    def test_align_within_tolerance_snaps_and_seals(self) -> None:
        game = KanheGame()
        game.left_x = 24.0
        game.left_y = 48.0
        game.right_x = 24.0 + KanheGame.HALF_W + 8.0
        game.right_y = 48.0 + 6.0
        self.assertTrue(game.is_aligned())
        game.down(game.right_x + 12.0, game.right_y + 12.0)
        self.assertTrue(game.up())
        self.assertEqual(game.phase, 1)
        self.assertEqual(game.miss, 0)
        self.assertAlmostEqual(game.right_x, game.left_x + KanheGame.HALF_W)
        self.assertAlmostEqual(game.right_y, game.left_y)

    def test_just_outside_tolerance_stays_open(self) -> None:
        game = KanheGame()
        game.left_x = 24.0
        game.left_y = 48.0
        game.right_x = 24.0 + KanheGame.HALF_W + KanheGame.ALIGN_TOL + 1.0
        game.right_y = 48.0
        self.assertFalse(game.is_aligned())
        game.down(game.right_x + 8.0, game.right_y + 8.0)
        self.assertFalse(game.up())
        self.assertEqual(game.phase, 0)
        self.assertEqual(game.miss, 1)

    def test_no_lives_miss_then_align_still_wins(self) -> None:
        game = KanheGame()
        game.down(game.left_x + 16.0, game.left_y + 16.0)
        self.assertFalse(game.up())
        self.assertEqual(game.miss, 1)
        game.left_x = 30.0
        game.left_y = 50.0
        game.right_x = 30.0 + KanheGame.HALF_W
        game.right_y = 50.0
        game.down(game.left_x + 10.0, game.left_y + 10.0)
        self.assertTrue(game.up())
        self.assertEqual(game.phase, 1)
        self.assertEqual(game.miss, 0)

    def test_drag_left_does_not_move_right(self) -> None:
        game = KanheGame()
        rx, ry = game.right_x, game.right_y
        start_x, start_y = game.left_x + 18.0, game.left_y + 22.0
        game.down(start_x, start_y)
        game.move(start_x + 40.0, start_y - 12.0)
        self.assertAlmostEqual(game.left_x, 8.0 + 40.0)
        self.assertAlmostEqual(game.left_y, 36.0 - 12.0)
        self.assertEqual(game.right_x, rx)
        self.assertEqual(game.right_y, ry)

    def test_drag_right_does_not_move_left(self) -> None:
        game = KanheGame()
        lx, ly = game.left_x, game.left_y
        start_x, start_y = game.right_x + 18.0, game.right_y + 22.0
        game.down(start_x, start_y)
        game.move(start_x - 24.0, start_y + 10.0)
        self.assertAlmostEqual(game.right_x, 172.0 - 24.0)
        self.assertAlmostEqual(game.right_y, 96.0 + 10.0)
        self.assertEqual(game.left_x, lx)
        self.assertEqual(game.left_y, ly)

    def test_show_return_after_seal(self) -> None:
        game = KanheGame()
        game.phase = 1
        game.show_return()
        self.assertEqual(game.phase, 2)

    def test_reset_reopens_sliding(self) -> None:
        game = KanheGame()
        game.phase = 2
        game.miss = 1
        game.reset()
        self.assertEqual(game.phase, 0)
        self.assertEqual(game.miss, 0)
        self.assertFalse(game.is_aligned())


class KanheCatalogIsolationTests(unittest.TestCase):
    """Interlude must not become a 14th Zip board."""

    def test_levels_json_stays_thirteen(self) -> None:
        data = json.loads((ROOT / "entry/src/main/resources/rawfile/levels.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data), 13)
        names = [lv["name"] for lv in data]
        self.assertNotIn("失散", names)
        self.assertNotIn("半印勘合", names)
        self.assertNotIn("汝南", names)

    def test_levels_cj_has_no_kanhe_board(self) -> None:
        src = (ROOT / "entry/src/main/cangjie/levels.cj").read_text(encoding="utf-8")
        self.assertNotIn("半印", src)
        self.assertNotIn("失散", src)
        self.assertEqual(src.count("levels.add("), 13)


class KanheUiContractTests(unittest.TestCase):
    def test_yicheng_row_is_not_a_grid_level(self) -> None:
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        catalog = (ROOT / "entry/src/main/cangjie/levels.cj").read_text(encoding="utf-8")
        self.assertIn("失散·半印勘合", ui)
        self.assertIn("openKanhe", ui)
        self.assertNotIn("失散·半印勘合", catalog)
        self.assertIn("KanheGame", ui)
        self.assertNotIn("openLevel(13)", ui)
        self.assertNotIn('LevelDef(13', catalog)

    def test_writer_copy_and_guidui_seal(self) -> None:
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        kanhe = (ROOT / "entry/src/main/cangjie/game/kanhe.cj").read_text(encoding="utf-8")
        blob = ui + kanhe
        self.assertIn(COPY_LEFT, blob)
        self.assertIn(COPY_RIGHT, blob)
        self.assertIn(COPY_JOINED, blob)
        self.assertIn(COPY_SEAL, blob)
        self.assertIn(COPY_RETURN, blob)
        self.assertIn("乌巢仓破。持此半票。", blob)
        self.assertIn("南寻汝南。持此半票。", blob)
        self.assertIn("仓破人散。南寻汝南。", blob)
        self.assertIn("北不可回。南寻汝南。", blob)
        self.assertIn("归队", blob)
        self.assertNotIn("熊猫", blob)
        self.assertNotIn("红包", blob)

    def test_kanhe_touch_uses_event_type_and_up(self) -> None:
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        self.assertIn("func handleKanhe(", ui)
        self.assertIn("event.eventType", ui)
        self.assertIn("TouchType.Up", ui)
        self.assertIn("event.touches[0].x", ui)
        self.assertIn("event.touches[0].y", ui)

    def test_vermillion_only_on_guidui_seal(self) -> None:
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        start = ui.index("func drawKanhe():")
        end = ui.index("func ", start + len("func drawKanhe():"))
        draw = ui[start:end]
        self.assertNotIn("Theme.vermillion", draw)
        self.assertIn("Theme.paperShade", draw)
        self.assertIn("Theme.whitePaper", draw)
        self.assertIn("Theme.ink", draw)
        self.assertIn("归", ui)
        self.assertIn("队", ui)
        seal = ui[ui.index("归") : ui.index("队") + 8]
        # 归队 seal sits in ArkUI, not the sliding canvas.
        self.assertIn("Theme.vermillion", ui[ui.index("func drawKanhe") :])

    def test_win_seal_wenshu_untouched(self) -> None:
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        self.assertIn("文书到", ui)
        self.assertIn("驿道已通", ui)


if __name__ == "__main__":
    unittest.main(verbosity=2)
