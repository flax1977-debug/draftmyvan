# DraftMyVan Fusion 360 galley creator — CANONICAL Fusion runtime script.
#
# This file is the canonical source for the body-creating Fusion 360 script.
# It is self-contained (imports adsk.* at top level) and is meant to be run
# inside Fusion 360, not imported in CI. Deploy it by copying this folder to:
#   ~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/
#       fusion_create_galley_v1/fusion_create_galley_v1.py
#
# It creates 5 verification-only root bodies (Galley_LeftSide, Galley_RightSide,
# Galley_BottomPanel, Galley_TopPanel, Galley_BackPanel) from transient BRep
# boxes committed into a "DraftMyVan Galley" BaseFeature (required in parametric
# designs). Reads /tmp/galley_1000_panels.json by default
# (override via DRAFTMYVAN_FUSION_PANEL_PAYLOAD).
#
# NOTE: tools/fusion/fusion_create_galley_v1.py is a DIFFERENT, CI-importable
# dry-run / geometry-plan VALIDATION module (component + sketch/extrude plan,
# *_body naming). It is not a duplicate of this runtime script. See
# docs/current_status.md for the runtime-vs-planning split.

import json
import os
import traceback

import adsk.core
import adsk.fusion

PAYLOAD_PATH = "/tmp/galley_1000_panels.json"
ERROR_PATH = "/tmp/draftmyvan_fusion_last_error.txt"

EXPECTED_PANEL_ORDER = [
    "left_side",
    "right_side",
    "bottom_panel",
    "top_panel",
    "back_panel",
]

BODY_DISPLAY_NAMES = {
    "left_side": "Galley_LeftSide",
    "right_side": "Galley_RightSide",
    "bottom_panel": "Galley_BottomPanel",
    "top_panel": "Galley_TopPanel",
    "back_panel": "Galley_BackPanel",
}


def _mm_to_cm(value):
    return float(value) / 10.0


def _app_ui():
    app = adsk.core.Application.get()
    ui = app.userInterface if app else None
    return app, ui


def _show(message):
    _app, ui = _app_ui()
    if ui:
        ui.messageBox(message)


def _write_error(text):
    try:
        with open(ERROR_PATH, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        pass


def _positive_number(value, label):
    if isinstance(value, bool):
        raise ValueError(label + " must be a positive number")
    try:
        number = float(value)
    except Exception as exc:
        raise ValueError(label + " must be a positive number") from exc
    if number <= 0:
        raise ValueError(label + " must be a positive number")
    return number


def _compute_panels_from_parameters(payload):
    params = payload.get("parameters")
    if not isinstance(params, dict):
        raise ValueError("Payload has no 'panels' list and no 'parameters' object")

    width = _positive_number(params.get("Width"), "parameters.Width")
    depth = _positive_number(params.get("Depth"), "parameters.Depth")
    height = _positive_number(params.get("Height"), "parameters.Height")
    thickness = _positive_number(params.get("PlyThickness"), "parameters.PlyThickness")

    if width <= 2 * thickness:
        raise ValueError("Width must be greater than 2 * PlyThickness")
    if height <= 2 * thickness:
        raise ValueError("Height must be greater than 2 * PlyThickness")

    internal_width = width - 2 * thickness
    internal_height = height - 2 * thickness
    return [
        {"name": "left_side", "length_mm": height, "width_mm": depth, "thickness_mm": thickness},
        {"name": "right_side", "length_mm": height, "width_mm": depth, "thickness_mm": thickness},
        {"name": "bottom_panel", "length_mm": internal_width, "width_mm": depth, "thickness_mm": thickness},
        {"name": "top_panel", "length_mm": internal_width, "width_mm": depth, "thickness_mm": thickness},
        {"name": "back_panel", "length_mm": internal_width, "width_mm": internal_height, "thickness_mm": thickness},
    ]


def _load_panels(path):
    if not os.path.exists(path):
        raise FileNotFoundError("Panel payload not found: " + path)

    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    panels = payload.get("panels")
    if panels is None:
        panels = _compute_panels_from_parameters(payload)

    if not isinstance(panels, list) or not panels:
        raise ValueError("payload.panels must be a non-empty list")

    by_name = {}
    for panel in panels:
        if not isinstance(panel, dict):
            raise ValueError("Every panel must be an object")
        name = panel.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("Every panel needs a name")
        by_name[name] = panel
        _positive_number(panel.get("length_mm"), name + ".length_mm")
        _positive_number(panel.get("width_mm"), name + ".width_mm")
        _positive_number(panel.get("thickness_mm"), name + ".thickness_mm")

    missing = [name for name in EXPECTED_PANEL_ORDER if name not in by_name]
    if missing:
        raise ValueError("Missing required panels: " + ", ".join(missing))

    ordered = [by_name[name] for name in EXPECTED_PANEL_ORDER]
    return payload, ordered


def _infer_dimensions(panels):
    by_name = {panel["name"]: panel for panel in panels}
    left = by_name["left_side"]
    bottom = by_name["bottom_panel"]
    thickness = _positive_number(left["thickness_mm"], "left_side.thickness_mm")
    width = _positive_number(bottom["length_mm"], "bottom_panel.length_mm") + 2 * thickness
    depth = _positive_number(left["width_mm"], "left_side.width_mm")
    height = _positive_number(left["length_mm"], "left_side.length_mm")
    return width, depth, height, thickness


def _set_user_parameter(design, name, value_mm):
    expr = ("%.6g mm" % float(value_mm))
    existing = design.userParameters.itemByName(name)
    if existing:
        existing.expression = expr
        return
    value_input = adsk.core.ValueInput.createByString(expr)
    design.userParameters.add(name, value_input, "mm", "DraftMyVan galley verification")


def _delete_existing_galley(root):
    """Delete previous DraftMyVan galley geometry and its owning base feature(s).

    In parametric Fusion designs the generated bodies are owned by a BaseFeature,
    so deleting only the visible Galley_* result bodies leaves empty timeline
    base features behind. Delete the owning base feature first (which removes the
    bodies it created), then clean up any remaining orphan Galley_* bodies and
    legacy Galley_* component occurrences as fallbacks for old or direct-mode
    designs. Collect failures and raise once at the end; run() writes the full
    traceback to ERROR_PATH.
    """
    errors = []

    # Delete old DraftMyVan base features first. Iterate backwards because
    # deletion mutates the collection.
    try:
        base_features = root.features.baseFeatures
        for index in range(base_features.count - 1, -1, -1):
            base_feat = base_features.item(index)
            if base_feat is None:
                continue
            try:
                if not base_feat.isValid:
                    continue
                name = base_feat.name or ""
                if name.startswith("DraftMyVan Galley"):
                    if base_feat.deleteMe() is False:
                        errors.append("BaseFeature delete returned False for " + repr(name))
            except Exception as exc:
                errors.append("BaseFeature cleanup failed: " + str(exc))
    except Exception as exc:
        errors.append("Scanning base features failed: " + str(exc))

    # Fallback: remove orphan Galley_* bodies from older or direct-mode runs.
    try:
        bodies = root.bRepBodies
        for index in range(bodies.count - 1, -1, -1):
            body = bodies.item(index)
            if body is None:
                continue
            try:
                if not body.isValid:
                    continue
                name = body.name or ""
                if name.startswith("Galley_"):
                    if body.deleteMe() is False:
                        errors.append("Body delete returned False for " + repr(name))
            except Exception as exc:
                errors.append("Body cleanup failed: " + str(exc))
    except Exception as exc:
        errors.append("Scanning BRep bodies failed: " + str(exc))

    # Fallback: remove legacy Galley_* component occurrences from older versions.
    try:
        occurrences = root.occurrences
        for index in range(occurrences.count - 1, -1, -1):
            occ = occurrences.item(index)
            if occ is None:
                continue
            try:
                if not occ.isValid:
                    continue
                comp = occ.component
                comp_name = (comp.name if comp else "") or ""
                if comp_name.startswith("Galley_"):
                    if occ.deleteMe() is False:
                        errors.append("Occurrence delete returned False for " + repr(comp_name))
            except Exception as exc:
                errors.append("Occurrence cleanup failed: " + str(exc))
    except Exception as exc:
        errors.append("Scanning occurrences failed: " + str(exc))

    if errors:
        raise RuntimeError(
            "Failed to delete old DraftMyVan galley objects: " + "; ".join(errors)
        )


def _add_box(root, name, center_mm, size_mm, target_base_feature=None):
    center = adsk.core.Point3D.create(
        _mm_to_cm(center_mm[0]),
        _mm_to_cm(center_mm[1]),
        _mm_to_cm(center_mm[2]),
    )
    x_dir = adsk.core.Vector3D.create(1, 0, 0)
    y_dir = adsk.core.Vector3D.create(0, 1, 0)
    box = adsk.core.OrientedBoundingBox3D.create(
        center,
        x_dir,
        y_dir,
        _mm_to_cm(size_mm[0]),
        _mm_to_cm(size_mm[1]),
        _mm_to_cm(size_mm[2]),
    )
    temp_mgr = adsk.fusion.TemporaryBRepManager.get()
    temp_body = temp_mgr.createBox(box)
    # In a parametric design BRepBodies.add requires a base feature that is
    # currently being edited (startEdit). Direct designs accept a bare body.
    if target_base_feature is not None:
        body = root.bRepBodies.add(temp_body, target_base_feature)
    else:
        body = root.bRepBodies.add(temp_body)
    body.name = name
    return body


def _create_galley(root, panels):
    width, depth, height, thickness = _infer_dimensions(panels)
    internal_width = width - 2 * thickness
    internal_height = height - 2 * thickness

    # Parametric designs require a BaseFeature (in edit mode) to host bodies
    # added from transient BRep. Direct-modeling designs do not, so only create
    # one when needed.
    design = root.parentDesign
    is_parametric = (
        design is not None
        and design.designType == adsk.fusion.DesignTypes.ParametricDesignType
    )

    base_feat = None
    if is_parametric:
        base_feat = root.features.baseFeatures.add()
        base_feat.name = "DraftMyVan Galley"
        base_feat.startEdit()

    body_names = []
    try:
        body_names.append(_add_box(
            root,
            BODY_DISPLAY_NAMES["left_side"],
            [thickness / 2, depth / 2, height / 2],
            [thickness, depth, height],
            base_feat,
        ).name)
        body_names.append(_add_box(
            root,
            BODY_DISPLAY_NAMES["right_side"],
            [width - thickness / 2, depth / 2, height / 2],
            [thickness, depth, height],
            base_feat,
        ).name)
        body_names.append(_add_box(
            root,
            BODY_DISPLAY_NAMES["bottom_panel"],
            [width / 2, depth / 2, thickness / 2],
            [internal_width, depth, thickness],
            base_feat,
        ).name)
        body_names.append(_add_box(
            root,
            BODY_DISPLAY_NAMES["top_panel"],
            [width / 2, depth / 2, height - thickness / 2],
            [internal_width, depth, thickness],
            base_feat,
        ).name)
        body_names.append(_add_box(
            root,
            BODY_DISPLAY_NAMES["back_panel"],
            [width / 2, thickness / 2, height / 2],
            [internal_width, thickness, internal_height],
            base_feat,
        ).name)
    finally:
        if base_feat is not None:
            base_feat.finishEdit()

    return {
        "Width": width,
        "Depth": depth,
        "Height": height,
        "PlyThickness": thickness,
        "bodies": body_names,
    }


def run(context):
    app, ui = _app_ui()
    try:
        if app is None or app.activeProduct is None:
            raise RuntimeError("Fusion app/activeProduct is not available")

        design = adsk.fusion.Design.cast(app.activeProduct)
        if design is None:
            raise RuntimeError("Active product is not a Fusion Design")

        payload_path = os.environ.get("DRAFTMYVAN_FUSION_PANEL_PAYLOAD", PAYLOAD_PATH)
        payload, panels = _load_panels(payload_path)
        root = design.rootComponent

        _delete_existing_galley(root)

        dims = _create_galley(root, panels)
        _set_user_parameter(design, "Width", dims["Width"])
        _set_user_parameter(design, "Depth", dims["Depth"])
        _set_user_parameter(design, "Height", dims["Height"])
        _set_user_parameter(design, "PlyThickness", dims["PlyThickness"])

        # Fit view so the result is visible immediately.
        try:
            viewport = app.activeViewport
            if viewport:
                viewport.fit()
        except Exception:
            pass

        manifest_id = payload.get("manifest_id", "unknown manifest") if isinstance(payload, dict) else "unknown manifest"
        _show(
            "DraftMyVan galley created.\n\n"
            "Payload: " + payload_path + "\n"
            "Manifest: " + str(manifest_id) + "\n\n"
            "Bodies:\n- " + "\n- ".join(dims["bodies"]) + "\n\n"
            "Dimensions:\n"
            "Width: %.1f mm\nDepth: %.1f mm\nHeight: %.1f mm\nPly: %.1f mm\n\n"
            "Verification geometry only. No DXF, CNC, drawings, kerf, dados, edging, hardware drilling, or manufacturing sign-off."
            % (dims["Width"], dims["Depth"], dims["Height"], dims["PlyThickness"])
        )

    except Exception:
        details = traceback.format_exc()
        _write_error(details)
        _show(
            "DraftMyVan galley failed.\n\n"
            "I wrote the full error to:\n" + ERROR_PATH + "\n\n"
            "Error preview:\n" + details[-1400:]
        )
        raise
