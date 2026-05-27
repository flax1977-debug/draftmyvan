"""Tests for candidate review metadata validation."""

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

import validate_candidate_review as r  # noqa: E402

REVIEW = (
    REPO_ROOT
    / "examples"
    / "assets"
    / "candidates"
    / "galley_1000_candidate_review.json"
)
ACCEPTANCE = (
    REPO_ROOT
    / "examples"
    / "assets"
    / "candidates"
    / "galley_1000_candidate.asset_acceptance.json"
)
CANDIDATE_GLB = REPO_ROOT / "examples" / "assets" / "candidates" / "galley_1000_candidate.glb"
MANIFEST = REPO_ROOT / "examples" / "galley_1000.json"
SCHEMA = REPO_ROOT / "manifest.schema.json"
MANIFEST_ASSET = REPO_ROOT / "examples" / "assets" / "galley_1000.glb"
GOLDEN_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "galley_1000_contract_box.glb"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _temp_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="dmv_candidate_review_"))
    (root / "examples" / "assets" / "candidates").mkdir(parents=True)
    (root / "tests" / "fixtures").mkdir(parents=True)
    shutil.copy2(SCHEMA, root / "manifest.schema.json")
    shutil.copy2(MANIFEST, root / "examples" / "galley_1000.json")
    shutil.copy2(MANIFEST_ASSET, root / "examples" / "assets" / "galley_1000.glb")
    shutil.copy2(CANDIDATE_GLB, root / "examples" / "assets" / "candidates" / "galley_1000_candidate.glb")
    shutil.copy2(ACCEPTANCE, root / "examples" / "assets" / "candidates" / "galley_1000_candidate.asset_acceptance.json")
    shutil.copy2(GOLDEN_FIXTURE, root / "tests" / "fixtures" / "galley_1000_contract_box.glb")
    return root


def _write_review(root: Path, data: dict) -> Path:
    path = root / "examples" / "assets" / "candidates" / "galley_1000_candidate_review.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _write_acceptance(root: Path, data: dict) -> Path:
    path = root / "examples" / "assets" / "candidates" / "galley_1000_candidate.asset_acceptance.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _validate_mutation(
    review_mutator,
    acceptance_mutator=None,
) -> tuple[str, str]:
    root = _temp_root()
    try:
        review = copy.deepcopy(_load_json(REVIEW))
        acceptance = copy.deepcopy(_load_json(ACCEPTANCE))
        review_mutator(review)
        if acceptance_mutator is not None:
            acceptance_mutator(acceptance)
            _write_acceptance(root, acceptance)
        review_path = _write_review(root, review)
        status, lines = r.validate_review(review_path, root)
        return status, "\n".join(lines)
    finally:
        shutil.rmtree(root)


def test_current_review_metadata_validates() -> None:
    status, lines = r.validate_review(REVIEW, REPO_ROOT)
    joined = "\n".join(lines)
    assert status == r.STATUS_VALID, joined
    assert "RESULT: CANDIDATE REVIEW VALID" in joined


def test_wrong_candidate_sha_fails() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("candidate_sha256", "0" * 64)
    )
    assert status == r.STATUS_INVALID
    assert "candidate_sha256 mismatch" in joined


def test_wrong_golden_fixture_sha_fails() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("golden_fixture_sha256", "0" * 64)
    )
    assert status == r.STATUS_INVALID
    assert "golden_fixture_sha256 mismatch" in joined


def test_wrong_manifest_id_fails() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("manifest_id", "wrong_id")
    )
    assert status == r.STATUS_INVALID
    assert "does not match manifest id" in joined


def test_missing_candidate_acceptance_metadata_fails() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__(
            "candidate_acceptance_path",
            "examples/assets/candidates/missing.asset_acceptance.json",
        )
    )
    assert status == r.STATUS_INVALID
    assert "candidate acceptance metadata does not exist" in joined


def test_review_sha_mismatch_with_acceptance_sha_fails_when_recorded() -> None:
    status, joined = _validate_mutation(
        lambda d: d,
        lambda a: a.__setitem__("candidate_sha256", "0" * 64),
    )
    assert status == r.STATUS_INVALID
    assert "candidate acceptance metadata does not match review candidate_sha256" in joined


def test_promotion_ready_true_fails() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("promotion_ready", True)
    )
    assert status == r.STATUS_INVALID
    assert "promotion_ready must be false" in joined


def test_production_art_true_fails() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("production_art", True)
    )
    assert status == r.STATUS_INVALID
    assert "production_art must be false" in joined


def test_required_before_promotion_string_fails() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("required_before_promotion", "Visual sign-off")
    )
    assert status == r.STATUS_INVALID
    assert "must be a list, not a string" in joined


def test_empty_required_before_promotion_list_fails() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("required_before_promotion", [])
    )
    assert status == r.STATUS_INVALID
    assert "must be a non-empty list" in joined


def test_missing_review_date_fails() -> None:
    def mutate(data: dict) -> None:
        data.pop("review_date")

    status, joined = _validate_mutation(mutate)
    assert status == r.STATUS_INVALID
    assert "review_date must be a non-empty string" in joined


def test_missing_review_version_fails() -> None:
    def mutate(data: dict) -> None:
        data.pop("review_version")

    status, joined = _validate_mutation(mutate)
    assert status == r.STATUS_INVALID
    assert "review_version must be a non-empty string" in joined


def test_cli_default_review_returns_0() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = r.main([])
    assert code == 0
    assert "RESULT: CANDIDATE REVIEW VALID" in buf.getvalue()


def main() -> int:
    tests = [
        test_current_review_metadata_validates,
        test_wrong_candidate_sha_fails,
        test_wrong_golden_fixture_sha_fails,
        test_wrong_manifest_id_fails,
        test_missing_candidate_acceptance_metadata_fails,
        test_review_sha_mismatch_with_acceptance_sha_fails_when_recorded,
        test_promotion_ready_true_fails,
        test_production_art_true_fails,
        test_required_before_promotion_string_fails,
        test_empty_required_before_promotion_list_fails,
        test_missing_review_date_fails,
        test_missing_review_version_fails,
        test_cli_default_review_returns_0,
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
