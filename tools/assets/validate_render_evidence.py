#!/usr/bin/env python3
"""Validate candidate render evidence metadata."""

from __future__ import annotations

import argparse
import hashlib
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
    / "galley_1000_candidate_render_evidence.json"
)

REQUIRED_VIEWS = frozenset(("front", "rear", "left", "right", "top", "three_quarter"))
STATUS_VALID = "RENDER EVIDENCE VALID"
STATUS_INVALID = "RENDER EVIDENCE INVALID"


class RenderEvidenceError(Exception):
    """Raised when render evidence metadata is invalid."""


def _read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        raise RenderEvidenceError(f"cannot read {path}: {e}") from e
    except json.JSONDecodeError as e:
        raise RenderEvidenceError(f"invalid JSON in {path}: {e}") from e


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RenderEvidenceError(f"{key} must be a non-empty string")
    return value


def _required_bool(data: dict[str, Any], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise RenderEvidenceError(f"{key} must be a boolean")
    return value


def _repo_relative_path(root: Path, value: str, key: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise RenderEvidenceError(f"{key} must be a repository-relative path")
    return (root / path).resolve()


def _resolved_repo_path(root: Path, data: dict[str, Any], key: str) -> Path:
    return _repo_relative_path(root, _required_str(data, key), key)


def _ensure_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise RenderEvidenceError(f"{label} does not exist: {path}")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _validate_expected_views(data: dict[str, Any]) -> None:
    views = data.get("expected_views")
    if not isinstance(views, list) or not all(isinstance(v, str) for v in views):
        raise RenderEvidenceError("expected_views must be a list of strings")
    missing = sorted(REQUIRED_VIEWS.difference(views))
    if missing:
        raise RenderEvidenceError("expected_views is missing: " + ", ".join(missing))


def _validate_committed_render_paths(
    root: Path,
    data: dict[str, Any],
    render_output_dir: Path,
) -> None:
    render_paths = data.get("render_paths")
    if not isinstance(render_paths, dict):
        raise RenderEvidenceError(
            "committed_renders true requires render_paths for every expected view"
        )
    for view in sorted(REQUIRED_VIEWS):
        value = render_paths.get(view)
        if not isinstance(value, str) or not value.strip():
            raise RenderEvidenceError(f"render_paths.{view} must be a non-empty string")
        path = _repo_relative_path(root, value, f"render_paths.{view}")
        _ensure_file(path, f"render for {view}")
        if path.suffix.lower() != ".png":
            raise RenderEvidenceError(f"render_paths.{view} must point to a PNG")
        try:
            path.relative_to(render_output_dir)
        except ValueError as e:
            raise RenderEvidenceError(
                f"render_paths.{view} must be under render_output_dir"
            ) from e


def validate_render_evidence(
    metadata_path: Path = DEFAULT_METADATA,
    root: Path = REPO_ROOT,
) -> tuple[str, list[str]]:
    """Validate render evidence metadata."""
    root = root.resolve()
    metadata_path = metadata_path.resolve()
    lines: list[str] = []

    try:
        data = _read_json(metadata_path)
        if not isinstance(data, dict):
            raise RenderEvidenceError("render evidence metadata root must be an object")
        lines.append(f"[OK] render evidence metadata readable: {metadata_path}")

        candidate_path = _resolved_repo_path(root, data, "candidate_asset_path")
        visual_audit_path = _resolved_repo_path(root, data, "visual_audit_path")
        render_script_path = _resolved_repo_path(root, data, "render_script")
        render_output_dir = _repo_relative_path(
            root,
            _required_str(data, "render_output_dir"),
            "render_output_dir",
        )
        _ensure_file(candidate_path, "candidate asset")
        _ensure_file(visual_audit_path, "visual audit metadata")
        _ensure_file(render_script_path, "render script")
        lines.append(f"[OK] candidate asset exists: {candidate_path.relative_to(root)}")
        lines.append(f"[OK] visual audit metadata exists: {visual_audit_path.relative_to(root)}")
        lines.append(f"[OK] render script exists: {render_script_path.relative_to(root)}")

        visual_audit = _read_json(visual_audit_path)
        if not isinstance(visual_audit, dict):
            raise RenderEvidenceError("visual audit metadata root must be an object")

        manifest_id = _required_str(data, "manifest_id")
        if visual_audit.get("manifest_id") != manifest_id:
            raise RenderEvidenceError("manifest_id must match visual audit metadata")
        lines.append(f"[OK] manifest_id matches visual audit metadata: {manifest_id}")

        candidate_sha = _sha256(candidate_path)
        expected_candidate_sha = _required_str(data, "candidate_sha256").lower()
        if expected_candidate_sha != candidate_sha:
            raise RenderEvidenceError(
                f"candidate_sha256 mismatch: metadata={expected_candidate_sha} actual={candidate_sha}"
            )
        visual_audit_sha = visual_audit.get("candidate_sha256")
        if visual_audit_sha != expected_candidate_sha:
            raise RenderEvidenceError("candidate_sha256 must match visual audit metadata")
        lines.append(f"[OK] candidate SHA256 matches: {candidate_sha}")

        _validate_expected_views(data)
        lines.append("[OK] expected_views includes all required render views")

        committed_renders = _required_bool(data, "committed_renders")
        if committed_renders:
            _validate_committed_render_paths(root, data, render_output_dir)
            lines.append("[OK] committed render PNGs exist for every required view")
        else:
            lines.append("[OK] committed_renders is false; PNG evidence remains local-only")

        if _required_str(data, "evidence_status") != "procedure_ready":
            raise RenderEvidenceError('evidence_status must be "procedure_ready"')
        if _required_bool(data, "production_art") is not False:
            raise RenderEvidenceError("production_art must be false for render evidence")
        if _required_bool(data, "promotion_ready") is not False:
            raise RenderEvidenceError("promotion_ready must be false for render evidence")
        lines.append("[OK] evidence status procedure-ready; production/promote flags false")

        lines.append(f"RESULT: {STATUS_VALID}")
        return STATUS_VALID, lines

    except RenderEvidenceError as e:
        lines.append(f"[FAIL] {e}")
        lines.append(f"RESULT: {STATUS_INVALID}")
        return STATUS_INVALID, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate DraftMyVan candidate render evidence metadata.",
    )
    parser.add_argument(
        "metadata",
        nargs="?",
        type=Path,
        default=DEFAULT_METADATA,
        help=(
            "Render evidence JSON (default: "
            "examples/assets/candidates/galley_1000_candidate_render_evidence.json)."
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
    status, lines = validate_render_evidence(metadata_path, root)
    print(os.linesep.join(lines))
    return 0 if status == STATUS_VALID else 1


if __name__ == "__main__":
    sys.exit(main())
