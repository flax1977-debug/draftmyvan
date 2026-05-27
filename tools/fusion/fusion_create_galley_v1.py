#!/usr/bin/env python3
"""Fusion 360 geometry-plan skeleton for galley_v1 panel payloads.

This module is intentionally importable in normal Python without Fusion 360 or
Autodesk `adsk` modules installed. CI validates the deterministic geometry plan
only; it does not execute Fusion geometry creation, drawings, cut lists, DXF, or
CNC output.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import compute_galley_panels as panel_math


EXPECTED_TEMPLATE = "galley_v1"
EXPECTED_STATUS = "planned_not_executed"
REQUIRED_PLAN_PANEL_FIELDS = (
    "name",
    "component_name",
    "body_name",
    "length_mm",
    "width_mm",
    "thickness_mm",
    "quantity",
    "material",
    "orientation",
    "sketch_plane",
    "extrude_axis",
    "extrude_distance_mm",
    "placement_origin_mm",
    "placement_note",
    "construction_method",
    "status",
    "notes",
)
DEFERRED = [
    "Fusion API execution",
    "joints",
    "kerf",
    "rabbets/dados",
    "edging",
    "door/drawer fronts",
    "sink cut-out",
    "hardware drilling",
    "drawings",
    "DXF/CNC",
    "manufacturing sign-off",
]


class FusionGeometryPlanError(Exception):
    """Raised when panel payloads or geometry plans are invalid."""


def load_panel_payload(path: str | Path) -> dict[str, Any]:
    """Load and validate a panel payload JSON file."""
    payload_path = Path(path)
    try:
        with payload_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except OSError as e:
        raise FusionGeometryPlanError(f"cannot read {payload_path}: {e}") from e
    except json.JSONDecodeError as e:
        raise FusionGeometryPlanError(f"invalid JSON in {payload_path}: {e}") from e
    return validate_panel_payload(payload)


def _required_non_empty_string(obj: dict[str, Any], key: str, *, label: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise FusionGeometryPlanError(f"{label}.{key} must be a non-empty string")
    return value


def validate_panel_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the output shape produced by `export_galley_v1_panels.py`."""
    if not isinstance(payload, dict):
        raise FusionGeometryPlanError("panel payload root must be an object")
    template = _required_non_empty_string(payload, "template", label="payload")
    if template != EXPECTED_TEMPLATE:
        raise FusionGeometryPlanError(f'payload.template must be "{EXPECTED_TEMPLATE}"')
    _required_non_empty_string(payload, "manifest_id", label="payload")

    assumptions = payload.get("assumptions")
    if not isinstance(assumptions, list) or not assumptions:
        raise FusionGeometryPlanError("payload.assumptions must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in assumptions):
        raise FusionGeometryPlanError("payload.assumptions must contain non-empty strings")

    panels = payload.get("panels")
    try:
        panel_math.validate_panel_list(panels)
    except panel_math.GalleyPanelError as e:
        raise FusionGeometryPlanError(str(e)) from e

    totals = payload.get("totals")
    if not isinstance(totals, dict):
        raise FusionGeometryPlanError("payload.totals must be an object")
    if totals.get("panel_count") != sum(panel["quantity"] for panel in panels):
        raise FusionGeometryPlanError("payload.totals.panel_count must match panel quantities")
    if totals.get("unique_panel_types") != len({panel["name"] for panel in panels}):
        raise FusionGeometryPlanError("payload.totals.unique_panel_types must match panel names")
    return payload


def _overall_dimensions(panels: list[dict[str, Any]]) -> dict[str, int]:
    by_name = {panel["name"]: panel for panel in panels}
    missing = [
        name
        for name in ("left_side", "right_side", "bottom_panel", "top_panel", "back_panel")
        if name not in by_name
    ]
    if missing:
        raise FusionGeometryPlanError("panel payload missing required panels: " + ", ".join(missing))

    left = by_name["left_side"]
    bottom = by_name["bottom_panel"]
    thickness = left["thickness_mm"]
    return {
        "Width": bottom["length_mm"] + 2 * thickness,
        "Depth": left["width_mm"],
        "Height": left["length_mm"],
        "PlyThickness": thickness,
    }


def _component_name(panel_name: str) -> str:
    return "Galley_" + "".join(part.capitalize() for part in panel_name.split("_"))


def _placement(panel: dict[str, Any], dims: dict[str, int]) -> tuple[str, str, int, list[int], str]:
    name = panel["name"]
    thickness = dims["PlyThickness"]
    if name == "left_side":
        return "YZ", "X", thickness, [0, 0, 0], "floor_back_left carcass origin; final Fusion placement still manual/verified later"
    if name == "right_side":
        return "YZ", "X", thickness, [dims["Width"] - thickness, 0, 0], "right side offset by overall width minus panel thickness; verify in Fusion later"
    if name == "bottom_panel":
        return "XY", "Z", thickness, [thickness, 0, 0], "bottom panel fits between side panels at floor level; verify in Fusion later"
    if name == "top_panel":
        return "XY", "Z", thickness, [thickness, 0, dims["Height"] - thickness], "top panel fits between side panels at overall height minus thickness; verify in Fusion later"
    if name == "back_panel":
        return "XZ", "Y", thickness, [thickness, 0, thickness], "back panel fits inside side/top/bottom frame at rear plane; verify in Fusion later"
    raise FusionGeometryPlanError(f"no placement rule for panel {name!r}")


def fusion_geometry_plan(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic planned-not-executed Fusion geometry plan."""
    validate_panel_payload(payload)
    panels = payload["panels"]
    dims = _overall_dimensions(panels)
    planned_panels: list[dict[str, Any]] = []
    for panel in panels:
        sketch_plane, extrude_axis, extrude_distance, origin, placement_note = _placement(panel, dims)
        planned_panels.append(
            {
                "name": panel["name"],
                "component_name": _component_name(panel["name"]),
                "body_name": f"{panel['name']}_body",
                "length_mm": panel["length_mm"],
                "width_mm": panel["width_mm"],
                "thickness_mm": panel["thickness_mm"],
                "quantity": panel["quantity"],
                "material": panel["material"],
                "orientation": panel["orientation"],
                "sketch_plane": sketch_plane,
                "extrude_axis": extrude_axis,
                "extrude_distance_mm": extrude_distance,
                "placement_origin_mm": origin,
                "placement_note": placement_note,
                "construction_method": "rectangular sketch + extrude",
                "status": EXPECTED_STATUS,
                "notes": panel["notes"],
            }
        )
    plan = {
        "template": payload["template"],
        "manifest_id": payload["manifest_id"],
        "units": "mm",
        "source": "panel_payload",
        "geometry_status": EXPECTED_STATUS,
        "panels": planned_panels,
        "deferred": DEFERRED,
    }
    validate_geometry_plan(plan)
    return plan


def _required_positive_int(panel: dict[str, Any], key: str) -> int:
    value = panel.get(key)
    name = panel.get("name", "<unknown>")
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise FusionGeometryPlanError(f"plan panel {name!r} field {key} must be a positive integer")
    return value


def _placement_origin(panel: dict[str, Any]) -> list[int | float]:
    value = panel.get("placement_origin_mm")
    name = panel.get("name", "<unknown>")
    if not isinstance(value, list) or len(value) != 3:
        raise FusionGeometryPlanError(
            f"plan panel {name!r} field placement_origin_mm must be a 3-number list"
        )
    for coord in value:
        if isinstance(coord, bool) or not isinstance(coord, (int, float)):
            raise FusionGeometryPlanError(
                f"plan panel {name!r} field placement_origin_mm must be a 3-number list"
            )
    return value


def validate_geometry_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Validate a deterministic planned-not-executed Fusion geometry plan."""
    if not isinstance(plan, dict):
        raise FusionGeometryPlanError("geometry plan root must be an object")
    template = _required_non_empty_string(plan, "template", label="plan")
    if template != EXPECTED_TEMPLATE:
        raise FusionGeometryPlanError(f'plan.template must be "{EXPECTED_TEMPLATE}"')
    _required_non_empty_string(plan, "manifest_id", label="plan")
    if plan.get("units") != "mm":
        raise FusionGeometryPlanError('plan.units must be "mm"')
    if plan.get("source") != "panel_payload":
        raise FusionGeometryPlanError('plan.source must be "panel_payload"')
    if plan.get("geometry_status") != EXPECTED_STATUS:
        raise FusionGeometryPlanError(f'plan.geometry_status must be "{EXPECTED_STATUS}"')

    deferred = plan.get("deferred")
    if not isinstance(deferred, list) or not deferred:
        raise FusionGeometryPlanError("plan.deferred must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in deferred):
        raise FusionGeometryPlanError("plan.deferred must contain non-empty strings")

    panels = plan.get("panels")
    if not isinstance(panels, list) or not panels:
        raise FusionGeometryPlanError("plan.panels must be a non-empty list")

    names: set[str] = set()
    component_names: set[str] = set()
    body_names: set[str] = set()
    for index, panel in enumerate(panels):
        if not isinstance(panel, dict):
            raise FusionGeometryPlanError(f"plan panel at index {index} must be an object")
        missing = [field for field in REQUIRED_PLAN_PANEL_FIELDS if field not in panel]
        if missing:
            raise FusionGeometryPlanError(
                f"plan panel at index {index} is missing fields: " + ", ".join(missing)
            )

        name = _required_non_empty_string(panel, "name", label="plan panel")
        component_name = _required_non_empty_string(panel, "component_name", label="plan panel")
        body_name = _required_non_empty_string(panel, "body_name", label="plan panel")
        if name in names:
            raise FusionGeometryPlanError(f"duplicate plan panel name: {name}")
        if component_name in component_names:
            raise FusionGeometryPlanError(f"duplicate component_name: {component_name}")
        if body_name in body_names:
            raise FusionGeometryPlanError(f"duplicate body_name: {body_name}")
        names.add(name)
        component_names.add(component_name)
        body_names.add(body_name)

        for key in (
            "length_mm",
            "width_mm",
            "thickness_mm",
            "quantity",
            "extrude_distance_mm",
        ):
            _required_positive_int(panel, key)
        for key in (
            "material",
            "orientation",
            "sketch_plane",
            "extrude_axis",
            "placement_note",
            "construction_method",
            "status",
            "notes",
        ):
            _required_non_empty_string(panel, key, label="plan panel")
        if panel["status"] != EXPECTED_STATUS:
            raise FusionGeometryPlanError(
                f"plan panel {name!r} field status must be {EXPECTED_STATUS!r}"
            )
        _placement_origin(panel)
    return plan


def geometry_plan_summary(plan: dict[str, Any]) -> str:
    """Return a concise deterministic text summary of a geometry plan."""
    validate_geometry_plan(plan)
    lines = [
        f"template: {plan['template']}",
        f"manifest_id: {plan['manifest_id']}",
        f"geometry_status: {plan['geometry_status']}",
        f"planned_panel_count: {len(plan['panels'])}",
    ]
    for panel in plan["panels"]:
        lines.append(f"{panel['component_name']} -> {panel['body_name']}")
    return os.linesep.join(lines)


def _fusion_message_box(message: str) -> None:
    """Show a message in Fusion 360 without importing Autodesk modules in CI."""
    import adsk.core  # type: ignore[import-not-found]

    app = adsk.core.Application.get()
    ui = app.userInterface if app else None
    if ui is not None:
        ui.messageBox(message)


def ensure_component(root: Any, component_name: str) -> Any:
    """Future Fusion helper placeholder for component lookup/creation."""
    # TODO(Fusion): use adsk.fusion.Design.cast(app.activeProduct), then search
    # root.occurrences and create a new occurrence/component when needed.
    raise NotImplementedError("Fusion component creation is deferred")


def set_user_parameter(design: Any, name: str, value_mm: int) -> None:
    """Future Fusion helper placeholder for user-parameter creation."""
    # TODO(Fusion): use design.userParameters.add(...) with adsk.core.ValueInput
    # so panel dimensions remain editable in Fusion.
    raise NotImplementedError("Fusion user-parameter creation is deferred")


def create_panel_body(component: Any, panel_plan: dict[str, Any]) -> Any:
    """Future Fusion helper placeholder for sketch/extrude body creation."""
    # TODO(Fusion): use root.sketches.add(...) on the planned sketch plane.
    # TODO(Fusion): use sketch.sketchCurves.sketchLines.addTwoPointRectangle(...)
    # for the rectangular panel profile.
    # TODO(Fusion): use extrudes = root.features.extrudeFeatures.
    # TODO(Fusion): use extrudeInput = extrudes.createInput(...).
    # TODO(Fusion): use extrudes.add(extrudeInput) and name the resulting body.
    raise NotImplementedError("Fusion panel body creation is deferred")


def create_galley_carcass_from_panels(design: Any, plan: dict[str, Any]) -> None:
    """Future Fusion helper placeholder for executing a full carcass plan."""
    # TODO(Fusion): start from adsk.core.Application.get(), then
    # adsk.fusion.Design.cast(app.activeProduct), set user parameters, ensure
    # components, create each panel body, and apply transforms from
    # placement_origin_mm after manual verification in Fusion.
    raise NotImplementedError("Fusion geometry execution is deferred")


def run(context: Any) -> None:
    """Fusion 360 script entry point.

    CI never calls this entry point. When run inside Fusion later, pass a panel
    payload path as `context` or through `DRAFTMYVAN_FUSION_PANEL_PAYLOAD`.
    This version validates and summarizes the deterministic geometry plan only;
    real geometry creation remains deferred until manually verified in Fusion.
    """
    payload_path = str(context or os.environ.get("DRAFTMYVAN_FUSION_PANEL_PAYLOAD", "")).strip()
    if not payload_path:
        _fusion_message_box(
            "DraftMyVan galley_v1 geometry skeleton loaded. "
            "No panel payload path was supplied; no geometry was created."
        )
        return

    payload = load_panel_payload(payload_path)
    plan = fusion_geometry_plan(payload)
    _fusion_message_box(
        "DraftMyVan galley_v1 geometry plan accepted.\n"
        f"{geometry_plan_summary(plan)}\n"
        "Geometry creation deferred; no Fusion bodies, drawings, cut lists, "
        "DXF, or CNC output were created."
    )
