#!/usr/bin/env python3
"""Geometry spec for approved 24vp stroke-only undo/redraw icons.

Source of truth: designer SVG (24×24, stroke-width 1.5, open chevron, no fill).
Canvas Y grows down. Angles are Canvas radians (0 = east, π/2 = south).
SVG elliptical A is converted to Path2D.arc center parameterization
(W3C SVG implnote endpoint-to-center).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

ICON_VP = 24
INK_HEX = "#2C2A26"
STROKE = 1.5
ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Seg:
    x1: float
    y1: float
    x2: float
    y2: float

    def points(self) -> tuple[tuple[float, float], tuple[float, float]]:
        return ((self.x1, self.y1), (self.x2, self.y2))


@dataclass(frozen=True)
class StrokeIcon:
    name: str
    # SVG: M x0 y0 A r r 0 large sweep x1 y1
    arc_x0: float
    arc_y0: float
    radius: float
    large_arc: int
    sweep: int
    arc_x1: float
    arc_y1: float
    arm_a: Seg
    arm_b: Seg

    def canvas_arc(self) -> tuple[float, float, float, float, float, bool]:
        return svg_a_to_canvas_arc(
            self.arc_x0,
            self.arc_y0,
            self.radius,
            self.radius,
            0.0,
            self.large_arc,
            self.sweep,
            self.arc_x1,
            self.arc_y1,
        )

    def counterclockwise(self) -> bool:
        return self.sweep == 0

    def sweep_rad(self) -> float:
        cx, cy, r, start, end, ccw = self.canvas_arc()
        if ccw:
            return (start - end) % (2.0 * math.pi)
        return (end - start) % (2.0 * math.pi)

    def cj_tokens(self) -> list[str]:
        cx, cy, r, start, end, ccw = self.canvas_arc()
        ccw_lit = "true" if ccw else "false"
        tokens = [
            fmt_num(STROKE),
            fmt_num(cx),
            fmt_num(cy),
            fmt_num(r),
            fmt_num(start),
            fmt_num(end),
            f"counterclockwise: {ccw_lit}",
        ]
        for arm in (self.arm_a, self.arm_b):
            for x, y in arm.points():
                tokens.append(fmt_num(x))
                tokens.append(fmt_num(y))
        return tokens

    def icon_svg(self) -> str:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
            'viewBox="0 0 24 24" fill="none">\n'
            f'  <path d="M{fmt_num(self.arc_x0)} {fmt_num(self.arc_y0)} '
            f"A{fmt_num(self.radius)} {fmt_num(self.radius)} 0 "
            f'{self.large_arc} {self.sweep} {fmt_num(self.arc_x1)} {fmt_num(self.arc_y1)}" '
            f'stroke="{INK_HEX}" stroke-width="{fmt_num(STROKE)}" stroke-linecap="round"/>\n'
            f'  <path d="M{fmt_num(self.arm_a.x1)} {fmt_num(self.arm_a.y1)} '
            f'L{fmt_num(self.arm_a.x2)} {fmt_num(self.arm_a.y2)}" '
            f'stroke="{INK_HEX}" stroke-width="{fmt_num(STROKE)}" stroke-linecap="round"/>\n'
            f'  <path d="M{fmt_num(self.arm_b.x1)} {fmt_num(self.arm_b.y1)} '
            f'L{fmt_num(self.arm_b.x2)} {fmt_num(self.arm_b.y2)}" '
            f'stroke="{INK_HEX}" stroke-width="{fmt_num(STROKE)}" stroke-linecap="round"/>\n'
            "</svg>\n"
        )


# Approved 24×24 SVG (undo = CCW large arc + left open chevron).
UNDO = StrokeIcon(
    name="undo",
    arc_x0=8.9,
    arc_y0=16.9,
    radius=6.35,
    large_arc=1,
    sweep=0,
    arc_x1=9.8,
    arc_y1=6.6,
    arm_a=Seg(12.0, 2.5, 6.5, 6.5),
    arm_b=Seg(6.5, 9.5, 12.0, 14.0),
)

# Optical mirror (redraw = CW large arc + right open chevron).
REDRAW = StrokeIcon(
    name="redraw",
    arc_x0=15.1,
    arc_y0=16.9,
    radius=6.35,
    large_arc=1,
    sweep=1,
    arc_x1=14.2,
    arc_y1=6.6,
    arm_a=Seg(12.0, 2.5, 17.5, 6.5),
    arm_b=Seg(17.5, 9.5, 12.0, 14.0),
)


def fmt_num(value: float) -> str:
    """Cangjie / SVG number matching index.cj Float64 literals."""
    rounded = round(float(value), 2)
    if abs(rounded - round(rounded, 1)) < 1e-9:
        return f"{rounded:.1f}"
    return f"{rounded:.2f}"


def svg_a_to_canvas_arc(
    x1: float,
    y1: float,
    rx: float,
    ry: float,
    phi_deg: float,
    fa: int,
    fs: int,
    x2: float,
    y2: float,
) -> tuple[float, float, float, float, float, bool]:
    """SVG A → (cx, cy, r, start, end, counterclockwise) for Canvas Path2D.arc.

    Angles stay in [0, 2π) so Cangjie 1.1.3 only sees positive Float64 literals.
    Sweep direction follows SVG sweep-flag: 0 = CCW, 1 = CW.
    """
    phi = math.radians(phi_deg)
    dx = (x1 - x2) / 2.0
    dy = (y1 - y2) / 2.0
    x1p = math.cos(phi) * dx + math.sin(phi) * dy
    y1p = -math.sin(phi) * dx + math.cos(phi) * dy
    lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
    if lam > 1.0:
        scale = math.sqrt(lam)
        rx *= scale
        ry *= scale
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    sq = math.sqrt(max(0.0, num / den))
    if fa == fs:
        sq = -sq
    cxp = sq * (rx * y1p / ry)
    cyp = sq * (-ry * x1p / rx)
    cx = math.cos(phi) * cxp - math.sin(phi) * cyp + (x1 + x2) / 2.0
    cy = math.sin(phi) * cxp + math.cos(phi) * cyp + (y1 + y2) / 2.0
    start = math.atan2(y1 - cy, x1 - cx)
    end = math.atan2(y2 - cy, x2 - cx)
    if start < 0.0:
        start += 2.0 * math.pi
    if end < 0.0:
        end += 2.0 * math.pi
    r = (math.hypot(x1 - cx, y1 - cy) + math.hypot(x2 - cx, y2 - cy)) / 2.0
    return (cx, cy, r, start, end, fs == 0)


def assert_inside_icon(pt: tuple[float, float], pad: float = 0.4) -> None:
    x, y = pt
    if not (pad <= x <= ICON_VP - pad and pad <= y <= ICON_VP - pad):
        raise AssertionError(f"icon point {pt} escapes the {ICON_VP}vp box")


def assert_open_chevron(spec: StrokeIcon) -> None:
    """Tip is two disjoint strokes — they must not share a vertex."""
    a = set(spec.arm_a.points())
    b = set(spec.arm_b.points())
    if a & b:
        raise AssertionError(f"{spec.name} chevron arms meet at {a & b}")


def svg() -> str:
    def icon(spec: StrokeIcon, label: str, ox: float) -> str:
        inner = spec.icon_svg().replace(
            '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
            'viewBox="0 0 24 24" fill="none">\n',
            "",
        ).replace("</svg>\n", "")
        return (
            f'<g transform="translate({ox},8)">'
            f'<rect x="0" y="0" width="{ICON_VP}" height="{ICON_VP}" fill="#FBF6EC" '
            f'stroke="#2C2A26" stroke-width="0.6" rx="4"/>'
            f"{inner}"
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


def write_icon_svgs(dest: Path | None = None) -> None:
    folder = dest if dest is not None else ROOT / "design" / "icons"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "icon-undo.svg").write_text(UNDO.icon_svg(), encoding="utf-8")
    (folder / "icon-reset.svg").write_text(REDRAW.icon_svg(), encoding="utf-8")


if __name__ == "__main__":
    write_icon_svgs()
    print(svg(), end="")
