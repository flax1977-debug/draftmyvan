"""Tests for candidate human visual review metadata validation."""

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

import validate_human_visual_review as h  # noqa: E402

REVIEW = (
    REPO_ROOT
    / "examples"
    / "assets"
    / "candidates"
    / "galley_1000_candidate_human_visual_review.json"
)
RENDER_EVIDENCE = (
    REPO_ROOT
    / "examples"
    / "assets"
    / "candidates"
    / "galley_1000_candidate_render_evidence.json"
)
VISUAL_AUDIT = (
    REPO_ROOT
    / "examples"
    / "assets"
    / "candidates"
    / "galley_1000_candidate_visual_audit.json"
)
CANDIDATE_GLB = REPO_ROOT / "examples" / "assets" / "candidates" / "galley_1000_candidate.glb"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _temp_root(
    *,
    include_render_evidence: bool = True,
    include_visual_audit: bool = True,
) -> Path:
    root = Path(tempfile.mkdtemp(prefix="dmv_human_visual_review_"))
    (root / "examples" / "assets" / "candidates").mkdir(parents=True)
    shutil.copy2(CANDIDATE_GLB, root / "examples" / "assets" / "candidates" / "galley_1000_candidate.glb")
    if include_render_evidence:
        shutil.copy2(
            RENDER_EVIDENCE,
            root
            / "examples"
            / "assets"
            / "candidates"
            / "galley_1000_candidate_render_evidence.json",
        )
    if include_visual_audit:
        shutil.copy2(
            VISUAL_AUDIT,
            root
            / "examples"
            / "assets"
            / "candidates"
            / "galley_1000_candidate_visual_audit.json",
        )
    return root


def _write_review(root: Path, data: dict) -> Path:
    path = root / "examples" / "assets" / "candidates" / "galley_1000_candidate_human_visual_review.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _validate_mutation(
    mutator,
    *,
    include_render_evidence: bool = True,
    include_visual_audit: bool = True,
) -> tuple[str, str]:
    root = _temp_root(
        include_render_evidence=include_render_evidence,
        include_visual_audit=include_visual_audit,
    )
    try:
        data = copy.deepcopy(_load_json(REVIEW))
        mutator(data)
        review_path = _write_review(root, data)
        status, lines = h.validate_human_visual_review(review_path, root)
        return status, "\n".join(lines)
    finally:
        shutil.rmtree(root)


def test_current_metadata_validates() -> None:
    status, lines = h.validate_human_visual_review(REVIEW, REPO_ROOT)
    joined = "\n".join(lines)
    assert status == h.STATUS_VALID, joined
    assert "RESULT: HUMAN VISUAL REVIEW VALID" in joined


def test_wrong_candidate_sha_fails() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("candidate_sha256", "0" * 64)
    )
    assert status == h.STATUS_INVALID
    assert "candidate_sha256 mismatch" in joined


def test_missing_render_evidence_metadata_fails() -> None:
    status, joined = _validate_mutation(lambda d: d, include_render_evidence=False)
    assert status == h.STATUS_INVALID
    assert "render evidence metadata does not exist" in joined


def test_missing_visual_audit_metadata_fails() -> None:
    status, joined = _validate_mutation(lambda d: d, include_visual_audit=False)
    assert status == h.STATUS_INVALID
    assert "visual audit metadata does not exist" in joined


def test_production_art_true_fails() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("production_art", True)
    )
    assert status == h.STATUS_INVALID
    assert "production_art must be false" in joined


def test_promotion_ready_true_fails() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("promotion_ready", True)
    )
    assert status == h.STATUS_INVALID
    assert "promotion_ready must be false" in joined


def test_promotion_recommendation_must_be_do_not_promote() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("promotion_recommendation", "promote")
    )
    assert status == h.STATUS_INVALID
    assert "promotion_recommendation must be" in joined


def test_missing_one_view_observation_fails() -> None:
    def mutate(data: dict) -> None:
        del data["view_observations"]["front"]

    status, joined = _validate_mutation(mutate)
    assert status == h.STATUS_INVALID
    assert "view_observations is missing: front" in joined


def test_empty_strengths_fails() -> None:
    status, joined = _validate_mutation(lambda d: d.__setitem__("strengths", []))
    assert status == h.STATUS_INVALID
    assert "strengths must be a non-empty list" in joined


def test_empty_weaknesses_fails() -> None:
    status, joined = _validate_mutation(lambda d: d.__setitem__("weaknesses", []))
    assert status == h.STATUS_INVALID
    assert "weaknesses must be a non-empty list" in joined


def test_required_before_promotion_as_string_fails() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("required_before_promotion", "Visual sign-off")
    )
    assert status == h.STATUS_INVALID
    assert "required_before_promotion must be a list, not a string" in joined


def test_missing_review_date_fails() -> None:
    def mutate(data: dict) -> None:
        data.pop("review_date")

    status, joined = _validate_mutation(mutate)
    assert status == h.STATUS_INVALID
    assert "review_date must be a non-empty string" in joined


def test_missing_review_version_fails() -> None:
    def mutate(data: dict) -> None:
        data.pop("review_version")

    status, joined = _validate_mutation(mutate)
    assert status == h.STATUS_INVALID
    assert "review_version must be a non-empty string" in joined


def test_cli_default_human_visual_review_returns_0() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = h.main([])
    assert code == 0
    assert "RESULT: HUMAN VISUAL REVIEW VALID" in buf.getvalue()


def main() -> int:
    tests = [
        test_current_metadata_validates,
        test_wrong_candidate_sha_fails,
        test_missing_render_evidence_metadata_fails,
        test_missing_visual_audit_metadata_fails,
        test_production_art_true_fails,
        test_promotion_ready_true_fails,
        test_promotion_recommendation_must_be_do_not_promote,
        test_missing_one_view_observation_fails,
        test_empty_strengths_fails,
        test_empty_weaknesses_fails,
        test_required_before_promotion_as_string_fails,
        test_missing_review_date_fails,
        test_missing_review_version_fails,
        test_cli_default_human_visual_review_returns_0,
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
