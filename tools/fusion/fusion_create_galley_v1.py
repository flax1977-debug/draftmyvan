#!/usr/bin/env python3
"""Fusion 360 geometry-plan skeleton for galley_v1 panel payloads.

This module is intentionally importable in normal Python without Fusion 360 or
Autodesk `adsk` modules installed. CI validates the deterministic geometry plan
only; it does not execute Fusion geometry creation, drawings, cut lists, DXF, or
CNC output.

Role: this module is the canonical DRY-RUN / GEOMETRY-PLAN VALIDATION library
(use `--dry-run`, or import its plan/validation functions). Its in-module
`run(context)` builds geometry via per-panel components + sketch/extrude
(`Galley_*` components containing `*_body` bodies).

The canonical script for ACTUAL body creation inside Fusion is the separate,
self-contained BRep/BaseFeature runtime script at
`tools/fusion/scripts/fusion_create_galley_v1/fusion_create_galley_v1.py`,
which creates root bodies named `Galley_*`. The two implementations use
different geometry strategies and naming; see docs/current_status.md. Unifying
or retiring one of them is a tracked follow-up.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import compute_galley_panels as panel_math


EXPECTED_TEMPLATE = "galley_v1"
EXPECTED_STATUS = "planned_not_executed"
FUSION_UNAVAILABLE = "Fusion 360 API unavailable; run this inside Fusion 360 or use --dry-run"
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
    _validate_five_panel_carcass(panels)
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


def _validate_five_panel_carcass(panels: list[dict[str, Any]]) -> None:
    """Cross-check the current 5-panel carcass assumptions.

    The panel payload does not carry raw manifest dimensions. We infer outer
    Width/Depth/Height/PlyThickness from the known 5-panel shape and validate
    the relationships that are explicit in `compute_galley_panels.py`.
    """
    expected_order = ["left_side", "right_side", "bottom_panel", "top_panel", "back_panel"]
    names = [panel["name"] for panel in panels]
    if names != expected_order:
        raise FusionGeometryPlanError(
            "panel payload must contain exactly the 5 galley_v1 panels in order: "
            + ", ".join(expected_order)
        )

    by_name = {panel["name"]: panel for panel in panels}
    left = by_name["left_side"]
    right = by_name["right_side"]
    bottom = by_name["bottom_panel"]
    top = by_name["top_panel"]
    back = by_name["back_panel"]

    thickness = left["thickness_mm"]
    if any(panel["thickness_mm"] != thickness for panel in panels):
        raise FusionGeometryPlanError("all galley_v1 panels must share one thickness")
    if right["length_mm"] != left["length_mm"] or right["width_mm"] != left["width_mm"]:
        raise FusionGeometryPlanError("right_side dimensions must match left_side dimensions")
    if top["length_mm"] != bottom["length_mm"] or top["width_mm"] != bottom["width_mm"]:
        raise FusionGeometryPlanError("top_panel dimensions must match bottom_panel dimensions")
    if bottom["width_mm"] != left["width_mm"]:
        raise FusionGeometryPlanError("top/bottom panel depth must match side panel depth")
    if back["length_mm"] != bottom["length_mm"]:
        raise FusionGeometryPlanError("back_panel length must match top/bottom panel length")
    if back["width_mm"] != left["length_mm"] - 2 * thickness:
        raise FusionGeometryPlanError(
            "back_panel width must equal side panel height minus 2 * thickness"
        )


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


def is_running_in_fusion() -> bool:
    """Return True only when Autodesk Fusion APIs are importable and active."""
    try:
        import adsk.core  # type: ignore[import-not-found]
        import adsk.fusion  # type: ignore[import-not-found]
    except Exception:
        return False
    app = adsk.core.Application.get()
    if app is None or app.activeProduct is None:
        return False
    return adsk.fusion.Design.cast(app.activeProduct) is not None


def require_fusion_modules() -> tuple[Any, Any, Any, Any]:
    """Load Fusion API modules and return `(core, fusion, app, design)`.

    This is the only supported entry for Fusion API execution. Normal Python CI
    should use `--dry-run`, which stops before this function.
    """
    try:
        import adsk.core  # type: ignore[import-not-found]
        import adsk.fusion  # type: ignore[import-not-found]
    except Exception as e:
        raise FusionGeometryPlanError(FUSION_UNAVAILABLE) from e

    app = adsk.core.Application.get()
    if app is None or app.activeProduct is None:
        raise FusionGeometryPlanError(FUSION_UNAVAILABLE)
    design = adsk.fusion.Design.cast(app.activeProduct)
    if design is None:
        raise FusionGeometryPlanError(FUSION_UNAVAILABLE)
    return adsk.core, adsk.fusion, app, design


def _mm_to_cm(value_mm: int | float) -> float:
    """Convert millimetres to Fusion's database length unit, centimetres."""
    return float(value_mm) / 10.0


def _translation_matrix(core: Any, origin_mm: list[int | float]) -> Any:
    matrix = core.Matrix3D.create()
    matrix.translation = core.Vector3D.create(
        _mm_to_cm(origin_mm[0]),
        _mm_to_cm(origin_mm[1]),
        _mm_to_cm(origin_mm[2]),
    )
    return matrix


def ensure_component(
    root: Any,
    component_name: str,
    *,
    placement_origin_mm: list[int | float] | None = None,
) -> dict[str, Any]:
    """Create or find a Fusion component for one planned panel.

    The first-pass placement strategy uses the geometry plan's
    `placement_origin_mm` as the occurrence translation. Existing components are
    reused by component name and are not moved; manual verification must confirm
    placement in Fusion before trusting the output.
    """
    core, _fusion, _app, _design = require_fusion_modules()
    origin = placement_origin_mm or [0, 0, 0]

    for index in range(root.occurrences.count):
        occurrence = root.occurrences.item(index)
        component = occurrence.component
        if component and component.name == component_name:
            return {
                "component": component,
                "occurrence": occurrence,
                "created": False,
                "component_name": component_name,
            }

    occurrence = root.occurrences.addNewComponent(_translation_matrix(core, origin))
    component = occurrence.component
    component.name = component_name
    return {
        "component": component,
        "occurrence": occurrence,
        "created": True,
        "component_name": component_name,
    }


def set_user_parameter(design: Any, name: str, value_mm: int) -> dict[str, Any]:
    """Create or update one Fusion user parameter in millimetres."""
    core, _fusion, _app, _design = require_fusion_modules()
    expression = f"{value_mm} mm"
    existing = design.userParameters.itemByName(name)
    if existing:
        existing.expression = expression
        return {"name": name, "expression": expression, "created": False}

    value_input = core.ValueInput.createByString(expression)
    parameter = design.userParameters.add(name, value_input, "mm", "DraftMyVan galley_v1")
    return {"name": parameter.name, "expression": expression, "created": True}


def _sketch_plane(component: Any, sketch_plane: str) -> Any:
    if sketch_plane == "XY":
        return component.xYConstructionPlane
    if sketch_plane == "XZ":
        return component.xZConstructionPlane
    if sketch_plane == "YZ":
        return component.yZConstructionPlane
    raise FusionGeometryPlanError(f"unsupported sketch plane: {sketch_plane}")


def create_panel_body(
    panel_plan: dict[str, Any],
    *,
    design: Any | None = None,
    root_component: Any | None = None,
) -> dict[str, Any]:
    """Create one rectangular planned panel body inside Fusion 360.

    Input is one panel dict from `fusion_geometry_plan(payload)["panels"]`.
    Output is a structured result containing the component/body names and the
    Fusion body reference. This function is manual/Fusion-only and fails clearly
    in normal Python.
    """
    validate_geometry_plan(
        {
            "template": EXPECTED_TEMPLATE,
            "manifest_id": "single_panel_validation",
            "units": "mm",
            "source": "panel_payload",
            "geometry_status": EXPECTED_STATUS,
            "panels": [panel_plan],
            "deferred": DEFERRED,
        }
    )
    core, fusion, _app, active_design = require_fusion_modules()
    design = design or active_design
    root = root_component or design.rootComponent
    component_result = ensure_component(
        root,
        panel_plan["component_name"],
        placement_origin_mm=panel_plan["placement_origin_mm"],
    )
    component = component_result["component"]

    sketch = component.sketches.add(_sketch_plane(component, panel_plan["sketch_plane"]))
    sketch.name = f"{panel_plan['name']}_profile"
    lines = sketch.sketchCurves.sketchLines
    corner_a = core.Point3D.create(0, 0, 0)
    corner_b = core.Point3D.create(
        _mm_to_cm(panel_plan["length_mm"]),
        _mm_to_cm(panel_plan["width_mm"]),
        0,
    )
    lines.addTwoPointRectangle(corner_a, corner_b)

    profile = sketch.profiles.item(0)
    distance = core.ValueInput.createByString(f"{panel_plan['extrude_distance_mm']} mm")
    extrudes = component.features.extrudeFeatures
    feature = extrudes.addSimple(
        profile,
        distance,
        fusion.FeatureOperations.NewBodyFeatureOperation,
    )
    body = feature.bodies.item(0)
    body.name = panel_plan["body_name"]
    return {
        "component_name": panel_plan["component_name"],
        "body_name": panel_plan["body_name"],
        "component": component,
        "body": body,
        "placement_origin_mm": panel_plan["placement_origin_mm"],
        "created": True,
    }


def create_galley_carcass_from_panels(plan: dict[str, Any]) -> dict[str, Any]:
    """Create all planned galley_v1 panel bodies inside Fusion 360.

    The placement strategy is deterministic and first-pass only:
    bottom at base, side panels at width edges, top at overall height, and back
    at the rear/back plane using each panel's `placement_origin_mm`. Manual
    Fusion verification is required before trusting the geometry.
    """
    validate_geometry_plan(plan)
    _core, _fusion, _app, design = require_fusion_modules()
    root = design.rootComponent

    # These values are inferred from the geometry plan, not hidden manifest
    # state. They are user parameters for inspection/editing in Fusion.
    dims = _overall_dimensions(plan["panels"])
    for name, value in dims.items():
        set_user_parameter(design, name, value)

    created_panels = [
        create_panel_body(panel, design=design, root_component=root)
        for panel in plan["panels"]
    ]
    return {
        "status": "created_in_fusion_requires_manual_verification",
        "manifest_id": plan["manifest_id"],
        "panel_count": len(created_panels),
        "components": [panel["component_name"] for panel in created_panels],
        "bodies": [panel["body_name"] for panel in created_panels],
    }


def dry_run(payload_path: str | Path) -> tuple[str, list[str]]:
    """Validate a panel payload and summarize the planned Fusion geometry."""
    lines: list[str] = []
    try:
        payload = load_panel_payload(payload_path)
        plan = fusion_geometry_plan(payload)
        lines.append(f"[OK] panel payload readable: {payload_path}")
        lines.append(f"template: {payload['template']}")
        lines.append(f"manifest_id: {payload['manifest_id']}")
        lines.append(f"panel_count: {payload['totals']['panel_count']}")
        lines.append(geometry_plan_summary(plan))
        lines.append("RESULT: FUSION GEOMETRY DRY RUN VALID")
        return "FUSION GEOMETRY DRY RUN VALID", lines
    except FusionGeometryPlanError as e:
        lines.append(f"[FAIL] {e}")
        lines.append("RESULT: FUSION GEOMETRY DRY RUN INVALID")
        return "FUSION GEOMETRY DRY RUN INVALID", lines


def run(context: Any) -> None:
    """Fusion 360 script entry point.

    CI never calls this entry point. When run inside Fusion later, pass a panel
    payload path as `context` or through `DRAFTMYVAN_FUSION_PANEL_PAYLOAD`.
    This guarded path creates the five rectangular panel bodies for manual
    verification only. It does not create drawings, cut lists, DXF/CNC output,
    or manufacturing-ready artifacts.
    """
    payload_path = str(context or os.environ.get("DRAFTMYVAN_FUSION_PANEL_PAYLOAD", "")).strip()
    if not is_running_in_fusion():
        raise FusionGeometryPlanError(FUSION_UNAVAILABLE)
    if not payload_path:
        _fusion_message_box(
            "DraftMyVan galley_v1 geometry skeleton loaded. "
            "No panel payload path was supplied; no geometry was created."
        )
        return

    payload = load_panel_payload(payload_path)
    plan = fusion_geometry_plan(payload)
    result = create_galley_carcass_from_panels(plan)
    _fusion_message_box(
        "DraftMyVan galley_v1 geometry created for manual verification.\n"
        f"{geometry_plan_summary(plan)}\n"
        f"created_panel_count: {result['panel_count']}\n"
        "No drawings, cut lists, DXF, CNC output, or manufacturing-ready "
        "artifacts were created."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run or manually execute galley_v1 Fusion geometry creation.",
    )
    parser.add_argument(
        "--dry-run",
        metavar="PANEL_PAYLOAD",
        help="Validate a panel payload and summarize the planned Fusion geometry without Fusion.",
    )
    args = parser.parse_args(argv)

    if not args.dry_run:
        parser.error("use --dry-run in normal Python; run(context) is the Fusion 360 entry point")

    status, lines = dry_run(args.dry_run)
    print(os.linesep.join(lines))
    return 0 if status == "FUSION GEOMETRY DRY RUN VALID" else 1


if __name__ == "__main__":
    sys.exit(main())
