#!/usr/bin/env python3
"""Validate candidate visual audit metadata.

The visual audit is separate from contract validation. It records visual
findings while keeping the candidate non-production and non-promotable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_AUDIT = (
    REPO_ROOT
    / "examples"
    / "assets"
    / "candidates"
    / "galley_1000_candidate_visual_audit.json"
)

STATUS_VALID = "CANDIDATE VISUAL AUDIT VALID"
STATUS_INVALID = "CANDIDATE VISUAL AUDIT INVALID"


class VisualAuditError(Exception):
    """Raised when visual audit metadata or referenced files are invalid."""


def _read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        raise VisualAuditError(f"cannot read {path}: {e}") from e
    except json.JSONDecodeError as e:
        raise VisualAuditError(f"invalid JSON in {path}: {e}") from e


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise VisualAuditError(f"{key} must be a non-empty string")
    return value


def _repo_relative_path(root: Path, value: str, key: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise VisualAuditError(f"{key} must be a repository-relative path")
    return (root / path).resolve()


def _resolved_repo_path(root: Path, data: dict[str, Any], key: str) -> Path:
    return _repo_relative_path(root, _required_str(data, key), key)


def _ensure_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise VisualAuditError(f"{label} does not exist: {path}")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _validate_string_list(data: dict[str, Any], key: str, *, allow_empty: bool) -> None:
    value = data.get(key)
    if isinstance(value, str):
        raise VisualAuditError(f"{key} must be a list, not a string")
    if not isinstance(value, list):
        raise VisualAuditError(f"{key} must be a list")
    if not allow_empty and not value:
        raise VisualAuditError(f"{key} must be a non-empty list")
    bad = [i for i, item in enumerate(value) if not isinstance(item, str) or not item.strip()]
    if bad:
        raise VisualAuditError(
            f"{key} items must be non-empty strings "
            f"(bad indexes: {', '.join(str(i) for i in bad)})"
        )


def validate_visual_audit(
    audit_path: Path = DEFAULT_AUDIT,
    root: Path = REPO_ROOT,
) -> tuple[str, list[str]]:
    """Validate candidate visual audit metadata."""
    root = root.resolve()
    audit_path = audit_path.resolve()
    lines: list[str] = []

    try:
        data = _read_json(audit_path)
        if not isinstance(data, dict):
            raise VisualAuditError("visual audit metadata root must be an object")
        lines.append(f"[OK] visual audit metadata readable: {audit_path}")

        candidate_path = _resolved_repo_path(root, data, "candidate_asset_path")
        review_path = _resolved_repo_path(root, data, "candidate_review_path")
        _ensure_file(candidate_path, "candidate asset")
        _ensure_file(review_path, "candidate review metadata")
        lines.append(f"[OK] candidate asset exists: {candidate_path.relative_to(root)}")
        lines.append(f"[OK] candidate review metadata exists: {review_path.relative_to(root)}")

        review = _read_json(review_path)
        if not isinstance(review, dict):
            raise VisualAuditError("candidate review metadata root must be an object")

        review_candidate_path = _repo_relative_path(
            root,
            _required_str(review, "candidate_asset_path"),
            "candidate_review.candidate_asset_path",
        )
        if review_candidate_path != candidate_path:
            raise VisualAuditError("candidate_asset_path must match candidate review metadata")

        manifest_id = _required_str(data, "manifest_id")
        if review.get("manifest_id") != manifest_id:
            raise VisualAuditError("manifest_id must match candidate review metadata")
        lines.append(f"[OK] manifest_id matches candidate review metadata: {manifest_id}")

        candidate_sha = _sha256(candidate_path)
        expected_candidate_sha = _required_str(data, "candidate_sha256").lower()
        if expected_candidate_sha != candidate_sha:
            raise VisualAuditError(
                f"candidate_sha256 mismatch: metadata={expected_candidate_sha} actual={candidate_sha}"
            )
        lines.append(f"[OK] candidate SHA256 matches: {candidate_sha}")

        review_candidate_sha = _required_str(review, "candidate_sha256").lower()
        if expected_candidate_sha != review_candidate_sha:
            raise VisualAuditError("candidate_sha256 must match candidate review metadata")
        lines.append("[OK] candidate SHA256 matches candidate review metadata")

        if _required_str(data, "visual_status") != "not_production_ready":
            raise VisualAuditError('visual_status must be "not_production_ready"')
        if _required_str(data, "promotion_recommendation") != "do_not_promote":
            raise VisualAuditError('promotion_recommendation must be "do_not_promote"')
        lines.append("[OK] visual_status not production-ready; recommendation do not promote")

        _validate_string_list(data, "audited_views", allow_empty=True)
        _validate_string_list(data, "findings", allow_empty=False)
        _validate_string_list(data, "required_visual_improvements", allow_empty=False)
        lines.append("[OK] audited_views/findings/required improvements are valid lists")

        _required_str(data, "audit_version")
        _required_str(data, "audit_date")
        if "reviewer" not in data:
            raise VisualAuditError("reviewer field must be present")
        if data.get("reviewer") is not None:
            raise VisualAuditError("reviewer must be null until visual sign-off")
        lines.append("[OK] audit metadata fields are present")

        lines.append(f"RESULT: {STATUS_VALID}")
        return STATUS_VALID, lines

    except VisualAuditError as e:
        lines.append(f"[FAIL] {e}")
        lines.append(f"RESULT: {STATUS_INVALID}")
        return STATUS_INVALID, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate DraftMyVan candidate visual audit metadata.",
    )
    parser.add_argument(
        "audit",
        nargs="?",
        type=Path,
        default=DEFAULT_AUDIT,
        help=(
            "Candidate visual audit JSON (default: "
            "examples/assets/candidates/galley_1000_candidate_visual_audit.json)."
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
    audit_path = args.audit if args.audit.is_absolute() else root / args.audit
    status, lines = validate_visual_audit(audit_path, root)
    print(os.linesep.join(lines))
    return 0 if status == STATUS_VALID else 1


if __name__ == "__main__":
    sys.exit(main())
