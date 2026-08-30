#!/usr/bin/env python3
"""Geometry spec for mock 甲 bottom-bar icons (24vp hairline arrows).

Numbers here are the source of truth for the Cangjie Path2D draws in index.cj.
Canvas Y grows down. Angles are Canvas radians (0 = east, π/2 = south).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

ICON_VP = 24
CX = 12.0
CY = 12.0
RADIUS = 7.0
HEAD_LEN = 3.6
HEAD_HALF = 2.1
INK_HEX = "#2C2A26"
HAIRLINE = 1.0


@dataclass(frozen=True)
class ArcIcon:
    name: str
    start: float
    end: float
    counterclockwise: bool
    head_dx: float
    head_dy: float

    def sweep_rad(self) -> float:
        if self.counterclockwise:
            return (self.start - self.end) % (2.0 * math.pi)
        return (self.end - self.start) % (2.0 * math.pi)

    def end_point(self) -> tuple[float, float]:
        return (CX + RADIUS * math.cos(self.end), CY + RADIUS * math.sin(self.end))

    def cj_tokens(self) -> list[str]:
        ccw = "true" if self.counterclockwise else "false"
        tokens = [
            f"{self.start}",
            f"{self.end}",
            f"counterclockwise: {ccw}",
        ]
        for x, y in arrowhead_points(self):
            tokens.append(f"{x:.1f}")
            tokens.append(f"{y:.1f}")
        return tokens


# Undo: start just below east, CCW over the top, finish at the left, head points left.
# Sweep ≈ 200° (mock 甲: 180–225° counterclockwise curved arrow).
UNDO = ArcIcon("undo", start=0.35, end=3.32, counterclockwise=True, head_dx=-1.0, head_dy=0.0)

# Redraw: start top-left, CW up→right→down→bottom-left (≈ 3/4 turn).
# Head points down-left (mock 甲 refresh).
REDRAW = ArcIcon(
    "redraw", start=3.93, end=2.36, counterclockwise=False, head_dx=-0.72, head_dy=0.72
)


def _unit(dx: float, dy: float) -> tuple[float, float]:
    length = math.hypot(dx, dy)
    return (dx / length, dy / length)


def arrowhead_points(spec: ArcIcon) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    ex, ey = spec.end_point()
    ux, uy = _unit(spec.head_dx, spec.head_dy)
    tip = (ex + ux * HEAD_LEN, ey + uy * HEAD_LEN)
    px, py = -uy, ux
    wing1 = (ex + px * HEAD_HALF, ey + py * HEAD_HALF)
    wing2 = (ex - px * HEAD_HALF, ey - py * HEAD_HALF)
    return (tip, wing1, wing2)


def assert_inside_icon(pt: tuple[float, float], pad: float = 0.4) -> None:
    x, y = pt
    if not (pad <= x <= ICON_VP - pad and pad <= y <= ICON_VP - pad):
        raise AssertionError(f"icon point {pt} escapes the {ICON_VP}vp box")


def svg() -> str:
    def path_d(spec: ArcIcon) -> str:
        large = 1 if spec.sweep_rad() > math.pi else 0
        sweep = 0 if spec.counterclockwise else 1
        sx = CX + RADIUS * math.cos(spec.start)
        sy = CY + RADIUS * math.sin(spec.start)
        ex, ey = spec.end_point()
        return (
            f"M {sx:.2f} {sy:.2f} A {RADIUS} {RADIUS} 0 {large} {sweep} {ex:.2f} {ey:.2f}"
        )

    def tri(spec: ArcIcon) -> str:
        pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in arrowhead_points(spec))
        return f'<polygon points="{pts}" fill="{INK_HEX}"/>'

    def icon(spec: ArcIcon, label: str, ox: float) -> str:
        return (
            f'<g transform="translate({ox},8)">'
            f'<rect x="0" y="0" width="{ICON_VP}" height="{ICON_VP}" fill="#FBF6EC" '
            f'stroke="#2C2A26" stroke-width="0.6" rx="4"/>'
            f'<path d="{path_d(spec)}" fill="none" stroke="{INK_HEX}" '
            f'stroke-width="{HAIRLINE}" stroke-linecap="round"/>'
            f"{tri(spec)}"
            f'<text x="12" y="36" text-anchor="middle" font-size="7" fill="#2C2A26">{label}</text>'
            f"</g>"
        )

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="220" height="56" viewBox="0 0 220 56">'
        '<rect width="220" height="56" fill="#F3E8D6"/>'
        f'{icon(UNDO, "撤销", 28)}'
        f'{icon(REDRAW, "重绘驿道", 120)}'
        "</svg>\n"
    )


if __name__ == "__main__":
    print(svg(), end="")
