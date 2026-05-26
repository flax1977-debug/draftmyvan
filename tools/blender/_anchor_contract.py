"""Anchor / origin enforcement rules shared by the pure-Python and bpy validators.

Authoring coordinate contract (Blender source-of-truth):

    +X = width   — left/right across the van
    +Y = depth   — front/back module depth (back is the wall the cabinet
                   typically presses against; "back_left" is the rear-left corner)
    +Z = height  — floor → roof

Blender object data is in metres; the manifest's truth is millimetres.
This module operates entirely in millimetres after the GLB units conversion
done upstream.

For `anchor = "floor_back_left"` the contract is:

    bbox_min ≈ (0, 0, 0) within tolerance
    bbox_max ≈ (width_mm, depth_mm, height_mm) within tolerance

i.e. the rear-left-bottom corner of the assembled mesh sits at the world
origin and the mesh extends into +X, +Y, +Z.

Any axis swap or handedness flip required by a downstream tool (UE5 import,
Fusion 360 placement) is the downstream tool's responsibility. The source
GLB and its manifest entry must never be mutated to suit a viewer.

This module deliberately implements only `floor_back_left` for V1. Every
other anchor declared in the schema returns an explicit
`UnsupportedAnchorError` so the validator can fail loudly rather than
silently accept an unverified asset.
"""

from __future__ import annotations

from typing import Iterable

SUPPORTED_ANCHORS: frozenset[str] = frozenset({"floor_back_left"})


class UnsupportedAnchorError(Exception):
    """The anchor value is valid in the schema but not yet enforceable here."""

    def __init__(self, anchor: str) -> None:
        super().__init__(f"anchor enforcement not implemented for {anchor!r}")
        self.anchor = anchor


def expected_corners_mm(
    anchor: str,
    dims_mm: tuple[int, int, int],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Return (expected_min, expected_max) corners in millimetres for `anchor`."""
    width, depth, height = dims_mm
    if anchor == "floor_back_left":
        return (0.0, 0.0, 0.0), (float(width), float(depth), float(height))
    raise UnsupportedAnchorError(anchor)


def check_origin_anchor(
    bbox_min_mm: tuple[float, float, float],
    bbox_max_mm: tuple[float, float, float],
    dims_mm: tuple[int, int, int],
    anchor: str,
    tolerance_mm: float,
) -> tuple[bool, list[str]]:
    """Verify the supplied bbox corners match the contract for `anchor`.

    Returns (ok, report_lines). Unsupported anchors always return
    (False, [explanatory line]) — silent pass is not an option.
    """
    try:
        expected_min, expected_max = expected_corners_mm(anchor, dims_mm)
    except UnsupportedAnchorError as e:
        return False, [f"  [FAIL] {e}"]

    lines: list[str] = []
    ok = True
    for corner_name, actual_corner, expected_corner in (
        ("min", bbox_min_mm, expected_min),
        ("max", bbox_max_mm, expected_max),
    ):
        for axis_idx, axis_name in enumerate(("x", "y", "z")):
            a = actual_corner[axis_idx]
            e = expected_corner[axis_idx]
            delta = a - e
            within = abs(delta) <= tolerance_mm
            marker = "OK" if within else "FAIL"
            lines.append(
                f"  [{marker}] {corner_name}.{axis_name}: glb={a:.3f} mm  "
                f"expected={e:.3f} mm  delta={delta:+.3f} mm  "
                f"(tolerance={tolerance_mm} mm)"
            )
            if not within:
                ok = False
    return ok, lines
