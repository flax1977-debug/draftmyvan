#!/usr/bin/env python3
"""Validate an asset-acceptance metadata file.

Every asset under ``examples/assets/`` that has shipped through the
manifest contract is accompanied by an ``*.asset_acceptance.json``
sidecar that records:

  * which manifest the asset belongs to,
  * whether the asset is still the deterministic generated fixture or
    has been replaced by real production art,
  * which validator command must pass before the asset is committable,
  * which named checks form the current full gate list,
  * a human sign-off block (visual review, production art, reviewer,
    notes).

This script is the gate on that sidecar. It is **stdlib-only** and runs
in CI. What it checks:

  * The metadata file is well-formed JSON with the expected fields.
  * ``manifest_path`` resolves to an existing file under the repo.
  * ``asset_path`` resolves to an existing file under the repo.
  * The manifest at ``manifest_path`` has the id named in
    ``manifest_id``.
  * ``validator_command`` is a non-empty string.
  * ``required_checks`` includes the current full gate list:
    ``schema``, ``dimensions``, ``floor_back_left_anchor``,
    ``material_slots``, ``collision_proxy``.
  * For this phase of the project (no real cabinet art yet),
    ``generated_fixture_replaced`` is ``false`` and
    ``human_signoff.production_art`` is ``false``. The day real art
    lands, this contract is what flips — and it must flip
    deliberately, not silently.

Usage::

    python tools/assets/validate_asset_acceptance.py \\
        examples/assets/galley_1000.asset_acceptance.json

    python tools/assets/validate_asset_acceptance.py --all

Exit codes:
    0  all metadata files valid
    1  one or more metadata files invalid
    2  bad arguments / file unreadable
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Every named check the current full validator suite enforces. The
# acceptance metadata must list at least this set — anything missing
# means the metadata is out of date with the gate.
REQUIRED_CHECKS: tuple[str, ...] = (
    "schema",
    "dimensions",
    "floor_back_left_anchor",
    "material_slots",
    "collision_proxy",
)

# Top-level keys that the acceptance metadata must declare.
REQUIRED_TOP_LEVEL_KEYS: tuple[str, ...] = (
    "manifest_id",
    "asset_path",
    "asset_kind",
    "generated_fixture_replaced",
    "validator_command",
    "required_checks",
    "human_signoff",
)

# Keys inside the human_signoff block.
REQUIRED_SIGNOFF_KEYS: tuple[str, ...] = (
    "visual_reviewed",
    "production_art",
    "reviewer",
    "notes",
)

# Asset-acceptance metadata is co-located with the asset, so by
# convention metadata at ``examples/assets/<id>.asset_acceptance.json``
# is associated with the manifest at ``examples/<id>.json`` unless an
# explicit ``manifest_path`` field overrides it.
DEFAULT_MANIFEST_DIR = REPO_ROOT / "examples"


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level JSON must be an object")
    return data


def _resolve_path(rel_or_abs: str, anchor: Path) -> Path:
    p = Path(rel_or_abs)
    if p.is_absolute():
        return p
    return (anchor / p).resolve()


def _default_manifest_for(metadata_path: Path) -> Path:
    """Convention: examples/assets/<id>.asset_acceptance.json
    ↔ examples/<id>.json."""
    stem = metadata_path.name.replace(".asset_acceptance.json", "")
    return DEFAULT_MANIFEST_DIR / f"{stem}.json"


def validate_file(
    metadata_path: Path, repo_root: Path = REPO_ROOT,
) -> tuple[bool, list[str]]:
    """Return (ok, lines). One file at a time."""
    lines: list[str] = []
    if not metadata_path.exists():
        return False, [f"[FAIL] metadata not found: {metadata_path}"]

    try:
        data = _read_json(metadata_path)
    except (json.JSONDecodeError, ValueError, OSError) as e:
        return False, [f"[FAIL] {metadata_path}: unreadable / not JSON: {e}"]

    ok = True

    # Top-level required keys.
    missing = [k for k in REQUIRED_TOP_LEVEL_KEYS if k not in data]
    if missing:
        lines.append(
            f"[FAIL] {metadata_path}: missing required key(s): "
            f"{', '.join(missing)}"
        )
        return False, lines

    # Manifest path resolution: prefer explicit, fall back to convention.
    manifest_rel = data.get("manifest_path")
    if isinstance(manifest_rel, str) and manifest_rel:
        manifest_path = _resolve_path(manifest_rel, repo_root)
    else:
        manifest_path = _default_manifest_for(metadata_path)
    if not manifest_path.is_file():
        lines.append(
            f"[FAIL] {metadata_path}: manifest path does not exist: "
            f"{manifest_path}"
        )
        ok = False
    else:
        lines.append(f"[OK]   manifest exists: {manifest_path}")

        # manifest_id must match the manifest's own id.
        try:
            manifest_data = _read_json(manifest_path)
        except (json.JSONDecodeError, ValueError, OSError) as e:
            lines.append(f"[FAIL] {metadata_path}: manifest unreadable: {e}")
            ok = False
        else:
            declared_id = data.get("manifest_id")
            actual_id = manifest_data.get("id")
            if declared_id != actual_id:
                lines.append(
                    f"[FAIL] {metadata_path}: manifest_id "
                    f"{declared_id!r} != manifest's id {actual_id!r}"
                )
                ok = False
            else:
                lines.append(f"[OK]   manifest_id matches: {actual_id!r}")

    # Asset existence.
    asset_rel = data.get("asset_path")
    if not isinstance(asset_rel, str) or not asset_rel:
        lines.append(f"[FAIL] {metadata_path}: asset_path missing or empty")
        ok = False
    else:
        asset_path = _resolve_path(asset_rel, repo_root)
        if not asset_path.is_file():
            lines.append(
                f"[FAIL] {metadata_path}: asset_path does not exist: "
                f"{asset_path}"
            )
            ok = False
        else:
            lines.append(f"[OK]   asset exists: {asset_path}")

    # Validator command present.
    validator_command = data.get("validator_command")
    if not isinstance(validator_command, str) or not validator_command.strip():
        lines.append(
            f"[FAIL] {metadata_path}: validator_command must be a "
            f"non-empty string"
        )
        ok = False
    else:
        lines.append(f"[OK]   validator_command present")

    # Required-checks coverage.
    declared_checks = data.get("required_checks")
    if not isinstance(declared_checks, list):
        lines.append(
            f"[FAIL] {metadata_path}: required_checks must be a list"
        )
        ok = False
    else:
        declared_set = set(c for c in declared_checks if isinstance(c, str))
        missing_checks = [c for c in REQUIRED_CHECKS if c not in declared_set]
        if missing_checks:
            lines.append(
                f"[FAIL] {metadata_path}: required_checks missing the "
                f"current full gate list: {', '.join(missing_checks)}"
            )
            ok = False
        else:
            lines.append(
                f"[OK]   required_checks covers the full gate list "
                f"({', '.join(REQUIRED_CHECKS)})"
            )

    # Phase invariant: no real art yet.
    gfr = data.get("generated_fixture_replaced")
    if gfr is not False:
        lines.append(
            f"[FAIL] {metadata_path}: generated_fixture_replaced must be "
            f"false for now (no real cabinet art has landed); got {gfr!r}"
        )
        ok = False
    else:
        lines.append(f"[OK]   generated_fixture_replaced is false")

    # human_signoff structural check + production_art invariant.
    signoff = data.get("human_signoff")
    if not isinstance(signoff, dict):
        lines.append(
            f"[FAIL] {metadata_path}: human_signoff must be an object"
        )
        ok = False
    else:
        missing_signoff = [k for k in REQUIRED_SIGNOFF_KEYS if k not in signoff]
        if missing_signoff:
            lines.append(
                f"[FAIL] {metadata_path}: human_signoff missing key(s): "
                f"{', '.join(missing_signoff)}"
            )
            ok = False
        else:
            lines.append(f"[OK]   human_signoff has every required field")
            prod = signoff.get("production_art")
            if prod is not False:
                lines.append(
                    f"[FAIL] {metadata_path}: human_signoff.production_art "
                    f"must be false for now (no real cabinet art has "
                    f"landed); got {prod!r}"
                )
                ok = False
            else:
                lines.append(
                    f"[OK]   human_signoff.production_art is false"
                )

    return ok, lines


def _find_all_metadata(repo_root: Path) -> list[Path]:
    return sorted(
        (repo_root / "examples" / "assets").glob("*.asset_acceptance.json")
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate DraftMyVan asset-acceptance metadata files.",
    )
    parser.add_argument(
        "paths", nargs="*", type=Path,
        help="Metadata JSON files to validate.",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Validate every *.asset_acceptance.json under examples/assets/.",
    )
    args = parser.parse_args(argv)

    if args.all:
        targets = _find_all_metadata(REPO_ROOT)
        if not targets:
            print("ERROR: no asset_acceptance metadata files found under examples/assets/",
                  file=sys.stderr)
            return 2
    else:
        if not args.paths:
            parser.error("no files provided (pass paths or --all)")
            return 2
        targets = list(args.paths)

    failed = 0
    for path in targets:
        ok, lines = validate_file(path)
        header = "OK   " if ok else "FAIL "
        print(f"{header} {path}")
        for line in lines:
            print(f"  {line}")
        if not ok:
            failed += 1

    print()
    print(f"{len(targets) - failed}/{len(targets)} valid")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
