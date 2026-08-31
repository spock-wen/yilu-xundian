"""半印勘合 — slide two ticket halves until they meet.

Python mirror of entry/src/main/cangjie/game/kanhe.cj.
Copy from Notion「桑氏传粮 故事草稿」§失散插章 (2026-08-31).
This is not a Zip / patrol board.
"""

from __future__ import annotations

COPY_LEFT = "乌巢仓破。持此半票。"
COPY_RIGHT = "南寻汝南。持此半票。"
COPY_JOINED = "仓破人散。南寻汝南。"
COPY_SEAL = "归队"
COPY_RETURN = "北不可回。南寻汝南。"


class KanheGame:
    HALF_W = 140.0
    HALF_H = 168.0
    ALIGN_TOL = 14.0
    CANVAS_W = 320.0
    CANVAS_H = 280.0
    START_LEFT_X = 8.0
    START_LEFT_Y = 36.0
    START_RIGHT_X = 172.0
    START_RIGHT_Y = 96.0

    def __init__(self) -> None:
        self.left_x = self.START_LEFT_X
        self.left_y = self.START_LEFT_Y
        self.right_x = self.START_RIGHT_X
        self.right_y = self.START_RIGHT_Y
        self.phase = 0
        self.drag = 0
        self.grab_x = 0.0
        self.grab_y = 0.0
        self.miss = 0

    def reset(self) -> None:
        self.left_x = self.START_LEFT_X
        self.left_y = self.START_LEFT_Y
        self.right_x = self.START_RIGHT_X
        self.right_y = self.START_RIGHT_Y
        self.phase = 0
        self.drag = 0
        self.grab_x = 0.0
        self.grab_y = 0.0
        self.miss = 0

    def _contains(self, px: float, py: float, x: float, y: float) -> bool:
        return x <= px <= x + self.HALF_W and y <= py <= y + self.HALF_H

    def _clamp_x(self, v: float) -> float:
        hi = self.CANVAS_W - self.HALF_W
        if v < 0.0:
            return 0.0
        if v > hi:
            return hi
        return v

    def _clamp_y(self, v: float) -> float:
        hi = self.CANVAS_H - self.HALF_H
        if v < 0.0:
            return 0.0
        if v > hi:
            return hi
        return v

    def is_aligned(self) -> bool:
        dx = self.right_x - (self.left_x + self.HALF_W)
        dy = self.right_y - self.left_y
        return abs(dx) <= self.ALIGN_TOL and abs(dy) <= self.ALIGN_TOL

    def _snap(self) -> None:
        joined = self.HALF_W * 2.0
        self.left_x = (self.CANVAS_W - joined) / 2.0
        self.left_y = (self.CANVAS_H - self.HALF_H) / 2.0
        self.right_x = self.left_x + self.HALF_W
        self.right_y = self.left_y

    def down(self, px: float, py: float) -> None:
        if self.phase != 0:
            return
        in_left = self._contains(px, py, self.left_x, self.left_y)
        in_right = self._contains(px, py, self.right_x, self.right_y)
        pick = 0
        if in_left and in_right:
            ldx = px - (self.left_x + self.HALF_W / 2.0)
            ldy = py - (self.left_y + self.HALF_H / 2.0)
            rdx = px - (self.right_x + self.HALF_W / 2.0)
            rdy = py - (self.right_y + self.HALF_H / 2.0)
            if ldx * ldx + ldy * ldy <= rdx * rdx + rdy * rdy:
                pick = 1
            else:
                pick = 2
        elif in_left:
            pick = 1
        elif in_right:
            pick = 2
        self.drag = pick
        if pick == 1:
            self.grab_x = px - self.left_x
            self.grab_y = py - self.left_y
        elif pick == 2:
            self.grab_x = px - self.right_x
            self.grab_y = py - self.right_y

    def move(self, px: float, py: float) -> None:
        if self.drag == 1:
            self.left_x = self._clamp_x(px - self.grab_x)
            self.left_y = self._clamp_y(py - self.grab_y)
        elif self.drag == 2:
            self.right_x = self._clamp_x(px - self.grab_x)
            self.right_y = self._clamp_y(py - self.grab_y)

    def up(self) -> bool:
        if self.drag == 0:
            return False
        self.drag = 0
        if self.is_aligned():
            self._snap()
            self.phase = 1
            self.miss = 0
            return True
        self.miss = 1
        return False

    def cancel(self) -> None:
        self.drag = 0

    def show_return(self) -> None:
        self.phase = 2
