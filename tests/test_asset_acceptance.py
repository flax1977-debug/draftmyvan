"""Tests for asset acceptance metadata.

These tests keep the future fixture-swap boundary explicit. The generated
contract box is now a permanent golden fixture under `tests/fixtures/`,
while `examples/assets/galley_1000.glb` is the current manifest asset.
"""

from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "assets"))

import validate_asset_acceptance as a  # noqa: E402

METADATA = REPO_ROOT / "examples" / "assets" / "galley_1000.asset_acceptance.json"
GOLDEN_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "galley_1000_contract_box.glb"
MANIFEST_ASSET = REPO_ROOT / "examples" / "assets" / "galley_1000.glb"


def _load_metadata() -> dict:
    with METADATA.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validate_temp_metadata(data: dict, root: Path = REPO_ROOT) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="dmv_acceptance_") as td:
        path = Path(td) / "asset_acceptance.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        ok, lines = a.validate_metadata(path, root)
        return ok, "\n".join(lines)


def test_current_asset_acceptance_metadata_is_valid() -> None:
    ok, lines = a.validate_metadata(METADATA, REPO_ROOT)
    joined = "\n".join(lines)
    assert ok, joined
    assert "RESULT: ASSET ACCEPTANCE VALID" in joined
    assert "[OK] current manifest asset matches golden generated fixture bytes" in joined


def test_golden_contract_fixture_exists_and_matches_current_asset_for_now() -> None:
    assert GOLDEN_FIXTURE.exists()
    assert MANIFEST_ASSET.exists()
    assert GOLDEN_FIXTURE.read_bytes() == MANIFEST_ASSET.read_bytes()


def test_metadata_requires_manifest_id_to_match_manifest() -> None:
    data = _load_metadata()
    data["manifest_id"] = "wrong_id"
    ok, joined = _validate_temp_metadata(data)
    assert ok is False
    assert "does not match manifest id" in joined


def test_metadata_requires_existing_asset_path() -> None:
    data = _load_metadata()
    data["asset_path"] = "examples/assets/missing.glb"
    ok, joined = _validate_temp_metadata(data)
    assert ok is False
    assert "asset does not exist" in joined


def test_metadata_asset_path_must_match_manifest_visual_glb_path() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="dmv_asset_path_"))
    try:
        manifest_dir = tmp / "examples"
        asset_dir = manifest_dir / "assets"
        fixture_dir = tmp / "tests" / "fixtures"
        asset_dir.mkdir(parents=True)
        fixture_dir.mkdir(parents=True)
        shutil.copy2(REPO_ROOT / "examples" / "galley_1000.json", manifest_dir / "galley_1000.json")
        shutil.copy2(MANIFEST_ASSET, asset_dir / "galley_1000.glb")
        shutil.copy2(MANIFEST_ASSET, asset_dir / "other.glb")
        shutil.copy2(GOLDEN_FIXTURE, fixture_dir / "galley_1000_contract_box.glb")

        data = _load_metadata()
        data["asset_path"] = "examples/assets/other.glb"
        ok, joined = _validate_temp_metadata(data, root=tmp)
        assert ok is False
        assert "asset_path must match manifest visual.glb_path" in joined
    finally:
        shutil.rmtree(tmp)


def test_metadata_requires_full_gate_list() -> None:
    data = _load_metadata()
    data["required_checks"] = ["schema", "dimensions", "floor_back_left_anchor"]
    ok, joined = _validate_temp_metadata(data)
    assert ok is False
    assert "material_slots" in joined
    assert "collision_proxy" in joined


def test_metadata_requires_validator_command() -> None:
    data = _load_metadata()
    data["validator_command"] = ""
    ok, joined = _validate_temp_metadata(data)
    assert ok is False
    assert "validator_command" in joined


def test_generated_fixture_state_requires_not_replaced() -> None:
    data = _load_metadata()
    data["generated_fixture_replaced"] = True
    ok, joined = _validate_temp_metadata(data)
    assert ok is False
    assert "generated_fixture_replaced must be false" in joined


def test_generated_fixture_state_requires_not_production_art() -> None:
    data = _load_metadata()
    data["human_signoff"]["production_art"] = True
    ok, joined = _validate_temp_metadata(data)
    assert ok is False
    assert "production_art must be false" in joined


def test_generated_fixture_state_requires_null_reviewer() -> None:
    data = _load_metadata()
    data["human_signoff"]["reviewer"] = "someone"
    ok, joined = _validate_temp_metadata(data)
    assert ok is False
    assert "reviewer must be null" in joined


def test_generated_fixture_metadata_requires_matching_golden_bytes() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="dmv_asset_bytes_"))
    try:
        manifest_dir = tmp / "examples"
        asset_dir = manifest_dir / "assets"
        fixture_dir = tmp / "tests" / "fixtures"
        asset_dir.mkdir(parents=True)
        fixture_dir.mkdir(parents=True)
        shutil.copy2(REPO_ROOT / "examples" / "galley_1000.json", manifest_dir / "galley_1000.json")
        (asset_dir / "galley_1000.glb").write_bytes(b"not the golden fixture")
        shutil.copy2(GOLDEN_FIXTURE, fixture_dir / "galley_1000_contract_box.glb")

        ok, joined = _validate_temp_metadata(_load_metadata(), root=tmp)
        assert ok is False
        assert "bytes differ from the golden fixture" in joined
    finally:
        shutil.rmtree(tmp)


def test_cli_default_metadata_returns_0() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = a.main([])
    assert code == 0
    assert "RESULT: ASSET ACCEPTANCE VALID" in buf.getvalue()


def main() -> int:
    tests = [
        test_current_asset_acceptance_metadata_is_valid,
        test_golden_contract_fixture_exists_and_matches_current_asset_for_now,
        test_metadata_requires_manifest_id_to_match_manifest,
        test_metadata_requires_existing_asset_path,
        test_metadata_asset_path_must_match_manifest_visual_glb_path,
        test_metadata_requires_full_gate_list,
        test_metadata_requires_validator_command,
        test_generated_fixture_state_requires_not_replaced,
        test_generated_fixture_state_requires_not_production_art,
        test_generated_fixture_state_requires_null_reviewer,
        test_generated_fixture_metadata_requires_matching_golden_bytes,
        test_cli_default_metadata_returns_0,
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
