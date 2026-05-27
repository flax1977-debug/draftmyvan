#!/usr/bin/env python3
"""Fusion 360 skeleton for consuming galley_v1 parameter payloads.

This module is intentionally importable in normal Python without Fusion 360 or
Autodesk `adsk` modules installed. It validates and summarizes the deterministic
dry-run payload only; it does not create geometry, drawings, cut lists, DXF, or
CNC output.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


EXPECTED_TEMPLATE = "galley_v1"
REQUIRED_PARAMETERS = ("Width", "Depth", "Height", "PlyThickness")


class FusionPayloadError(Exception):
    """Raised when a galley_v1 Fusion payload is invalid."""


def load_parameter_payload(path: str | Path) -> dict[str, Any]:
    """Load a galley_v1 parameter payload from JSON and validate its root type."""
    payload_path = Path(path)
    try:
        with payload_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except OSError as e:
        raise FusionPayloadError(f"cannot read {payload_path}: {e}") from e
    except json.JSONDecodeError as e:
        raise FusionPayloadError(f"invalid JSON in {payload_path}: {e}") from e
    if not isinstance(payload, dict):
        raise FusionPayloadError("payload root must be an object")
    return payload


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise FusionPayloadError(f"{key} must be a non-empty string")
    return value


def _required_positive_int(parameters: dict[str, Any], key: str) -> int:
    value = parameters.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise FusionPayloadError(f"parameters.{key} must be a positive integer millimetre value")
    if value <= 0:
        raise FusionPayloadError(f"parameters.{key} must be a positive integer millimetre value")
    return value


def validate_parameter_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a galley_v1 parameter payload.

    Returns the original payload on success so callers can use this as a guard
    before reading fields. Raises `FusionPayloadError` on failure.
    """
    if not isinstance(payload, dict):
        raise FusionPayloadError("payload root must be an object")

    template = _required_string(payload, "template")
    if template != EXPECTED_TEMPLATE:
        raise FusionPayloadError(f'template must be "{EXPECTED_TEMPLATE}"')
    _required_string(payload, "manifest_id")

    parameters = payload.get("parameters")
    if not isinstance(parameters, dict):
        raise FusionPayloadError("parameters must be an object")
    for name in REQUIRED_PARAMETERS:
        _required_positive_int(parameters, name)

    hardware = payload.get("hardware", [])
    if not isinstance(hardware, list) or not all(isinstance(item, str) for item in hardware):
        raise FusionPayloadError("hardware must be a list of strings when present")

    return payload


def parameter_summary(payload: dict[str, Any]) -> str:
    """Return a concise text summary for CLI output or Fusion UI logging."""
    validate_parameter_payload(payload)
    parameters = payload["parameters"]
    hardware = payload.get("hardware", [])
    lines = [
        f"template: {payload['template']}",
        f"manifest_id: {payload['manifest_id']}",
        f"Width: {parameters['Width']}",
        f"Depth: {parameters['Depth']}",
        f"Height: {parameters['Height']}",
        f"PlyThickness: {parameters['PlyThickness']}",
        f"hardware_count: {len(hardware)}",
    ]
    return os.linesep.join(lines)


def _fusion_message_box(message: str) -> None:
    """Show a message in Fusion 360.

    The Autodesk import stays inside this function so normal Python tests can
    import this module without Fusion installed.
    """
    import adsk.core  # type: ignore[import-not-found]

    app = adsk.core.Application.get()
    ui = app.userInterface if app else None
    if ui is not None:
        ui.messageBox(message)


def run(context: Any) -> None:
    """Fusion 360 script entry point.

    This is a skeleton only. When run inside Fusion later, pass a JSON payload
    path as `context` or through the `DRAFTMYVAN_FUSION_PAYLOAD` environment
    variable. The script validates and logs the summary; it does not create
    geometry yet.
    """
    payload_path = str(context or os.environ.get("DRAFTMYVAN_FUSION_PAYLOAD", "")).strip()
    if not payload_path:
        _fusion_message_box(
            "DraftMyVan galley_v1 skeleton loaded. "
            "No parameter payload path was supplied; no geometry was created."
        )
        return

    payload = load_parameter_payload(payload_path)
    summary = parameter_summary(payload)
    _fusion_message_box(
        "DraftMyVan galley_v1 payload accepted.\n"
        f"{summary}\n"
        "No geometry, drawings, cut lists, DXF, or CNC output were created."
    )
