#!/usr/bin/env python3
"""Validate candidate asset metadata and optional candidate GLB.

Candidate assets are process-test exports. They are not production assets and
must not replace `examples/assets/galley_1000.glb` until a later promotion PR
updates acceptance metadata and keeps the full GLB gates intact.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_METADATA = (
    REPO_ROOT
    / "examples"
    / "assets"
    / "candidates"
    / "galley_1000_candidate.asset_acceptance.json"
)

REQUIRED_CHECKS = frozenset(
    (
        "schema",
        "dimensions",
        "floor_back_left_anchor",
        "material_slots",
        "collision_proxy",
    )
)

STATUS_READY = "CANDIDATE READY"
STATUS_PLAN_ONLY = "CANDIDATE PLAN ONLY"
STATUS_INVALID = "CANDIDATE INVALID"

TOOLS_BLENDER = REPO_ROOT / "tools" / "blender"
sys.path.insert(0, str(TOOLS_BLENDER))

import validate_glb_against_manifest as glb_validator  # noqa: E402

try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None  # type: ignore[assignment]


class CandidateError(Exception):
    """Raised when candidate metadata or referenced files are invalid."""


def _read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        raise CandidateError(f"cannot read {path}: {e}") from e
    except json.JSONDecodeError as e:
        raise CandidateError(f"invalid JSON in {path}: {e}") from e


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CandidateError(f"{key} must be a non-empty string")
    return value


def _required_bool(data: dict[str, Any], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise CandidateError(f"{key} must be a boolean")
    return value


def _repo_relative_path(root: Path, value: str, key: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise CandidateError(f"{key} must be a repository-relative path")
    return (root / path).resolve()


def _resolved_repo_path(root: Path, data: dict[str, Any], key: str) -> Path:
    return _repo_relative_path(root, _required_str(data, key), key)


def _ensure_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise CandidateError(f"{label} does not exist: {path}")


def _validate_required_checks(data: dict[str, Any]) -> None:
    checks = data.get("required_checks")
    if not isinstance(checks, list) or not all(isinstance(c, str) for c in checks):
        raise CandidateError("required_checks must be a list of strings")
    missing = sorted(REQUIRED_CHECKS.difference(checks))
    if missing:
        raise CandidateError("required_checks is missing: " + ", ".join(missing))


def _validate_signoff(data: dict[str, Any]) -> None:
    signoff = data.get("human_signoff")
    if not isinstance(signoff, dict):
        raise CandidateError("human_signoff must be an object")
    if signoff.get("visual_reviewed") is not False:
        raise CandidateError("human_signoff.visual_reviewed must be false before promotion")
    if signoff.get("reviewer") is not None:
        raise CandidateError("human_signoff.reviewer must be null before promotion")
    if signoff.get("reviewed_at") is not None:
        raise CandidateError("human_signoff.reviewed_at must be null before promotion")
    notes = signoff.get("notes")
    if not isinstance(notes, str) or not notes.strip():
        raise CandidateError("human_signoff.notes must explain the candidate state")


def _manifest_target_path(manifest_path: Path, manifest: dict[str, Any]) -> Path:
    visual = manifest.get("visual")
    if not isinstance(visual, dict):
        raise CandidateError("referenced manifest has no visual object")
    glb_path = visual.get("glb_path")
    if not isinstance(glb_path, str) or not glb_path:
        raise CandidateError("referenced manifest has no visual.glb_path")
    return (manifest_path.parent / glb_path).resolve()


def _validate_manifest_schema(root: Path, manifest: dict[str, Any]) -> None:
    if Draft202012Validator is None:
        raise CandidateError(
            "jsonschema is not installed; cannot run manifest schema validation"
        )
    schema_path = root / "manifest.schema.json"
    schema = _read_json(schema_path)
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(manifest),
        key=lambda e: list(e.absolute_path),
    )
    if errors:
        first = errors[0]
        path = "/".join(str(p) for p in first.absolute_path) or "<root>"
        raise CandidateError(f"manifest schema validation failed at {path}: {first.message}")


def validate_candidate(
    metadata_path: Path = DEFAULT_METADATA,
    root: Path = REPO_ROOT,
) -> tuple[str, list[str]]:
    """Validate a candidate metadata file.

    Returns (status, report_lines) where status is one of:
    CANDIDATE READY, CANDIDATE PLAN ONLY, CANDIDATE INVALID.
    """
    root = root.resolve()
    metadata_path = metadata_path.resolve()
    lines: list[str] = []

    try:
        data = _read_json(metadata_path)
        if not isinstance(data, dict):
            raise CandidateError("metadata root must be an object")
        lines.append(f"[OK] metadata readable: {metadata_path}")

        manifest_path = _resolved_repo_path(root, data, "manifest_path")
        candidate_path = _resolved_repo_path(root, data, "candidate_asset_path")
        target_path = _resolved_repo_path(root, data, "target_asset_path")
        golden_fixture_path = _resolved_repo_path(root, data, "golden_fixture_path")
        _ensure_file(manifest_path, "manifest")
        _ensure_file(target_path, "target asset")
        _ensure_file(golden_fixture_path, "golden fixture")
        lines.append(f"[OK] manifest exists: {manifest_path.relative_to(root)}")
        lines.append(f"[OK] target asset exists: {target_path.relative_to(root)}")
        lines.append(f"[OK] golden fixture exists: {golden_fixture_path.relative_to(root)}")

        manifest = _read_json(manifest_path)
        if not isinstance(manifest, dict):
            raise CandidateError("referenced manifest root must be an object")
        _validate_manifest_schema(root, manifest)
        lines.append("[OK] manifest schema validates")

        manifest_id = _required_str(data, "manifest_id")
        if manifest.get("id") != manifest_id:
            raise CandidateError(
                f"manifest_id {manifest_id!r} does not match manifest id {manifest.get('id')!r}"
            )
        lines.append(f"[OK] manifest_id matches: {manifest_id}")

        expected_target = _manifest_target_path(manifest_path, manifest)
        if target_path != expected_target:
            raise CandidateError(
                f"target_asset_path must match manifest visual.glb_path: "
                f"{target_path.relative_to(root)} != {expected_target.relative_to(root)}"
            )
        lines.append("[OK] target_asset_path matches manifest visual.glb_path")

        if target_path.read_bytes() != golden_fixture_path.read_bytes():
            raise CandidateError(
                "target manifest asset no longer matches the golden fixture; "
                "candidate PRs must not promote assets"
            )
        lines.append("[OK] target manifest asset remains the current generated fixture")

        if _required_bool(data, "candidate_only") is not True:
            raise CandidateError("candidate_only must be true")
        if _required_bool(data, "production_art") is not False:
            raise CandidateError("production_art must be false for candidates")
        if _required_bool(data, "promotion_allowed") is not False:
            raise CandidateError("promotion_allowed must be false for candidates")
        lines.append("[OK] candidate_only true; production_art false; promotion_allowed false")

        if not _required_str(data, "validator_command"):
            raise CandidateError("validator_command must be present")
        lines.append("[OK] validator_command present")

        _validate_required_checks(data)
        lines.append("[OK] required_checks includes full current gate list")

        _validate_signoff(data)
        lines.append("[OK] human sign-off fields are present and do not claim review")

        candidate_expected = _required_bool(data, "candidate_asset_expected")
        candidate_exists = candidate_path.is_file()

        if not candidate_expected:
            if candidate_exists:
                raise CandidateError(
                    "candidate_asset_expected is false but candidate_asset_path exists"
                )
            lines.append("[OK] candidate GLB is not expected yet")
            lines.append(f"RESULT: {STATUS_PLAN_ONLY}")
            return STATUS_PLAN_ONLY, lines

        if not candidate_exists:
            raise CandidateError(f"candidate asset does not exist: {candidate_path}")
        lines.append(f"[OK] candidate asset exists: {candidate_path.relative_to(root)}")

        try:
            report = glb_validator.validate(
                manifest_path=manifest_path,
                glb_path=candidate_path,
                tolerance_mm=1.0,
                glb_units="meters",
                ignore_path_mismatch=True,
            )
        except (glb_validator.ManifestError, glb_validator.GlbParseError) as e:
            raise CandidateError(f"candidate GLB validation error: {e}") from e
        lines.append("[..] candidate GLB gate:")
        lines.extend(f"     {message}" for message in report.messages)
        if not report.ok:
            raise CandidateError("candidate GLB failed the manifest gate")
        lines.append(f"RESULT: {STATUS_READY}")
        return STATUS_READY, lines

    except CandidateError as e:
        lines.append(f"[FAIL] {e}")
        lines.append(f"RESULT: {STATUS_INVALID}")
        return STATUS_INVALID, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate DraftMyVan candidate asset metadata and GLB state.",
    )
    parser.add_argument(
        "metadata",
        nargs="?",
        type=Path,
        default=DEFAULT_METADATA,
        help=(
            "Candidate metadata JSON (default: "
            "examples/assets/candidates/galley_1000_candidate.asset_acceptance.json)."
        ),
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
    status, lines = validate_candidate(metadata_path, root)
    print(os.linesep.join(lines))
    return 0 if status in {STATUS_READY, STATUS_PLAN_ONLY} else 1


if __name__ == "__main__":
    sys.exit(main())
