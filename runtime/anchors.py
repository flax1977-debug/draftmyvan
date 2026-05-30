"""Anchor semantics: map a module's anchor + position to a van-space AABB.

Single source of truth shared by layout validation (collision/containment)
and — mirrored in the frontend — by the 3D renderer.

Van space (millimetres): X = width (left wall at x=0, right wall at x=van
width), Y = length (front-back), Z = height (floor at z=0, ceiling at z=van
height). A module's manifest dimensions are width (W → van X), depth (D → van
Y), height (H → van Z). No axis swap: the anchor only chooses which corner
position_mm denotes and which way each dimension extends.

Supported anchors (V1) and how position_mm (x, y, z) maps to the AABB
(rotation 0; +Y always extends from y):

  floor_back_left  reference = back-left-floor corner; X +W, Z +H (up).
                   box = [x, x+W] · [y, y+D] · [z, z+H]
  wall_left        same X/Z extents as floor; mounted against the left wall
                   (x≈0) at height z. box = [x, x+W] · [y, y+D] · [z, z+H]
  wall_right       mounted against the right wall; X extends -W from x (the
                   right edge). box = [x-W, x] · [y, y+D] · [z, z+H]
  ceiling_left     hangs from the ceiling; z is the TOP, H extends down.
                   box = [x, x+W] · [y, y+D] · [z-H, z]
  ceiling_right    right-side ceiling. box = [x-W, x] · [y, y+D] · [z-H, z]

Rotation (rotation_deg, about vertical Z) rotates the W×D footprint about the
reference corner, exactly as floor_back_left already did; "right" anchors then
mirror that footprint in X. Curved walls / wheel arches are not modelled.

The GLB authoring origin is anchor-independent: a module GLB always has its
bounding-box minimum at the local origin (0,0,0). Placement applies these
anchor rules; the GLB validation gate only checks that authored contract.
"""

from __future__ import annotations

import math

# Anchor flavour sets.
_RIGHT = frozenset({"wall_right", "ceiling_right"})
_CEILING = frozenset({"ceiling_left", "ceiling_right"})
SUPPORTED_ANCHORS = frozenset(
    {"floor_back_left", "wall_left", "wall_right", "ceiling_left", "ceiling_right"}
)


class UnsupportedAnchorError(Exception):
    """The anchor is valid in the schema but not yet implemented here."""

    def __init__(self, anchor: str) -> None:
        super().__init__(f"anchor semantics not implemented for {anchor!r}")
        self.anchor = anchor


def _footprint_offsets(w: float, d: float, rotation_deg: float) -> tuple[float, float, float, float]:
    """(min_x, max_x, min_y, max_y) of the W×D rect rotated about its corner.

    Multiples of 90 deg use exact integer rotation; other angles use trig.
    """
    rot = rotation_deg % 360
    corners = ((0.0, 0.0), (w, 0.0), (0.0, d), (w, d))
    if rot in (0, 90, 180, 270):
        def r(cx: float, cy: float) -> tuple[float, float]:
            if rot == 0:
                return (cx, cy)
            if rot == 90:
                return (-cy, cx)
            if rot == 180:
                return (-cx, -cy)
            return (cy, -cx)  # 270
        pts = [r(cx, cy) for cx, cy in corners]
    else:
        theta = math.radians(rot)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        pts = [(cx * cos_t - cy * sin_t, cx * sin_t + cy * cos_t) for cx, cy in corners]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), max(xs), min(ys), max(ys)


def aabb(
    anchor: str,
    x: float,
    y: float,
    z: float,
    w: float,
    d: float,
    h: float,
    rotation_deg: float = 0.0,
) -> tuple[float, float, float, float, float, float]:
    """Van-space (x0, x1, y0, y1, z0, z1) for an anchored, positioned module."""
    if anchor not in SUPPORTED_ANCHORS:
        raise UnsupportedAnchorError(anchor)
    fx0, fx1, fy0, fy1 = _footprint_offsets(w, d, rotation_deg)
    if anchor in _RIGHT:
        x0, x1 = x - fx1, x - fx0
    else:
        x0, x1 = x + fx0, x + fx1
    y0, y1 = y + fy0, y + fy1
    if anchor in _CEILING:
        z0, z1 = z - h, z
    else:
        z0, z1 = z, z + h
    return (x0, x1, y0, y1, z0, z1)
