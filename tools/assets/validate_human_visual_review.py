#!/usr/bin/env python3
"""Validate candidate human visual review metadata.

Human visual review records observations from committed render evidence. It is
not production sign-off and must keep the candidate non-production and
non-promotable.
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
DEFAULT_REVIEW = (
    REPO_ROOT
    / "examples"
    / "assets"
    / "candidates"
    / "galley_1000_candidate_human_visual_review.json"
)

REQUIRED_VIEWS = frozenset(("front", "rear", "left", "right", "top", "three_quarter"))
STATUS_VALID = "HUMAN VISUAL REVIEW VALID"
STATUS_INVALID = "HUMAN VISUAL REVIEW INVALID"


class HumanVisualReviewError(Exception):
    """Raised when human visual review metadata is invalid."""


def _read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        raise HumanVisualReviewError(f"cannot read {path}: {e}") from e
    except json.JSONDecodeError as e:
        raise HumanVisualReviewError(f"invalid JSON in {path}: {e}") from e


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise HumanVisualReviewError(f"{key} must be a non-empty string")
    return value


def _required_bool(data: dict[str, Any], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise HumanVisualReviewError(f"{key} must be a boolean")
    return value


def _repo_relative_path(root: Path, value: str, key: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise HumanVisualReviewError(f"{key} must be a repository-relative path")
    return (root / path).resolve()


def _resolved_repo_path(root: Path, data: dict[str, Any], key: str) -> Path:
    return _repo_relative_path(root, _required_str(data, key), key)


def _ensure_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise HumanVisualReviewError(f"{label} does not exist: {path}")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _validate_string_list(data: dict[str, Any], key: str) -> None:
    value = data.get(key)
    if isinstance(value, str):
        raise HumanVisualReviewError(f"{key} must be a list, not a string")
    if not isinstance(value, list):
        raise HumanVisualReviewError(f"{key} must be a list")
    if not value:
        raise HumanVisualReviewError(f"{key} must be a non-empty list")
    bad = [i for i, item in enumerate(value) if not isinstance(item, str) or not item.strip()]
    if bad:
        raise HumanVisualReviewError(
            f"{key} items must be non-empty strings "
            f"(bad indexes: {', '.join(str(i) for i in bad)})"
        )


def _validate_view_observations(data: dict[str, Any]) -> None:
    observations = data.get("view_observations")
    if not isinstance(observations, dict):
        raise HumanVisualReviewError("view_observations must be an object")
    missing = sorted(REQUIRED_VIEWS.difference(observations))
    if missing:
        raise HumanVisualReviewError("view_observations is missing: " + ", ".join(missing))
    bad = [
        view
        for view in sorted(REQUIRED_VIEWS)
        if not isinstance(observations.get(view), str) or not observations[view].strip()
    ]
    if bad:
        raise HumanVisualReviewError(
            "view_observations entries must be non-empty strings: " + ", ".join(bad)
        )


def validate_human_visual_review(
    review_path: Path = DEFAULT_REVIEW,
    root: Path = REPO_ROOT,
) -> tuple[str, list[str]]:
    """Validate human visual review metadata."""
    root = root.resolve()
    review_path = review_path.resolve()
    lines: list[str] = []

    try:
        data = _read_json(review_path)
        if not isinstance(data, dict):
            raise HumanVisualReviewError("human visual review metadata root must be an object")
        lines.append(f"[OK] human visual review metadata readable: {review_path}")

        candidate_path = _resolved_repo_path(root, data, "candidate_asset_path")
        render_evidence_path = _resolved_repo_path(root, data, "render_evidence_path")
        visual_audit_path = _resolved_repo_path(root, data, "visual_audit_path")
        _ensure_file(candidate_path, "candidate asset")
        _ensure_file(render_evidence_path, "render evidence metadata")
        _ensure_file(visual_audit_path, "visual audit metadata")
        lines.append(f"[OK] candidate asset exists: {candidate_path.relative_to(root)}")
        lines.append(f"[OK] render evidence metadata exists: {render_evidence_path.relative_to(root)}")
        lines.append(f"[OK] visual audit metadata exists: {visual_audit_path.relative_to(root)}")

        render_evidence = _read_json(render_evidence_path)
        visual_audit = _read_json(visual_audit_path)
        if not isinstance(render_evidence, dict):
            raise HumanVisualReviewError("render evidence metadata root must be an object")
        if not isinstance(visual_audit, dict):
            raise HumanVisualReviewError("visual audit metadata root must be an object")

        manifest_id = _required_str(data, "manifest_id")
        if render_evidence.get("manifest_id") != manifest_id:
            raise HumanVisualReviewError("manifest_id must match render evidence metadata")
        if visual_audit.get("manifest_id") != manifest_id:
            raise HumanVisualReviewError("manifest_id must match visual audit metadata")
        lines.append(f"[OK] manifest_id matches linked metadata: {manifest_id}")

        candidate_sha = _sha256(candidate_path)
        expected_candidate_sha = _required_str(data, "candidate_sha256").lower()
        if expected_candidate_sha != candidate_sha:
            raise HumanVisualReviewError(
                f"candidate_sha256 mismatch: metadata={expected_candidate_sha} actual={candidate_sha}"
            )
        if render_evidence.get("candidate_sha256") != expected_candidate_sha:
            raise HumanVisualReviewError("candidate_sha256 must match render evidence metadata")
        if visual_audit.get("candidate_sha256") != expected_candidate_sha:
            raise HumanVisualReviewError("candidate_sha256 must match visual audit metadata")
        lines.append(f"[OK] candidate SHA256 matches: {candidate_sha}")

        render_status = _required_str(data, "render_evidence_status")
        if render_status != "committed_review_evidence":
            raise HumanVisualReviewError('render_evidence_status must be "committed_review_evidence"')
        if render_evidence.get("evidence_status") != render_status:
            raise HumanVisualReviewError("render_evidence_status must match render evidence metadata")
        lines.append("[OK] render evidence status is committed review evidence")

        if _required_bool(data, "production_art") is not False:
            raise HumanVisualReviewError("production_art must be false for human visual review")
        if _required_bool(data, "promotion_ready") is not False:
            raise HumanVisualReviewError("promotion_ready must be false for human visual review")
        if _required_str(data, "promotion_recommendation") != "do_not_promote":
            raise HumanVisualReviewError('promotion_recommendation must be "do_not_promote"')
        lines.append("[OK] production/promote flags remain false")

        _validate_view_observations(data)
        lines.append("[OK] all required view observations are present")

        for key in ("strengths", "weaknesses", "required_before_promotion"):
            _validate_string_list(data, key)
        lines.append("[OK] strengths, weaknesses, and required_before_promotion are valid lists")

        _required_str(data, "review_version")
        _required_str(data, "review_date")
        if "reviewer" not in data:
            raise HumanVisualReviewError("reviewer field must be present")
        if data.get("reviewer") is not None:
            raise HumanVisualReviewError("reviewer must be null until production visual sign-off")
        _required_str(data, "next_recommended_action")
        lines.append("[OK] review metadata fields are present")

        lines.append(f"RESULT: {STATUS_VALID}")
        return STATUS_VALID, lines

    except HumanVisualReviewError as e:
        lines.append(f"[FAIL] {e}")
        lines.append(f"RESULT: {STATUS_INVALID}")
        return STATUS_INVALID, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate DraftMyVan candidate human visual review metadata.",
    )
    parser.add_argument(
        "review",
        nargs="?",
        type=Path,
        default=DEFAULT_REVIEW,
        help=(
            "Candidate human visual review JSON (default: "
            "examples/assets/candidates/galley_1000_candidate_human_visual_review.json)."
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
    review_path = args.review if args.review.is_absolute() else root / args.review
    status, lines = validate_human_visual_review(review_path, root)
    print(os.linesep.join(lines))
    return 0 if status == STATUS_VALID else 1


if __name__ == "__main__":
    sys.exit(main())
