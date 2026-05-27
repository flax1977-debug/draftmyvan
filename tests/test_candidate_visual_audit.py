"""Tests for candidate visual audit metadata validation."""

from __future__ import annotations

import copy
import io
import json
import shutil
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "assets"))

import validate_candidate_visual_audit as v  # noqa: E402

AUDIT = (
    REPO_ROOT
    / "examples"
    / "assets"
    / "candidates"
    / "galley_1000_candidate_visual_audit.json"
)
REVIEW = (
    REPO_ROOT
    / "examples"
    / "assets"
    / "candidates"
    / "galley_1000_candidate_review.json"
)
CANDIDATE_GLB = REPO_ROOT / "examples" / "assets" / "candidates" / "galley_1000_candidate.glb"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _temp_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="dmv_candidate_visual_audit_"))
    (root / "examples" / "assets" / "candidates").mkdir(parents=True)
    shutil.copy2(CANDIDATE_GLB, root / "examples" / "assets" / "candidates" / "galley_1000_candidate.glb")
    shutil.copy2(REVIEW, root / "examples" / "assets" / "candidates" / "galley_1000_candidate_review.json")
    return root


def _write_audit(root: Path, data: dict) -> Path:
    path = root / "examples" / "assets" / "candidates" / "galley_1000_candidate_visual_audit.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _write_review(root: Path, data: dict) -> Path:
    path = root / "examples" / "assets" / "candidates" / "galley_1000_candidate_review.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _validate_mutation(audit_mutator, review_mutator=None) -> tuple[str, str]:
    root = _temp_root()
    try:
        audit = copy.deepcopy(_load_json(AUDIT))
        review = copy.deepcopy(_load_json(REVIEW))
        audit_mutator(audit)
        if review_mutator is not None:
            review_mutator(review)
            _write_review(root, review)
        audit_path = _write_audit(root, audit)
        status, lines = v.validate_visual_audit(audit_path, root)
        return status, "\n".join(lines)
    finally:
        shutil.rmtree(root)


def test_current_visual_audit_validates() -> None:
    status, lines = v.validate_visual_audit(AUDIT, REPO_ROOT)
    joined = "\n".join(lines)
    assert status == v.STATUS_VALID, joined
    assert "RESULT: CANDIDATE VISUAL AUDIT VALID" in joined


def test_wrong_candidate_sha_fails() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("candidate_sha256", "0" * 64)
    )
    assert status == v.STATUS_INVALID
    assert "candidate_sha256 mismatch" in joined


def test_mismatch_with_candidate_review_sha_fails() -> None:
    status, joined = _validate_mutation(
        lambda d: d,
        lambda r: r.__setitem__("candidate_sha256", "0" * 64),
    )
    assert status == v.STATUS_INVALID
    assert "candidate_sha256 must match candidate review metadata" in joined


def test_promotion_recommendation_must_be_do_not_promote() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("promotion_recommendation", "promote")
    )
    assert status == v.STATUS_INVALID
    assert "promotion_recommendation must be" in joined


def test_visual_status_must_be_not_production_ready() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("visual_status", "production_ready")
    )
    assert status == v.STATUS_INVALID
    assert "visual_status must be" in joined


def test_empty_findings_fails() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("findings", [])
    )
    assert status == v.STATUS_INVALID
    assert "findings must be a non-empty list" in joined


def test_findings_as_string_fails() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("findings", "No renders yet")
    )
    assert status == v.STATUS_INVALID
    assert "findings must be a list, not a string" in joined


def test_empty_required_visual_improvements_fails() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("required_visual_improvements", [])
    )
    assert status == v.STATUS_INVALID
    assert "required_visual_improvements must be a non-empty list" in joined


def test_missing_audit_date_fails() -> None:
    def mutate(data: dict) -> None:
        data.pop("audit_date")

    status, joined = _validate_mutation(mutate)
    assert status == v.STATUS_INVALID
    assert "audit_date must be a non-empty string" in joined


def test_missing_audit_version_fails() -> None:
    def mutate(data: dict) -> None:
        data.pop("audit_version")

    status, joined = _validate_mutation(mutate)
    assert status == v.STATUS_INVALID
    assert "audit_version must be a non-empty string" in joined


def test_cli_default_visual_audit_returns_0() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = v.main([])
    assert code == 0
    assert "RESULT: CANDIDATE VISUAL AUDIT VALID" in buf.getvalue()


def main() -> int:
    tests = [
        test_current_visual_audit_validates,
        test_wrong_candidate_sha_fails,
        test_mismatch_with_candidate_review_sha_fails,
        test_promotion_recommendation_must_be_do_not_promote,
        test_visual_status_must_be_not_production_ready,
        test_empty_findings_fails,
        test_findings_as_string_fails,
        test_empty_required_visual_improvements_fails,
        test_missing_audit_date_fails,
        test_missing_audit_version_fails,
        test_cli_default_visual_audit_returns_0,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"ERROR {t.__name__}: {e}")
    print()
    print(f"{len(tests) - failed}/{len(tests)} passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
