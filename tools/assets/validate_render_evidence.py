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
ALLOWED_RENDER_ROOT_REL = Path("examples/assets/candidates/render_evidence")
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


def _required_positive_int(data: dict[str, Any], key: str, label: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RenderEvidenceError(f"{label}.{key} must be a positive integer")
    return value


def _required_object(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise RenderEvidenceError(f"{key} must be an object")
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


def _validate_expected_views(data: dict[str, Any]) -> set[str]:
    views = data.get("expected_views")
    if not isinstance(views, list) or not all(isinstance(v, str) for v in views):
        raise RenderEvidenceError("expected_views must be a list of strings")
    missing = sorted(REQUIRED_VIEWS.difference(views))
    if missing:
        raise RenderEvidenceError("expected_views is missing: " + ", ".join(missing))
    return set(views)


def _render_file_str(entry: dict[str, Any], key: str, label: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RenderEvidenceError(f"{label}.{key} must be a non-empty string")
    return value


def _validate_committed_render_files(
    root: Path,
    data: dict[str, Any],
    render_output_dir: Path,
    expected_views: set[str],
) -> None:
    render_files = data.get("render_files")
    if not isinstance(render_files, list):
        raise RenderEvidenceError(
            "committed_renders true requires render_files for every expected view"
        )
    allowed_root = (root / ALLOWED_RENDER_ROOT_REL).resolve()
    seen: set[str] = set()
    listed_paths: set[Path] = set()
    for idx, entry in enumerate(render_files):
        label = f"render_files[{idx}]"
        if not isinstance(entry, dict):
            raise RenderEvidenceError(f"{label} must be an object")
        view = _render_file_str(entry, "view", label)
        if view not in expected_views:
            raise RenderEvidenceError(f"{label}.view is not in expected_views: {view}")
        if view in seen:
            raise RenderEvidenceError(f"render_files has duplicate view: {view}")
        seen.add(view)

        path = _repo_relative_path(root, _render_file_str(entry, "path", label), f"{label}.path")
        _ensure_file(path, f"render for {view}")
        if path.suffix.lower() != ".png":
            raise RenderEvidenceError(f"{label}.path must point to a PNG")
        try:
            path.relative_to(allowed_root)
        except ValueError as e:
            raise RenderEvidenceError(
                f"{label}.path must be under {ALLOWED_RENDER_ROOT_REL}"
            ) from e
        try:
            path.relative_to(render_output_dir)
        except ValueError as e:
            raise RenderEvidenceError(
                f"{label}.path must be under render_output_dir"
            ) from e
        listed_paths.add(path)

        expected_size = _required_positive_int(entry, "file_size_bytes", label)
        actual_size = path.stat().st_size
        if actual_size != expected_size:
            raise RenderEvidenceError(
                f"{label}.file_size_bytes mismatch: metadata={expected_size} actual={actual_size}"
            )

        expected_sha = _render_file_str(entry, "sha256", label).lower()
        actual_sha = _sha256(path)
        if actual_sha != expected_sha:
            raise RenderEvidenceError(
                f"{label}.sha256 mismatch: metadata={expected_sha} actual={actual_sha}"
            )

    missing = sorted(expected_views.difference(seen))
    if missing:
        raise RenderEvidenceError("render_files is missing: " + ", ".join(missing))

    extra_files = sorted(
        path
        for path in render_output_dir.rglob("*")
        if path.is_file() and path.resolve() not in listed_paths
    )
    if extra_files:
        extras = ", ".join(str(path.relative_to(root)) for path in extra_files)
        raise RenderEvidenceError("render_output_dir contains unapproved file(s): " + extras)


def _validate_render_provenance(data: dict[str, Any]) -> None:
    resolution = _required_object(data, "render_resolution")
    _required_positive_int(resolution, "width_px", "render_resolution")
    _required_positive_int(resolution, "height_px", "render_resolution")
    if _required_str(data, "render_engine") != "BLENDER_WORKBENCH":
        raise RenderEvidenceError('render_engine must be "BLENDER_WORKBENCH"')
    _required_str(data, "lighting_setup")


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

        expected_views = _validate_expected_views(data)
        lines.append("[OK] expected_views includes all required render views")

        committed_renders = _required_bool(data, "committed_renders")
        if committed_renders:
            generated_from = _required_str(data, "generated_from_candidate_sha256").lower()
            if generated_from != candidate_sha:
                raise RenderEvidenceError(
                    "generated_from_candidate_sha256 must match actual candidate SHA"
                )
            _required_str(data, "render_command")
            if _required_str(data, "render_tool") != "Blender":
                raise RenderEvidenceError('render_tool must be "Blender"')
            _required_str(data, "render_note")
            _validate_render_provenance(data)
            lines.append("[OK] render provenance fields are recorded")
            _validate_committed_render_files(root, data, render_output_dir, expected_views)
            lines.append(
                "[OK] committed render PNGs are present, SHA/size pinned, and no extra files found"
            )
        else:
            if "generated_from_candidate_sha256" in data:
                generated_from = data["generated_from_candidate_sha256"]
                if not isinstance(generated_from, str) or generated_from.lower() != candidate_sha:
                    raise RenderEvidenceError(
                        "generated_from_candidate_sha256 must match actual candidate SHA"
                    )
            lines.append("[OK] committed_renders is false; PNG evidence remains local-only")

        expected_status = (
            "committed_review_evidence" if committed_renders else "procedure_ready"
        )
        if _required_str(data, "evidence_status") != expected_status:
            raise RenderEvidenceError(f'evidence_status must be "{expected_status}"')
        if _required_bool(data, "production_art") is not False:
            raise RenderEvidenceError("production_art must be false for render evidence")
        if _required_bool(data, "promotion_ready") is not False:
            raise RenderEvidenceError("promotion_ready must be false for render evidence")
        lines.append(f"[OK] evidence status {expected_status}; production/promote flags false")

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
