#!/usr/bin/env python3
"""Validate per-asset acceptance metadata.

This is a small guard for the fixture-swap boundary. The manifest asset
may eventually become real cabinet art, but the swap must be explicit:
the metadata must still point at a valid manifest, a valid asset, the
permanent golden generated fixture, and the full validator gate list.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_METADATA = REPO_ROOT / "examples" / "assets" / "galley_1000.asset_acceptance.json"

REQUIRED_CHECKS = frozenset(
    (
        "schema",
        "dimensions",
        "floor_back_left_anchor",
        "material_slots",
        "collision_proxy",
    )
)


class AcceptanceError(Exception):
    """Raised when metadata or referenced files are malformed."""


def _read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        raise AcceptanceError(f"cannot read {path}: {e}") from e
    except json.JSONDecodeError as e:
        raise AcceptanceError(f"invalid JSON in {path}: {e}") from e


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AcceptanceError(f"{key} must be a non-empty string")
    return value


def _repo_relative_path(root: Path, value: str, key: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise AcceptanceError(f"{key} must be a repository-relative path")
    return (root / path).resolve()


def _resolved_repo_path(root: Path, data: dict[str, Any], key: str) -> Path:
    return _repo_relative_path(root, _required_str(data, key), key)


def _ensure_exists(path: Path, label: str) -> None:
    if not path.is_file():
        raise AcceptanceError(f"{label} does not exist: {path}")


def _validate_required_checks(data: dict[str, Any]) -> None:
    checks = data.get("required_checks")
    if not isinstance(checks, list) or not all(isinstance(c, str) for c in checks):
        raise AcceptanceError("required_checks must be a list of strings")
    missing = sorted(REQUIRED_CHECKS.difference(checks))
    if missing:
        raise AcceptanceError(
            "required_checks is missing: " + ", ".join(missing)
        )


def _validate_signoff(data: dict[str, Any], asset_kind: str) -> None:
    signoff = data.get("human_signoff")
    if not isinstance(signoff, dict):
        raise AcceptanceError("human_signoff must be an object")
    notes = signoff.get("notes")
    if not isinstance(notes, str) or not notes.strip():
        raise AcceptanceError("human_signoff.notes must explain the acceptance state")

    if asset_kind == "generated_contract_fixture":
        if data.get("generated_fixture_replaced") is not False:
            raise AcceptanceError(
                "generated_fixture_replaced must be false for generated contract fixtures"
            )
        if signoff.get("visual_reviewed") is not False:
            raise AcceptanceError("human_signoff.visual_reviewed must be false for fixtures")
        if signoff.get("production_art") is not False:
            raise AcceptanceError("human_signoff.production_art must be false for fixtures")
        if signoff.get("reviewer") is not None:
            raise AcceptanceError("human_signoff.reviewer must be null until real art is reviewed")
        return

    if asset_kind == "real_asset":
        if data.get("generated_fixture_replaced") is not True:
            raise AcceptanceError("generated_fixture_replaced must be true for real assets")
        if signoff.get("visual_reviewed") is not True:
            raise AcceptanceError("human_signoff.visual_reviewed must be true for real assets")
        if signoff.get("production_art") is not True:
            raise AcceptanceError("human_signoff.production_art must be true for real assets")
        reviewer = signoff.get("reviewer")
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise AcceptanceError("human_signoff.reviewer must name the real-art reviewer")
        return

    raise AcceptanceError(
        "asset_kind must be 'generated_contract_fixture' or 'real_asset'"
    )


def validate_metadata(
    metadata_path: Path = DEFAULT_METADATA,
    root: Path = REPO_ROOT,
) -> tuple[bool, list[str]]:
    """Validate one metadata file. Returns (ok, report_lines)."""
    root = root.resolve()
    metadata_path = metadata_path.resolve()
    lines: list[str] = []

    try:
        data = _read_json(metadata_path)
        if not isinstance(data, dict):
            raise AcceptanceError("metadata root must be an object")
        lines.append(f"[OK] metadata readable: {metadata_path}")

        manifest_path = _resolved_repo_path(root, data, "manifest_path")
        asset_path = _resolved_repo_path(root, data, "asset_path")
        golden_fixture_path = _resolved_repo_path(root, data, "golden_fixture_path")
        _ensure_exists(manifest_path, "manifest")
        _ensure_exists(asset_path, "asset")
        _ensure_exists(golden_fixture_path, "golden fixture")
        lines.append(f"[OK] manifest exists: {manifest_path.relative_to(root)}")
        lines.append(f"[OK] asset exists: {asset_path.relative_to(root)}")
        lines.append(f"[OK] golden fixture exists: {golden_fixture_path.relative_to(root)}")

        manifest = _read_json(manifest_path)
        if not isinstance(manifest, dict):
            raise AcceptanceError("referenced manifest root must be an object")
        manifest_id = _required_str(data, "manifest_id")
        if manifest.get("id") != manifest_id:
            raise AcceptanceError(
                f"manifest_id {manifest_id!r} does not match manifest id {manifest.get('id')!r}"
            )
        lines.append(f"[OK] manifest_id matches: {manifest_id}")

        visual = manifest.get("visual")
        if not isinstance(visual, dict):
            raise AcceptanceError("referenced manifest has no visual object")
        visual_glb_path = visual.get("glb_path")
        if not isinstance(visual_glb_path, str) or not visual_glb_path:
            raise AcceptanceError("referenced manifest has no visual.glb_path")
        expected_asset = (manifest_path.parent / visual_glb_path).resolve()
        if expected_asset != asset_path:
            raise AcceptanceError(
                f"asset_path must match manifest visual.glb_path: "
                f"{asset_path.relative_to(root)} != {expected_asset.relative_to(root)}"
            )
        lines.append("[OK] asset_path matches manifest visual.glb_path")

        if not _required_str(data, "validator_command"):
            raise AcceptanceError("validator_command must be present")
        lines.append("[OK] validator_command present")

        _validate_required_checks(data)
        lines.append("[OK] required_checks includes full current gate list")

        asset_kind = _required_str(data, "asset_kind")
        _validate_signoff(data, asset_kind)
        lines.append(f"[OK] acceptance state is internally consistent: {asset_kind}")

        if asset_kind == "generated_contract_fixture":
            if asset_path.read_bytes() != golden_fixture_path.read_bytes():
                raise AcceptanceError(
                    "generated fixture metadata says the manifest asset is still "
                    "the generated fixture, but its bytes differ from the golden fixture"
                )
            lines.append("[OK] current manifest asset matches golden generated fixture bytes")

    except AcceptanceError as e:
        lines.append(f"[FAIL] {e}")
        lines.append("RESULT: ASSET ACCEPTANCE INVALID")
        return False, lines

    lines.append("RESULT: ASSET ACCEPTANCE VALID")
    return True, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate DraftMyVan asset acceptance metadata.",
    )
    parser.add_argument(
        "metadata",
        nargs="?",
        type=Path,
        default=DEFAULT_METADATA,
        help="Acceptance metadata JSON (default: examples/assets/galley_1000.asset_acceptance.json).",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root (default: inferred from this script).",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    metadata_path = args.metadata if args.metadata.is_absolute() else root / args.metadata
    ok, lines = validate_metadata(metadata_path, root)
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
