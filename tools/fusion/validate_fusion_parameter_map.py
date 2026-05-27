#!/usr/bin/env python3
"""Validate the galley_v1 manifest-to-Fusion parameter map.

This is a pure-Python planning gate. It validates dry-run parameter
consumption only; it does not call Fusion 360, generate drawings, or emit CNC
files.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MAP = REPO_ROOT / "tools" / "fusion" / "galley_v1_parameter_map.json"
EXPECTED_TEMPLATE = "galley_v1"
REQUIRED_PARAMETERS = {
    "Width": "dimensions_mm.width",
    "Depth": "dimensions_mm.depth",
    "Height": "dimensions_mm.height",
    "PlyThickness": "manufacturing.plywood_thickness_mm",
}
REQUIRED_IGNORED_FIELDS = (
    "visual.glb_path",
    "visual.material_slots",
    "visual.collision_proxy",
    "anchor",
    "placement",
    "clearances",
    "rules.service_access",
)
STATUS_VALID = "FUSION PARAMETER MAP VALID"
STATUS_INVALID = "FUSION PARAMETER MAP INVALID"


class FusionParameterMapError(Exception):
    """Raised when the Fusion parameter map is invalid."""


def read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        raise FusionParameterMapError(f"cannot read {path}: {e}") from e
    except json.JSONDecodeError as e:
        raise FusionParameterMapError(f"invalid JSON in {path}: {e}") from e


def required_str(data: dict[str, Any], key: str, label: str | None = None) -> str:
    value = data.get(key)
    name = label or key
    if not isinstance(value, str) or not value.strip():
        raise FusionParameterMapError(f"{name} must be a non-empty string")
    return value


def repo_relative_path(root: Path, value: str, key: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise FusionParameterMapError(f"{key} must be a repository-relative path")
    return (root / path).resolve()


def normalize_manifest_path(path: str) -> str:
    return path.removeprefix("manifest.")


def manifest_value(manifest: dict[str, Any], source: str) -> Any:
    current: Any = manifest
    for part in normalize_manifest_path(source).split("."):
        if not isinstance(current, dict) or part not in current:
            raise FusionParameterMapError(f"manifest field not found: {source}")
        current = current[part]
    return current


def require_integer_mm(value: Any, source: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise FusionParameterMapError(f"{source} must resolve to an integer millimetre value")
    if value <= 0:
        raise FusionParameterMapError(f"{source} must resolve to a positive millimetre value")
    return value


def _mapping_source(mapping: dict[str, Any], key: str, label: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise FusionParameterMapError(f"{label}.{key} must be an object")
    return required_str(value, "source", f"{label}.{key}.source")


def _validate_parameter_names(parameters: dict[str, Any]) -> None:
    for name, spec in parameters.items():
        if not isinstance(name, str) or not name.strip():
            raise FusionParameterMapError("parameter names must be non-empty strings")
        if not isinstance(spec, dict):
            raise FusionParameterMapError(f"parameters.{name} must be an object")
        required_str(spec, "source", f"parameters.{name}.source")
        required_str(spec, "type", f"parameters.{name}.type")


def _collect_consumed_sources(mapping: dict[str, Any]) -> list[str]:
    consumed = [required_str(mapping, "template_source")]
    metadata = mapping.get("metadata")
    if isinstance(metadata, dict):
        for name in metadata:
            consumed.append(_mapping_source(metadata, name, "metadata"))
    parameters = mapping.get("parameters")
    if isinstance(parameters, dict):
        for name in parameters:
            consumed.append(_mapping_source(parameters, name, "parameters"))
    hardware = mapping.get("hardware")
    if isinstance(hardware, dict):
        consumed.append(required_str(hardware, "source", "hardware.source"))
    return [normalize_manifest_path(source) for source in consumed]


def _validate_no_visual_consumption(mapping: dict[str, Any]) -> None:
    consumed_visual = [source for source in _collect_consumed_sources(mapping) if source.startswith("visual.")]
    if consumed_visual:
        raise FusionParameterMapError(
            "visual fields must not be consumed as Fusion parameters: "
            + ", ".join(sorted(consumed_visual))
        )


def _validate_ignored_fields(mapping: dict[str, Any]) -> None:
    ignored = mapping.get("ignored_fields")
    if isinstance(ignored, str):
        raise FusionParameterMapError("ignored_fields must be a list, not a string")
    if not isinstance(ignored, list):
        raise FusionParameterMapError("ignored_fields must be a list")
    if not all(isinstance(item, str) and item.strip() for item in ignored):
        raise FusionParameterMapError("ignored_fields items must be non-empty strings")
    missing = [field for field in REQUIRED_IGNORED_FIELDS if field not in ignored]
    if missing:
        raise FusionParameterMapError("ignored_fields is missing: " + ", ".join(missing))


def validate_fusion_parameter_map(
    map_path: Path = DEFAULT_MAP,
    root: Path = REPO_ROOT,
) -> tuple[str, list[str]]:
    """Validate a Fusion parameter map."""
    root = root.resolve()
    map_path = map_path.resolve()
    lines: list[str] = []

    try:
        mapping = read_json(map_path)
        if not isinstance(mapping, dict):
            raise FusionParameterMapError("parameter map root must be an object")
        lines.append(f"[OK] parameter map readable: {map_path}")

        manifest_rel = required_str(mapping, "source_manifest")
        manifest_path = repo_relative_path(root, manifest_rel, "source_manifest")
        if not manifest_path.is_file():
            raise FusionParameterMapError(f"referenced manifest does not exist: {manifest_path}")
        manifest = read_json(manifest_path)
        if not isinstance(manifest, dict):
            raise FusionParameterMapError("referenced manifest root must be an object")
        lines.append(f"[OK] referenced manifest exists: {manifest_path.relative_to(root)}")

        if required_str(mapping, "template") != EXPECTED_TEMPLATE:
            raise FusionParameterMapError(f'template must be "{EXPECTED_TEMPLATE}"')
        template_source = required_str(mapping, "template_source")
        template_value = manifest_value(manifest, template_source)
        if template_value != EXPECTED_TEMPLATE:
            raise FusionParameterMapError(
                f'manifest manufacturing.fusion_template must be "{EXPECTED_TEMPLATE}"'
            )
        lines.append(f"[OK] manifest selects template: {EXPECTED_TEMPLATE}")

        metadata = mapping.get("metadata")
        if not isinstance(metadata, dict):
            raise FusionParameterMapError("metadata must be an object")
        manifest_id_source = _mapping_source(metadata, "manifest_id", "metadata")
        if manifest_id_source != "manifest.id":
            raise FusionParameterMapError('metadata.manifest_id.source must be "manifest.id"')
        if not isinstance(manifest_value(manifest, manifest_id_source), str):
            raise FusionParameterMapError("manifest.id must resolve to a string")
        lines.append("[OK] manifest.id maps to manifest_id")

        parameters = mapping.get("parameters")
        if not isinstance(parameters, dict):
            raise FusionParameterMapError("parameters must be an object")
        _validate_parameter_names(parameters)
        for param_name, expected_source in REQUIRED_PARAMETERS.items():
            if param_name not in parameters:
                raise FusionParameterMapError(f"required Fusion parameter missing: {param_name}")
            actual_source = required_str(
                parameters[param_name],
                "source",
                f"parameters.{param_name}.source",
            )
            if actual_source != expected_source:
                raise FusionParameterMapError(
                    f"parameters.{param_name}.source must be {expected_source!r}"
                )
            require_integer_mm(manifest_value(manifest, actual_source), actual_source)
        lines.append("[OK] required Fusion parameters map to integer millimetre values")

        hardware = mapping.get("hardware")
        if not isinstance(hardware, dict):
            raise FusionParameterMapError("hardware must be an object")
        if required_str(hardware, "source", "hardware.source") != "manufacturing.hardware":
            raise FusionParameterMapError('hardware.source must be "manufacturing.hardware"')
        hardware_value = manifest_value(manifest, "manufacturing.hardware")
        if not isinstance(hardware_value, list) or not all(isinstance(item, str) for item in hardware_value):
            raise FusionParameterMapError("manufacturing.hardware must resolve to a list of strings")
        lines.append("[OK] manufacturing.hardware maps to hardware")

        _validate_ignored_fields(mapping)
        _validate_no_visual_consumption(mapping)
        lines.append("[OK] ignored/deferred fields are explicit and visual fields are not consumed")

        lines.append(f"RESULT: {STATUS_VALID}")
        return STATUS_VALID, lines

    except FusionParameterMapError as e:
        lines.append(f"[FAIL] {e}")
        lines.append(f"RESULT: {STATUS_INVALID}")
        return STATUS_INVALID, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate DraftMyVan Fusion parameter mapping metadata.",
    )
    parser.add_argument(
        "map",
        nargs="?",
        type=Path,
        default=DEFAULT_MAP,
        help="Fusion parameter map JSON.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root (default: inferred from this script).",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    map_path = args.map if args.map.is_absolute() else root / args.map
    status, lines = validate_fusion_parameter_map(map_path, root)
    print(os.linesep.join(lines))
    return 0 if status == STATUS_VALID else 1


if __name__ == "__main__":
    sys.exit(main())
