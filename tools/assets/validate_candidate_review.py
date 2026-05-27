#!/usr/bin/env python3
"""Validate candidate review metadata.

The candidate review is the boundary between "contract-valid candidate" and
"ready to discuss promotion." It must stay SHA-pinned to the candidate file and
must not claim production or promotion readiness.
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
    / "galley_1000_candidate_review.json"
)

STATUS_VALID = "CANDIDATE REVIEW VALID"
STATUS_INVALID = "CANDIDATE REVIEW INVALID"

sys.path.insert(0, str(REPO_ROOT / "tools" / "assets"))
import validate_candidate_asset as candidate_validator  # noqa: E402


class ReviewError(Exception):
    """Raised when review metadata or referenced files are invalid."""


def _read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        raise ReviewError(f"cannot read {path}: {e}") from e
    except json.JSONDecodeError as e:
        raise ReviewError(f"invalid JSON in {path}: {e}") from e


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ReviewError(f"{key} must be a non-empty string")
    return value


def _required_bool(data: dict[str, Any], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise ReviewError(f"{key} must be a boolean")
    return value


def _repo_relative_path(root: Path, value: str, key: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ReviewError(f"{key} must be a repository-relative path")
    return (root / path).resolve()


def _resolved_repo_path(root: Path, data: dict[str, Any], key: str) -> Path:
    return _repo_relative_path(root, _required_str(data, key), key)


def _ensure_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise ReviewError(f"{label} does not exist: {path}")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _validate_required_before_promotion(data: dict[str, Any]) -> None:
    items = data.get("required_before_promotion")
    if isinstance(items, str):
        raise ReviewError("required_before_promotion must be a list, not a string")
    if not isinstance(items, list) or not items:
        raise ReviewError("required_before_promotion must be a non-empty list")
    bad = [i for i, item in enumerate(items) if not isinstance(item, str) or not item.strip()]
    if bad:
        raise ReviewError(
            "required_before_promotion items must be non-empty strings "
            f"(bad indexes: {', '.join(str(i) for i in bad)})"
        )


def _manifest_path_from_acceptance(
    root: Path,
    acceptance: dict[str, Any],
) -> Path:
    manifest_path = acceptance.get("manifest_path")
    if not isinstance(manifest_path, str) or not manifest_path.strip():
        raise ReviewError("candidate acceptance metadata must include manifest_path")
    return _repo_relative_path(root, manifest_path, "candidate_acceptance.manifest_path")


def _acceptance_sha(acceptance: dict[str, Any]) -> tuple[str, str] | None:
    for key in ("candidate_sha256", "candidate_asset_sha256"):
        if key in acceptance:
            value = acceptance[key]
            if not isinstance(value, str) or not value.strip():
                raise ReviewError(f"{key} in candidate acceptance metadata must be a non-empty string")
            return key, value.lower()
    return None


def validate_review(
    review_path: Path = DEFAULT_REVIEW,
    root: Path = REPO_ROOT,
) -> tuple[str, list[str]]:
    """Validate candidate review metadata.

    Returns (status, report_lines), where status is CANDIDATE REVIEW VALID or
    CANDIDATE REVIEW INVALID.
    """
    root = root.resolve()
    review_path = review_path.resolve()
    lines: list[str] = []

    try:
        data = _read_json(review_path)
        if not isinstance(data, dict):
            raise ReviewError("review metadata root must be an object")
        lines.append(f"[OK] review metadata readable: {review_path}")

        candidate_path = _resolved_repo_path(root, data, "candidate_asset_path")
        acceptance_path = _resolved_repo_path(root, data, "candidate_acceptance_path")
        golden_path = _resolved_repo_path(root, data, "golden_fixture_path")
        _ensure_file(candidate_path, "candidate asset")
        _ensure_file(acceptance_path, "candidate acceptance metadata")
        _ensure_file(golden_path, "golden fixture")
        lines.append(f"[OK] candidate asset exists: {candidate_path.relative_to(root)}")
        lines.append(
            f"[OK] candidate acceptance metadata exists: {acceptance_path.relative_to(root)}"
        )
        lines.append(f"[OK] golden fixture exists: {golden_path.relative_to(root)}")

        acceptance = _read_json(acceptance_path)
        if not isinstance(acceptance, dict):
            raise ReviewError("candidate acceptance metadata root must be an object")

        acceptance_candidate_path = _repo_relative_path(
            root,
            _required_str(acceptance, "candidate_asset_path"),
            "candidate_acceptance.candidate_asset_path",
        )
        if acceptance_candidate_path != candidate_path:
            raise ReviewError(
                "candidate_asset_path must match candidate acceptance metadata"
            )

        if "golden_fixture_path" in acceptance:
            acceptance_golden_path = _repo_relative_path(
                root,
                _required_str(acceptance, "golden_fixture_path"),
                "candidate_acceptance.golden_fixture_path",
            )
            if acceptance_golden_path != golden_path:
                raise ReviewError(
                    "golden_fixture_path must match candidate acceptance metadata"
                )

        manifest_path = _manifest_path_from_acceptance(root, acceptance)
        _ensure_file(manifest_path, "manifest")
        lines.append(f"[OK] manifest exists: {manifest_path.relative_to(root)}")

        manifest = _read_json(manifest_path)
        if not isinstance(manifest, dict):
            raise ReviewError("referenced manifest root must be an object")

        manifest_id = _required_str(data, "manifest_id")
        if manifest.get("id") != manifest_id:
            raise ReviewError(
                f"manifest_id {manifest_id!r} does not match manifest id {manifest.get('id')!r}"
            )
        if acceptance.get("manifest_id") != manifest_id:
            raise ReviewError("manifest_id must match candidate acceptance metadata")
        lines.append(f"[OK] manifest_id matches: {manifest_id}")

        candidate_sha = _sha256(candidate_path)
        expected_candidate_sha = _required_str(data, "candidate_sha256").lower()
        if expected_candidate_sha != candidate_sha:
            raise ReviewError(
                f"candidate_sha256 mismatch: metadata={expected_candidate_sha} actual={candidate_sha}"
            )
        lines.append(f"[OK] candidate SHA256 matches: {candidate_sha}")

        golden_sha = _sha256(golden_path)
        expected_golden_sha = _required_str(data, "golden_fixture_sha256").lower()
        if expected_golden_sha != golden_sha:
            raise ReviewError(
                f"golden_fixture_sha256 mismatch: metadata={expected_golden_sha} actual={golden_sha}"
            )
        lines.append(f"[OK] golden fixture SHA256 matches: {golden_sha}")

        recorded_acceptance_sha = _acceptance_sha(acceptance)
        if recorded_acceptance_sha is not None:
            key, value = recorded_acceptance_sha
            if value != candidate_sha:
                raise ReviewError(
                    f"{key} in candidate acceptance metadata does not match review candidate_sha256"
                )
            lines.append(f"[OK] {key} matches review candidate_sha256")

        if _required_str(data, "validation_result") != "ready":
            raise ReviewError('validation_result must be "ready"')
        if _required_bool(data, "production_art") is not False:
            raise ReviewError("production_art must be false for candidate review")
        if _required_bool(data, "promotion_ready") is not False:
            raise ReviewError("promotion_ready must be false for candidate review")
        lines.append("[OK] validation_result ready; production_art false; promotion_ready false")

        _required_str(data, "review_version")
        _required_str(data, "review_date")
        if "reviewer" not in data:
            raise ReviewError("reviewer field must be present")
        if data.get("reviewer") is not None:
            raise ReviewError("reviewer must be null before promotion")
        _required_str(data, "review_notes")
        _validate_required_before_promotion(data)
        lines.append("[OK] review fields and promotion blockers are present")

        candidate_status, candidate_lines = candidate_validator.validate_candidate(
            acceptance_path,
            root,
        )
        if candidate_status != candidate_validator.STATUS_READY:
            lines.append("[..] candidate acceptance validator:")
            lines.extend(f"     {line}" for line in candidate_lines)
            raise ReviewError("candidate acceptance validator did not report CANDIDATE READY")
        lines.append("[OK] candidate acceptance validator reports CANDIDATE READY")

        lines.append(f"RESULT: {STATUS_VALID}")
        return STATUS_VALID, lines

    except ReviewError as e:
        lines.append(f"[FAIL] {e}")
        lines.append(f"RESULT: {STATUS_INVALID}")
        return STATUS_INVALID, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate DraftMyVan candidate review metadata.",
    )
    parser.add_argument(
        "review",
        nargs="?",
        type=Path,
        default=DEFAULT_REVIEW,
        help=(
            "Candidate review JSON (default: "
            "examples/assets/candidates/galley_1000_candidate_review.json)."
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
    status, lines = validate_review(review_path, root)
    print(os.linesep.join(lines))
    return 0 if status == STATUS_VALID else 1


if __name__ == "__main__":
    sys.exit(main())
