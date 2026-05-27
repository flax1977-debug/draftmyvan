#!/usr/bin/env python3
"""Validate DraftMyVan asset-acceptance metadata.

Acceptance metadata records whether the manifest asset at
`examples/assets/<asset>.glb` is still the generated contract fixture or has
been replaced by signed-off production art. This validator intentionally lives
outside the manifest schema: it is release/process metadata for a concrete GLB,
not module data consumed by downstream runtime code.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_GLOB = "examples/assets/*.asset_acceptance.json"

REQUIRED_CHECKS = frozenset(
    (
        "schema",
        "dimensions",
        "floor_back_left_anchor",
        "material_slots",
        "collision_proxy",
    )
)

CURRENT_ASSET_KIND = "generated_contract_fixture"


class AcceptanceLoadError(Exception):
    """Acceptance metadata could not be read as JSON."""


def load_json(path: Path) -> Any:
    if not path.is_file():
        raise AcceptanceLoadError(f"file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise AcceptanceLoadError(f"invalid JSON: {e}") from e


def _repo_relative_path(
    data: dict[str, Any],
    field: str,
    root: Path,
    errors: list[str],
) -> Path | None:
    value = data.get(field)
    if not isinstance(value, str) or not value:
        errors.append(f"{field} must be a non-empty repo-relative path")
        return None

    rel = Path(value)
    if rel.is_absolute():
        errors.append(f"{field} must be repo-relative, got absolute path: {value}")
        return None

    root_resolved = root.resolve()
    resolved = (root / rel).resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError:
        errors.append(f"{field} escapes the repository root: {value}")
        return None
    return resolved


def _manifest_asset_path(manifest_path: Path, manifest: dict[str, Any]) -> Path | None:
    visual = manifest.get("visual")
    if not isinstance(visual, dict):
        return None
    glb_path = visual.get("glb_path")
    if not isinstance(glb_path, str) or not glb_path:
        return None
    return (manifest_path.parent / glb_path).resolve()


def validate_metadata(data: Any, *, root: Path = REPO_ROOT) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["metadata root must be a JSON object"]

    manifest_id = data.get("manifest_id")
    if not isinstance(manifest_id, str) or not manifest_id:
        errors.append("manifest_id must be a non-empty string")

    manifest_path = _repo_relative_path(data, "manifest_path", root, errors)
    asset_path = _repo_relative_path(data, "asset_path", root, errors)

    manifest: dict[str, Any] | None = None
    if manifest_path is not None:
        if not manifest_path.is_file():
            errors.append(f"manifest_path does not exist: {manifest_path}")
        else:
            try:
                loaded = load_json(manifest_path)
            except AcceptanceLoadError as e:
                errors.append(f"manifest_path is unreadable: {e}")
            else:
                if not isinstance(loaded, dict):
                    errors.append("manifest_path must reference a JSON object")
                else:
                    manifest = loaded
                    actual_id = manifest.get("id")
                    if manifest_id and actual_id != manifest_id:
                        errors.append(
                            f"manifest_id {manifest_id!r} does not match "
                            f"manifest id {actual_id!r}"
                        )

    if asset_path is not None:
        if not asset_path.is_file():
            errors.append(f"asset_path does not exist: {asset_path}")
        if manifest_path is not None and manifest is not None:
            expected_asset = _manifest_asset_path(manifest_path, manifest)
            if expected_asset is None:
                errors.append("manifest visual.glb_path is missing or invalid")
            elif asset_path != expected_asset:
                errors.append(
                    "asset_path must match manifest visual.glb_path: "
                    f"{asset_path} != {expected_asset}"
                )

    asset_kind = data.get("asset_kind")
    if asset_kind != CURRENT_ASSET_KIND:
        errors.append(
            f"asset_kind must be {CURRENT_ASSET_KIND!r} for the current asset, "
            f"got {asset_kind!r}"
        )

    if data.get("generated_fixture_replaced") is not False:
        errors.append("generated_fixture_replaced must be false until real art lands")

    validator_command = data.get("validator_command")
    if not isinstance(validator_command, str) or not validator_command.strip():
        errors.append("validator_command must be a non-empty string")

    checks = data.get("required_checks")
    if not isinstance(checks, list) or not all(isinstance(c, str) and c for c in checks):
        errors.append("required_checks must be a list of non-empty strings")
    else:
        missing = sorted(REQUIRED_CHECKS - set(checks))
        if missing:
            errors.append(f"required_checks missing gate(s): {', '.join(missing)}")

    human_signoff = data.get("human_signoff")
    if not isinstance(human_signoff, dict):
        errors.append("human_signoff must be an object")
    else:
        if human_signoff.get("production_art") is not False:
            errors.append("human_signoff.production_art must be false until real art lands")
        if not isinstance(human_signoff.get("visual_reviewed"), bool):
            errors.append("human_signoff.visual_reviewed must be a boolean")
        if "reviewer" not in human_signoff:
            errors.append("human_signoff.reviewer must be present")
        notes = human_signoff.get("notes")
        if not isinstance(notes, str) or not notes:
            errors.append("human_signoff.notes must be a non-empty string")

    return errors


def validate_file(path: Path, *, root: Path = REPO_ROOT) -> list[str]:
    try:
        data = load_json(path)
    except AcceptanceLoadError as e:
        return [str(e)]
    return validate_metadata(data, root=root)


def _display(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate DraftMyVan asset-acceptance metadata.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Acceptance metadata JSON files to validate.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help=f"Validate every metadata file matching {DEFAULT_GLOB}.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root for repo-relative metadata paths.",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if args.all:
        targets = sorted(root.glob(DEFAULT_GLOB))
    else:
        targets = args.paths

    if not targets:
        parser.error("no files provided (pass paths or --all)")
        return 2

    failed = 0
    for target in targets:
        errors = validate_file(target, root=root)
        if errors:
            failed += 1
            print(f"FAIL  {_display(target, root)}")
            for err in errors:
                print(f"      - {err}")
        else:
            print(f"OK    {_display(target, root)}")

    print()
    print(f"{len(targets) - failed}/{len(targets)} valid")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
