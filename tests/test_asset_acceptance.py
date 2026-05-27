"""Tests for tools/assets/validate_asset_acceptance.py.

Pure Python, stdlib only. Exercises:

  * The current committed metadata
    (``examples/assets/galley_1000.asset_acceptance.json``) validates.
  * Each invariant the validator enforces fires when violated:
      - missing manifest, missing asset
      - manifest_id / manifest mismatch
      - missing validator_command
      - required_checks incomplete
      - generated_fixture_replaced=true (no real art yet)
      - production_art=true (no real art yet)
      - human_signoff incomplete
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

import validate_asset_acceptance as v  # noqa: E402

COMMITTED_METADATA = (
    REPO_ROOT / "examples" / "assets" / "galley_1000.asset_acceptance.json"
)
SAMPLE_MANIFEST = REPO_ROOT / "examples" / "galley_1000.json"
MANIFEST_ASSET = REPO_ROOT / "examples" / "assets" / "galley_1000.glb"


def _load_committed() -> dict:
    with COMMITTED_METADATA.open("r", encoding="utf-8") as f:
        return json.load(f)


def _build_repo(tmp: Path, metadata: dict) -> Path:
    """Materialise a minimal repo tree under ``tmp`` and write `metadata`
    to ``examples/assets/galley_1000.asset_acceptance.json``. Returns
    that metadata path.
    """
    (tmp / "examples" / "assets").mkdir(parents=True, exist_ok=True)
    # Copy the real manifest and asset across so resolution succeeds
    # unless a test explicitly mutates them.
    shutil.copy(SAMPLE_MANIFEST, tmp / "examples" / "galley_1000.json")
    shutil.copy(MANIFEST_ASSET, tmp / "examples" / "assets" / "galley_1000.glb")
    meta_path = tmp / "examples" / "assets" / "galley_1000.asset_acceptance.json"
    meta_path.write_text(json.dumps(metadata), encoding="utf-8")
    return meta_path


# ---------------------------------------------------------------------------
# Happy path on the real committed metadata
# ---------------------------------------------------------------------------

def test_committed_metadata_validates() -> None:
    ok, lines = v.validate_file(COMMITTED_METADATA)
    assert ok, "\n".join(lines)
    joined = "\n".join(lines)
    assert "manifest exists" in joined
    assert "manifest_id matches" in joined
    assert "asset exists" in joined
    assert "validator_command present" in joined
    assert "required_checks covers the full gate list" in joined
    assert "generated_fixture_replaced is false" in joined
    assert "human_signoff.production_art is false" in joined


def test_committed_metadata_lists_full_required_check_set() -> None:
    data = _load_committed()
    declared = set(data["required_checks"])
    for required in v.REQUIRED_CHECKS:
        assert required in declared, (
            f"committed metadata is missing required check {required!r}"
        )


def test_committed_metadata_records_asset_kind_as_generated_contract_fixture() -> None:
    data = _load_committed()
    assert data["asset_kind"] == "generated_contract_fixture", (
        "while no real art exists, asset_kind must be "
        "'generated_contract_fixture' so the phase invariant is explicit"
    )


# ---------------------------------------------------------------------------
# Synthetic tree — invariants fire on violation
# ---------------------------------------------------------------------------

def test_missing_top_level_key_fails() -> None:
    base = _load_committed()
    del base["validator_command"]
    tmp = Path(tempfile.mkdtemp(prefix="acc_"))
    try:
        meta_path = _build_repo(tmp, base)
        ok, lines = v.validate_file(meta_path, repo_root=tmp)
        assert ok is False
        joined = "\n".join(lines)
        assert "missing required key" in joined
        assert "validator_command" in joined
    finally:
        shutil.rmtree(tmp)


def test_missing_manifest_fails() -> None:
    base = _load_committed()
    tmp = Path(tempfile.mkdtemp(prefix="acc_"))
    try:
        meta_path = _build_repo(tmp, base)
        # Remove the manifest from the synthetic repo.
        (tmp / "examples" / "galley_1000.json").unlink()
        ok, lines = v.validate_file(meta_path, repo_root=tmp)
        assert ok is False
        joined = "\n".join(lines)
        assert "manifest path does not exist" in joined
    finally:
        shutil.rmtree(tmp)


def test_missing_asset_fails() -> None:
    base = _load_committed()
    tmp = Path(tempfile.mkdtemp(prefix="acc_"))
    try:
        meta_path = _build_repo(tmp, base)
        (tmp / "examples" / "assets" / "galley_1000.glb").unlink()
        ok, lines = v.validate_file(meta_path, repo_root=tmp)
        assert ok is False
        joined = "\n".join(lines)
        assert "asset_path does not exist" in joined
    finally:
        shutil.rmtree(tmp)


def test_manifest_id_mismatch_fails() -> None:
    base = _load_committed()
    base["manifest_id"] = "wrong_id"
    tmp = Path(tempfile.mkdtemp(prefix="acc_"))
    try:
        meta_path = _build_repo(tmp, base)
        ok, lines = v.validate_file(meta_path, repo_root=tmp)
        assert ok is False
        joined = "\n".join(lines)
        assert "manifest_id" in joined and "!=" in joined
    finally:
        shutil.rmtree(tmp)


def test_empty_validator_command_fails() -> None:
    base = _load_committed()
    base["validator_command"] = "   "
    tmp = Path(tempfile.mkdtemp(prefix="acc_"))
    try:
        meta_path = _build_repo(tmp, base)
        ok, lines = v.validate_file(meta_path, repo_root=tmp)
        assert ok is False
        joined = "\n".join(lines)
        assert "validator_command must be a non-empty string" in joined
    finally:
        shutil.rmtree(tmp)


def test_required_checks_missing_a_gate_fails() -> None:
    base = _load_committed()
    base["required_checks"] = ["schema", "dimensions"]  # missing the rest
    tmp = Path(tempfile.mkdtemp(prefix="acc_"))
    try:
        meta_path = _build_repo(tmp, base)
        ok, lines = v.validate_file(meta_path, repo_root=tmp)
        assert ok is False
        joined = "\n".join(lines)
        assert "required_checks missing" in joined
        for gate in ("floor_back_left_anchor", "material_slots", "collision_proxy"):
            assert gate in joined
    finally:
        shutil.rmtree(tmp)


def test_generated_fixture_replaced_true_fails_for_now() -> None:
    base = _load_committed()
    base["generated_fixture_replaced"] = True
    tmp = Path(tempfile.mkdtemp(prefix="acc_"))
    try:
        meta_path = _build_repo(tmp, base)
        ok, lines = v.validate_file(meta_path, repo_root=tmp)
        assert ok is False
        joined = "\n".join(lines)
        assert "generated_fixture_replaced must be false for now" in joined
    finally:
        shutil.rmtree(tmp)


def test_production_art_true_fails_for_now() -> None:
    base = _load_committed()
    base["human_signoff"]["production_art"] = True
    tmp = Path(tempfile.mkdtemp(prefix="acc_"))
    try:
        meta_path = _build_repo(tmp, base)
        ok, lines = v.validate_file(meta_path, repo_root=tmp)
        assert ok is False
        joined = "\n".join(lines)
        assert "production_art" in joined
        assert "must be false for now" in joined
    finally:
        shutil.rmtree(tmp)


def test_human_signoff_missing_keys_fails() -> None:
    base = _load_committed()
    del base["human_signoff"]["reviewer"]
    tmp = Path(tempfile.mkdtemp(prefix="acc_"))
    try:
        meta_path = _build_repo(tmp, base)
        ok, lines = v.validate_file(meta_path, repo_root=tmp)
        assert ok is False
        joined = "\n".join(lines)
        assert "human_signoff missing key" in joined
        assert "reviewer" in joined
    finally:
        shutil.rmtree(tmp)


def test_unreadable_metadata_fails() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="acc_"))
    try:
        bad = tmp / "broken.asset_acceptance.json"
        bad.write_text("{not: valid", encoding="utf-8")
        ok, lines = v.validate_file(bad, repo_root=tmp)
        assert ok is False
        joined = "\n".join(lines)
        assert "unreadable" in joined or "not JSON" in joined
    finally:
        shutil.rmtree(tmp)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_cli_all_succeeds_on_real_repo() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = v.main(["--all"])
    out = buf.getvalue()
    assert code == 0, out
    assert "1/1 valid" in out


def test_cli_explicit_path_succeeds() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = v.main([str(COMMITTED_METADATA)])
    out = buf.getvalue()
    assert code == 0, out


def main() -> int:
    tests = [
        test_committed_metadata_validates,
        test_committed_metadata_lists_full_required_check_set,
        test_committed_metadata_records_asset_kind_as_generated_contract_fixture,
        test_missing_top_level_key_fails,
        test_missing_manifest_fails,
        test_missing_asset_fails,
        test_manifest_id_mismatch_fails,
        test_empty_validator_command_fails,
        test_required_checks_missing_a_gate_fails,
        test_generated_fixture_replaced_true_fails_for_now,
        test_production_art_true_fails_for_now,
        test_human_signoff_missing_keys_fails,
        test_unreadable_metadata_fails,
        test_cli_all_succeeds_on_real_repo,
        test_cli_explicit_path_succeeds,
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
