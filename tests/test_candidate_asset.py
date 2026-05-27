"""Tests for candidate asset metadata and validation.

Candidate assets are process tests for the Blender export workflow. They are
not production assets, and this suite keeps that boundary explicit.
"""

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

import validate_candidate_asset as c  # noqa: E402

METADATA = (
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


def _load_metadata() -> dict:
    with METADATA.open("r", encoding="utf-8") as f:
        return json.load(f)


def _temp_root(*, include_candidate: bool = True) -> Path:
    root = Path(tempfile.mkdtemp(prefix="dmv_candidate_"))
    (root / "examples" / "assets" / "candidates").mkdir(parents=True)
    (root / "tests" / "fixtures").mkdir(parents=True)
    shutil.copy2(SCHEMA, root / "manifest.schema.json")
    shutil.copy2(MANIFEST, root / "examples" / "galley_1000.json")
    shutil.copy2(MANIFEST_ASSET, root / "examples" / "assets" / "galley_1000.glb")
    shutil.copy2(GOLDEN_FIXTURE, root / "tests" / "fixtures" / "galley_1000_contract_box.glb")
    if include_candidate:
        shutil.copy2(CANDIDATE_GLB, root / "examples" / "assets" / "candidates" / "galley_1000_candidate.glb")
    return root


def _write_metadata(root: Path, data: dict) -> Path:
    path = root / "examples" / "assets" / "candidates" / "galley_1000_candidate.asset_acceptance.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _validate_mutation(mutator, *, include_candidate: bool = True) -> tuple[str, str]:
    root = _temp_root(include_candidate=include_candidate)
    try:
        data = copy.deepcopy(_load_metadata())
        mutator(data)
        metadata = _write_metadata(root, data)
        status, lines = c.validate_candidate(metadata, root)
        return status, "\n".join(lines)
    finally:
        shutil.rmtree(root)


def test_candidate_metadata_validates_ready() -> None:
    status, lines = c.validate_candidate(METADATA, REPO_ROOT)
    joined = "\n".join(lines)
    assert status == c.STATUS_READY, joined
    assert "RESULT: CANDIDATE READY" in joined
    assert "RESULT: PASS" in joined


def test_candidate_plan_only_state_is_explicit_without_glb() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("candidate_asset_expected", False),
        include_candidate=False,
    )
    assert status == c.STATUS_PLAN_ONLY, joined
    assert "RESULT: CANDIDATE PLAN ONLY" in joined


def test_candidate_missing_glb_is_invalid_when_expected() -> None:
    status, joined = _validate_mutation(lambda d: d, include_candidate=False)
    assert status == c.STATUS_INVALID
    assert "candidate asset does not exist" in joined


def test_candidate_rejects_missing_manifest() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("manifest_path", "examples/missing.json")
    )
    assert status == c.STATUS_INVALID
    assert "manifest does not exist" in joined


def test_candidate_rejects_mismatched_manifest_id() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("manifest_id", "wrong_id")
    )
    assert status == c.STATUS_INVALID
    assert "does not match manifest id" in joined


def test_candidate_rejects_missing_required_checks() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("required_checks", ["schema", "dimensions"])
    )
    assert status == c.STATUS_INVALID
    assert "floor_back_left_anchor" in joined
    assert "material_slots" in joined
    assert "collision_proxy" in joined


def test_candidate_cannot_claim_production_art() -> None:
    status, joined = _validate_mutation(lambda d: d.__setitem__("production_art", True))
    assert status == c.STATUS_INVALID
    assert "production_art must be false" in joined


def test_candidate_cannot_allow_promotion_yet() -> None:
    status, joined = _validate_mutation(lambda d: d.__setitem__("promotion_allowed", True))
    assert status == c.STATUS_INVALID
    assert "promotion_allowed must be false" in joined


def test_candidate_signoff_cannot_claim_review() -> None:
    def mutate(data: dict) -> None:
        data["human_signoff"]["visual_reviewed"] = True
        data["human_signoff"]["reviewer"] = "reviewer"

    status, joined = _validate_mutation(mutate)
    assert status == c.STATUS_INVALID
    assert "visual_reviewed must be false" in joined


def test_candidate_glb_is_distinct_from_golden_fixture() -> None:
    assert CANDIDATE_GLB.exists()
    assert CANDIDATE_GLB.read_bytes() != GOLDEN_FIXTURE.read_bytes()


def test_golden_fixture_remains_untouched() -> None:
    assert GOLDEN_FIXTURE.exists()
    assert MANIFEST_ASSET.read_bytes() == GOLDEN_FIXTURE.read_bytes()


def test_examples_asset_remains_manifest_asset() -> None:
    with MANIFEST.open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["visual"]["glb_path"] == "assets/galley_1000.glb"
    assert (MANIFEST.parent / manifest["visual"]["glb_path"]).resolve() == MANIFEST_ASSET
    assert _load_metadata()["target_asset_path"] == "examples/assets/galley_1000.glb"


def test_cli_default_candidate_returns_0() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = c.main([])
    assert code == 0
    assert "RESULT: CANDIDATE READY" in buf.getvalue()


def main() -> int:
    tests = [
        test_candidate_metadata_validates_ready,
        test_candidate_plan_only_state_is_explicit_without_glb,
        test_candidate_missing_glb_is_invalid_when_expected,
        test_candidate_rejects_missing_manifest,
        test_candidate_rejects_mismatched_manifest_id,
        test_candidate_rejects_missing_required_checks,
        test_candidate_cannot_claim_production_art,
        test_candidate_cannot_allow_promotion_yet,
        test_candidate_signoff_cannot_claim_review,
        test_candidate_glb_is_distinct_from_golden_fixture,
        test_golden_fixture_remains_untouched,
        test_examples_asset_remains_manifest_asset,
        test_cli_default_candidate_returns_0,
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
