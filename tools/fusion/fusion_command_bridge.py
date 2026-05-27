#!/usr/bin/env python3
"""Fusion-side file command bridge for DraftMyVan manual verification.

The bridge intentionally supports only a read/report command today. It does not
execute arbitrary Python, does not create geometry, and does not generate CNC,
DXF, drawings, cut lists, or manufacturing-ready output.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COMMAND_FILE = Path("/tmp/draftmyvan_fusion_command.json")
DEFAULT_STATUS_FILE = Path("/tmp/draftmyvan_fusion_status.json")
BUILD_FUSION_DIR = REPO_ROOT / "build" / "fusion"
TMP_ROOT = Path("/tmp").resolve(strict=False)
SUPPORTED_COMMANDS = {"report_manual_verification_status"}
EXPECTED_COMPONENT_BODIES = {
    "Galley_LeftSide": "left_side_body",
    "Galley_RightSide": "right_side_body",
    "Galley_BottomPanel": "bottom_panel_body",
    "Galley_TopPanel": "top_panel_body",
    "Galley_BackPanel": "back_panel_body",
}
EXPECTED_USER_PARAMETERS = ("Width", "Depth", "Height", "PlyThickness")


class FusionCommandBridgeError(ValueError):
    """Raised when a Fusion command bridge request is unsupported or unsafe."""


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _resolve_path(value: str | Path) -> Path:
    raw = Path(value)
    path = raw if raw.is_absolute() else REPO_ROOT / raw
    return path.resolve(strict=False)


def _allowlisted_bridge_path(path: Path) -> bool:
    return (
        _is_relative_to(path, BUILD_FUSION_DIR)
        or path == _resolve_path(DEFAULT_COMMAND_FILE)
        or path == _resolve_path(DEFAULT_STATUS_FILE)
    )


def resolve_bridge_write_path(value: str | Path, *, kind: str) -> Path:
    path = _resolve_path(value)
    if path.suffix != ".json":
        raise FusionCommandBridgeError(f"{kind} must be a JSON file: {path}")
    if not _allowlisted_bridge_path(path):
        raise FusionCommandBridgeError(
            f"{kind} must be {DEFAULT_COMMAND_FILE}, {DEFAULT_STATUS_FILE}, or under {BUILD_FUSION_DIR}"
        )
    return path


def _resolve_optional_payload_path(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise FusionCommandBridgeError("payload_path must be a non-empty string when provided")
    path = _resolve_path(value.strip())
    if path.suffix != ".json":
        raise FusionCommandBridgeError("payload_path must be a JSON file")
    if not (
        _is_relative_to(path, REPO_ROOT)
        or (
            path.parent == TMP_ROOT
            and (
                path.name.startswith("galley_")
                and (path.name.endswith("_panels.json") or path.name.endswith("_fusion_parameters.json"))
            )
        )
    ):
        raise FusionCommandBridgeError(
            "payload_path must be under the DraftMyVan repo or an allowlisted galley JSON in /tmp"
        )
    return str(path)


def validate_command_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise FusionCommandBridgeError("command payload root must be an object")
    allowed = {"command", "payload_path", "status_path", "reviewer", "notes"}
    extra = sorted(set(payload) - allowed)
    if extra:
        raise FusionCommandBridgeError("unsupported command field(s): " + ", ".join(extra))

    command = payload.get("command")
    if command not in SUPPORTED_COMMANDS:
        raise FusionCommandBridgeError(f"unsupported command: {command}")

    normalized: dict[str, Any] = {"command": command}
    payload_path = _resolve_optional_payload_path(payload.get("payload_path"))
    if payload_path is not None:
        normalized["payload_path"] = payload_path

    status_path = payload.get("status_path") or str(DEFAULT_STATUS_FILE)
    normalized["status_path"] = str(resolve_bridge_write_path(status_path, kind="status_path"))

    for field in ("reviewer", "notes"):
        if field in payload:
            if not isinstance(payload[field], str):
                raise FusionCommandBridgeError(f"{field} must be a string")
            normalized[field] = payload[field]
    return normalized


def load_command_file(path: str | Path) -> dict[str, Any]:
    command_path = resolve_bridge_write_path(path, kind="command_path")
    try:
        with command_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except OSError as e:
        raise FusionCommandBridgeError(f"cannot read command file {command_path}: {e}") from e
    except json.JSONDecodeError as e:
        raise FusionCommandBridgeError(f"invalid JSON in command file {command_path}: {e}") from e
    return validate_command_payload(payload)


def write_command_file(payload: dict[str, Any], path: str | Path) -> Path:
    command_path = resolve_bridge_write_path(path, kind="command_path")
    normalized = validate_command_payload(payload)
    if _is_relative_to(command_path, BUILD_FUSION_DIR):
        command_path.parent.mkdir(parents=True, exist_ok=True)
    with command_path.open("w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2, sort_keys=True)
        f.write("\n")
    return command_path


def load_status_file(path: str | Path) -> dict[str, Any]:
    status_path = resolve_bridge_write_path(path, kind="status_path")
    try:
        with status_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except OSError as e:
        raise FusionCommandBridgeError(f"cannot read status file {status_path}: {e}") from e
    except json.JSONDecodeError as e:
        raise FusionCommandBridgeError(f"invalid JSON in status file {status_path}: {e}") from e
    if not isinstance(payload, dict):
        raise FusionCommandBridgeError("status file root must be an object")
    return payload


def _write_status_file(status: dict[str, Any], path: str | Path) -> Path:
    status_path = resolve_bridge_write_path(path, kind="status_path")
    if _is_relative_to(status_path, BUILD_FUSION_DIR):
        status_path.parent.mkdir(parents=True, exist_ok=True)
    with status_path.open("w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, sort_keys=True)
        f.write("\n")
    return status_path


def _fusion_modules() -> tuple[Any, Any, Any, Any]:
    import fusion_create_galley_v1 as geometry

    return geometry.require_fusion_modules()


def _fusion_message(message: str) -> None:
    try:
        import adsk.core  # type: ignore[import-not-found]

        app = adsk.core.Application.get()
        ui = app.userInterface if app else None
        if ui is not None:
            ui.messageBox(message)
    except Exception:
        return


def _component_body_status(root: Any) -> dict[str, Any]:
    found_components: dict[str, list[str]] = {}
    missing_components: list[str] = []
    missing_bodies: list[str] = []

    for component_name, body_name in EXPECTED_COMPONENT_BODIES.items():
        component = None
        for index in range(root.occurrences.count):
            occurrence = root.occurrences.item(index)
            if occurrence.component and occurrence.component.name == component_name:
                component = occurrence.component
                break
        if component is None:
            missing_components.append(component_name)
            missing_bodies.append(body_name)
            continue
        bodies = [
            component.bRepBodies.item(body_index).name
            for body_index in range(component.bRepBodies.count)
        ]
        found_components[component_name] = bodies
        if body_name not in bodies:
            missing_bodies.append(body_name)

    return {
        "expected_component_count": len(EXPECTED_COMPONENT_BODIES),
        "found_components": found_components,
        "missing_components": missing_components,
        "missing_bodies": missing_bodies,
        "component_names_match": not missing_components,
        "body_names_match": not missing_bodies,
    }


def report_manual_verification_status(command: dict[str, Any]) -> dict[str, Any]:
    normalized = validate_command_payload(command)
    base: dict[str, Any] = {
        "command": "report_manual_verification_status",
        "payload_path": normalized.get("payload_path"),
        "reviewer": normalized.get("reviewer"),
        "notes": normalized.get("notes"),
        "manufacturing_ready": False,
        "generated_outputs": {
            "drawings": False,
            "dxf": False,
            "cnc": False,
            "cut_lists": False,
        },
    }

    try:
        _core, _fusion, _app, design = _fusion_modules()
    except Exception as e:
        return {
            **base,
            "running_in_fusion": False,
            "status": "fusion_unavailable",
            "message": str(e),
        }

    root = design.rootComponent
    parameters = {}
    for name in EXPECTED_USER_PARAMETERS:
        parameter = design.userParameters.itemByName(name)
        parameters[name] = parameter.expression if parameter else None

    component_status = _component_body_status(root)
    return {
        **base,
        "running_in_fusion": True,
        "status": "manual_verification_reported",
        "user_parameters": parameters,
        "user_parameters_present": all(parameters.values()),
        **component_status,
        "manual_review_required": True,
    }


def execute_command_payload(command: dict[str, Any]) -> dict[str, Any]:
    normalized = validate_command_payload(command)
    if normalized["command"] == "report_manual_verification_status":
        return report_manual_verification_status(normalized)
    raise FusionCommandBridgeError(f"unsupported command: {normalized['command']}")


def run(context: Any) -> None:
    """Fusion 360 entry point for the file command bridge."""
    command_path = str(context or os.environ.get("DRAFTMYVAN_FUSION_COMMAND_FILE", DEFAULT_COMMAND_FILE))
    try:
        command = load_command_file(command_path)
        status = execute_command_payload(command)
        status_path = _write_status_file(status, command["status_path"])
        _fusion_message(
            "DraftMyVan Fusion command bridge wrote manual verification status:\n"
            f"{status_path}\n"
            "No geometry, drawings, cut lists, DXF, CNC, or manufacturing output was created."
        )
    except Exception as e:
        _fusion_message(f"DraftMyVan Fusion command bridge failed:\n{e}")
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a DraftMyVan Fusion file-command bridge request.",
    )
    parser.add_argument("--validate-command", type=Path, help="Validate an allowlisted command file.")
    args = parser.parse_args(argv)
    if not args.validate_command:
        parser.error("use --validate-command outside Fusion; run(context) is the Fusion entry point")

    try:
        command = load_command_file(args.validate_command)
    except FusionCommandBridgeError as e:
        print(f"[FAIL] {e}")
        print("RESULT: FUSION COMMAND BRIDGE COMMAND INVALID")
        return 1
    print(json.dumps(command, indent=2, sort_keys=True))
    print("RESULT: FUSION COMMAND BRIDGE COMMAND VALID")
    return 0


if __name__ == "__main__":
    sys.exit(main())
