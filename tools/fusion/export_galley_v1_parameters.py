#!/usr/bin/env python3
"""Export a deterministic galley_v1 Fusion parameter dry-run JSON.

This script writes review/planning data only. It does not call Fusion 360,
generate drawings, or emit CNC/DXF files.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import validate_fusion_parameter_map as validator


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MANIFEST = REPO_ROOT / "examples" / "galley_1000.json"
DEFAULT_MAP = REPO_ROOT / "tools" / "fusion" / "galley_v1_parameter_map.json"
DEFAULT_OUT = REPO_ROOT / "build" / "fusion" / "galley_1000_fusion_parameters.json"
GENERATED_BY = "tools/fusion/export_galley_v1_parameters.py"


class FusionParameterExportError(Exception):
    """Raised when the dry-run export cannot be generated."""


def _repo_relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        raise FusionParameterExportError(f"cannot read {path}: {e}") from e
    except json.JSONDecodeError as e:
        raise FusionParameterExportError(f"invalid JSON in {path}: {e}") from e


def build_payload(manifest_path: Path, map_path: Path, root: Path = REPO_ROOT) -> dict[str, Any]:
    status, lines = validator.validate_fusion_parameter_map(map_path, root)
    if status != validator.STATUS_VALID:
        raise FusionParameterExportError("; ".join(lines))

    manifest = _read_json(manifest_path)
    mapping = _read_json(map_path)
    if not isinstance(manifest, dict) or not isinstance(mapping, dict):
        raise FusionParameterExportError("manifest and parameter map must be JSON objects")

    template = validator.manifest_value(manifest, validator.required_str(mapping, "template_source"))
    if template != validator.EXPECTED_TEMPLATE:
        raise FusionParameterExportError(f"manifest does not select {validator.EXPECTED_TEMPLATE}")

    parameters = {
        name: validator.require_integer_mm(
            validator.manifest_value(manifest, spec["source"]),
            spec["source"],
        )
        for name, spec in mapping["parameters"].items()
    }
    hardware = validator.manifest_value(manifest, mapping["hardware"]["source"])
    if not isinstance(hardware, list) or not all(isinstance(item, str) for item in hardware):
        raise FusionParameterExportError("hardware must be a list of strings")

    return {
        "template": template,
        "manifest_id": validator.manifest_value(manifest, mapping["metadata"]["manifest_id"]["source"]),
        "source_manifest": _repo_relative(root, manifest_path),
        "generated_by": GENERATED_BY,
        "parameters": parameters,
        "hardware": hardware,
        "ignored_fields": mapping["ignored_fields"],
    }


def export_parameters(manifest_path: Path, map_path: Path, out_path: Path, root: Path = REPO_ROOT) -> None:
    payload = build_payload(manifest_path, map_path, root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export galley_v1 Fusion parameter dry-run JSON.",
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)

    root = args.root.resolve()
    manifest_path = args.manifest if args.manifest.is_absolute() else root / args.manifest
    map_path = args.map if args.map.is_absolute() else root / args.map
    out_path = args.out if args.out.is_absolute() else root / args.out
    try:
        export_parameters(manifest_path, map_path, out_path, root)
    except FusionParameterExportError as e:
        sys.stderr.write(f"ERROR: {e}\n")
        return 1
    print(f"WROTE {out_path}")
    print("RESULT: FUSION PARAMETER EXPORT READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
