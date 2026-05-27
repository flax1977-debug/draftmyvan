"""Tests for asset-acceptance metadata.

These tests keep process metadata separate from the manifest schema while
making sure the current manifest asset cannot silently become production art.
The golden generated box remains pinned in `tests/fixtures/`; the manifest
asset must also keep passing every existing gate.
"""

from __future__ import annotations

import copy
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "assets"))

import validate_asset_acceptance as vaa  # noqa: E402

METADATA_PATH = REPO_ROOT / "examples" / "assets" / "galley_1000.asset_acceptance.json"
MANIFEST_PATH = REPO_ROOT / "examples" / "galley_1000.json"
ASSET_PATH = REPO_ROOT / "examples" / "assets" / "galley_1000.glb"


def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _metadata() -> dict:
    return _load(METADATA_PATH)


def _errors_after(mutator) -> list[str]:
    data = copy.deepcopy(_metadata())
    mutator(data)
    return vaa.validate_metadata(data, root=REPO_ROOT)


def _assert_error_contains(errors: list[str], text: str) -> None:
    assert any(text in e for e in errors), f"expected {text!r} in errors: {errors}"


def test_committed_acceptance_metadata_validates() -> None:
    errors = vaa.validate_file(METADATA_PATH, root=REPO_ROOT)
    assert errors == [], errors


def test_metadata_references_existing_manifest_and_asset() -> None:
    data = _metadata()
    assert (REPO_ROOT / data["manifest_path"]).resolve() == MANIFEST_PATH
    assert (REPO_ROOT / data["asset_path"]).resolve() == ASSET_PATH
    assert MANIFEST_PATH.is_file()
    assert ASSET_PATH.is_file()


def test_manifest_id_matches_manifest_file() -> None:
    data = _metadata()
    manifest = _load(REPO_ROOT / data["manifest_path"])
    assert data["manifest_id"] == manifest["id"]


def test_asset_path_matches_manifest_visual_glb_path() -> None:
    data = _metadata()
    manifest = _load(REPO_ROOT / data["manifest_path"])
    expected = (MANIFEST_PATH.parent / manifest["visual"]["glb_path"]).resolve()
    assert (REPO_ROOT / data["asset_path"]).resolve() == expected


def test_manifest_id_mismatch_fails() -> None:
    errors = _errors_after(lambda d: d.__setitem__("manifest_id", "wrong_id"))
    _assert_error_contains(errors, "does not match manifest id")


def test_missing_manifest_reference_fails() -> None:
    errors = _errors_after(lambda d: d.__setitem__("manifest_path", "examples/missing.json"))
    _assert_error_contains(errors, "manifest_path does not exist")


def test_missing_asset_reference_fails() -> None:
    errors = _errors_after(lambda d: d.__setitem__("asset_path", "examples/assets/missing.glb"))
    _assert_error_contains(errors, "asset_path does not exist")


def test_asset_path_mismatch_fails() -> None:
    errors = _errors_after(lambda d: d.__setitem__("asset_path", "examples/assets/other.glb"))
    _assert_error_contains(errors, "asset_path must match manifest visual.glb_path")


def test_validator_command_is_required() -> None:
    errors = _errors_after(lambda d: d.__setitem__("validator_command", ""))
    _assert_error_contains(errors, "validator_command")


def test_required_checks_include_full_gate_list() -> None:
    data = _metadata()
    assert vaa.REQUIRED_CHECKS <= set(data["required_checks"])

    errors = _errors_after(lambda d: d["required_checks"].remove("collision_proxy"))
    _assert_error_contains(errors, "required_checks missing gate")


def test_generated_fixture_replaced_must_be_false_for_now() -> None:
    errors = _errors_after(lambda d: d.__setitem__("generated_fixture_replaced", True))
    _assert_error_contains(errors, "generated_fixture_replaced must be false")


def test_asset_kind_is_generated_contract_fixture_for_now() -> None:
    errors = _errors_after(lambda d: d.__setitem__("asset_kind", "production_art"))
    _assert_error_contains(errors, "asset_kind must be")


def test_production_art_must_be_false_for_now() -> None:
    errors = _errors_after(lambda d: d["human_signoff"].__setitem__("production_art", True))
    _assert_error_contains(errors, "production_art must be false")


def test_cli_all_validates_committed_metadata() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = vaa.main(["--all", "--root", str(REPO_ROOT)])
    assert code == 0
    out = buf.getvalue()
    assert "galley_1000.asset_acceptance.json" in out
    assert "1/1 valid" in out


def main() -> int:
    tests = [
        test_committed_acceptance_metadata_validates,
        test_metadata_references_existing_manifest_and_asset,
        test_manifest_id_matches_manifest_file,
        test_asset_path_matches_manifest_visual_glb_path,
        test_manifest_id_mismatch_fails,
        test_missing_manifest_reference_fails,
        test_missing_asset_reference_fails,
        test_asset_path_mismatch_fails,
        test_validator_command_is_required,
        test_required_checks_include_full_gate_list,
        test_generated_fixture_replaced_must_be_false_for_now,
        test_asset_kind_is_generated_contract_fixture_for_now,
        test_production_art_must_be_false_for_now,
        test_cli_all_validates_committed_metadata,
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
