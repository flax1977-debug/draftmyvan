#!/usr/bin/env python3
"""Compute simple galley_v1 carcass panels from a validated Fusion payload.

This is panel math only. It is not a cut list, drawing generator, DXF/CNC
exporter, or manufacturing-ready output.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import fusion_galley_v1_skeleton as skeleton


ASSUMPTIONS = [
    "Simple galley_v1 carcass panels only.",
    "No kerf allowance.",
    "No rabbets or dados.",
    "No edging.",
    "No door or drawer fronts.",
    "No sink cut-out.",
    "No hardware drilling.",
    "Top and bottom panels fit between side panels.",
    "Back panel fits between side panels and between top/bottom panels.",
]

REQUIRED_PANEL_FIELDS = (
    "name",
    "length_mm",
    "width_mm",
    "thickness_mm",
    "quantity",
    "material",
    "orientation",
    "notes",
)


class GalleyPanelError(Exception):
    """Raised when galley panel math input or output is invalid."""


def load_payload(path: str | Path) -> dict[str, Any]:
    """Load and validate a galley_v1 Fusion payload for panel math."""
    try:
        payload = skeleton.load_parameter_payload(path)
        skeleton.validate_parameter_payload(payload)
    except skeleton.FusionPayloadError as e:
        raise GalleyPanelError(str(e)) from e
    return payload


def _parameters(payload: dict[str, Any]) -> dict[str, int]:
    try:
        skeleton.validate_parameter_payload(payload)
    except skeleton.FusionPayloadError as e:
        raise GalleyPanelError(str(e)) from e
    return payload["parameters"]


def _panel(
    *,
    name: str,
    length_mm: int,
    width_mm: int,
    thickness_mm: int,
    orientation: str,
    notes: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "length_mm": length_mm,
        "width_mm": width_mm,
        "thickness_mm": thickness_mm,
        "quantity": 1,
        "material": "plywood",
        "orientation": orientation,
        "notes": notes,
    }


def compute_galley_panels(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return deterministic simple carcass panels for a galley_v1 payload."""
    params = _parameters(payload)
    width = params["Width"]
    depth = params["Depth"]
    height = params["Height"]
    thickness = params["PlyThickness"]

    if width <= 2 * thickness:
        raise GalleyPanelError("parameters.Width must be greater than 2 * parameters.PlyThickness")
    if height <= 2 * thickness:
        raise GalleyPanelError("parameters.Height must be greater than 2 * parameters.PlyThickness")

    internal_width = width - 2 * thickness
    internal_height = height - 2 * thickness
    panels = [
        _panel(
            name="left_side",
            length_mm=height,
            width_mm=depth,
            thickness_mm=thickness,
            orientation="vertical_side",
            notes="Full-height left side; no kerf, rabbets, dados, or edging allowance.",
        ),
        _panel(
            name="right_side",
            length_mm=height,
            width_mm=depth,
            thickness_mm=thickness,
            orientation="vertical_side",
            notes="Full-height right side; no kerf, rabbets, dados, or edging allowance.",
        ),
        _panel(
            name="bottom_panel",
            length_mm=internal_width,
            width_mm=depth,
            thickness_mm=thickness,
            orientation="horizontal_base",
            notes="Fits between side panels; no kerf, rabbets, dados, or edging allowance.",
        ),
        _panel(
            name="top_panel",
            length_mm=internal_width,
            width_mm=depth,
            thickness_mm=thickness,
            orientation="horizontal_top",
            notes="Fits between side panels; no sink cut-out, kerf, rabbets, dados, or edging allowance.",
        ),
        _panel(
            name="back_panel",
            length_mm=internal_width,
            width_mm=internal_height,
            thickness_mm=thickness,
            orientation="vertical_back",
            notes="Fits between side panels and between top/bottom panels; no kerf or joinery allowance.",
        ),
    ]
    validate_panel_list(panels)
    return panels


def _required_positive_int(panel: dict[str, Any], key: str) -> int:
    value = panel.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        name = panel.get("name", "<unknown>")
        raise GalleyPanelError(f"panel {name!r} field {key} must be a positive integer")
    return value


def _required_non_empty_string(panel: dict[str, Any], key: str) -> str:
    value = panel.get(key)
    name = panel.get("name", "<unknown>")
    if not isinstance(value, str) or not value.strip():
        raise GalleyPanelError(f"panel {name!r} field {key} must be a non-empty string")
    return value


def validate_panel_list(panels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate panel records produced by `compute_galley_panels`."""
    if not isinstance(panels, list) or not panels:
        raise GalleyPanelError("panels must be a non-empty list")

    names: set[str] = set()
    for index, panel in enumerate(panels):
        if not isinstance(panel, dict):
            raise GalleyPanelError(f"panel at index {index} must be an object")
        missing = [field for field in REQUIRED_PANEL_FIELDS if field not in panel]
        if missing:
            raise GalleyPanelError(
                f"panel at index {index} is missing fields: " + ", ".join(missing)
            )
        name = _required_non_empty_string(panel, "name")
        if name in names:
            raise GalleyPanelError(f"duplicate panel name: {name}")
        names.add(name)
        for key in ("length_mm", "width_mm", "thickness_mm", "quantity"):
            _required_positive_int(panel, key)
        for key in ("material", "orientation", "notes"):
            _required_non_empty_string(panel, key)
    return panels


def panel_totals(panels: list[dict[str, Any]]) -> dict[str, Any]:
    validate_panel_list(panels)
    panel_count = sum(panel["quantity"] for panel in panels)
    area_mm2 = sum(
        panel["length_mm"] * panel["width_mm"] * panel["quantity"]
        for panel in panels
    )
    return {
        "panel_count": panel_count,
        "unique_panel_types": len({panel["name"] for panel in panels}),
        "approximate_sheet_area_m2": round(area_mm2 / 1_000_000, 6),
    }


def build_panel_breakdown(payload: dict[str, Any]) -> dict[str, Any]:
    panels = compute_galley_panels(payload)
    return {
        "template": payload["template"],
        "manifest_id": payload["manifest_id"],
        "assumptions": ASSUMPTIONS,
        "panels": panels,
        "totals": panel_totals(panels),
    }


def panel_summary(panels: list[dict[str, Any]]) -> str:
    """Return a concise deterministic text summary of panel math output."""
    validate_panel_list(panels)
    totals = panel_totals(panels)
    lines = [
        f"panel_count: {totals['panel_count']}",
        f"unique_panel_types: {totals['unique_panel_types']}",
        f"approximate_sheet_area_m2: {totals['approximate_sheet_area_m2']:.6f}",
    ]
    for panel in panels:
        lines.append(
            f"{panel['name']}: {panel['quantity']} x "
            f"{panel['length_mm']} x {panel['width_mm']} x {panel['thickness_mm']} mm "
            f"{panel['material']} ({panel['orientation']})"
        )
    return os.linesep.join(lines)
