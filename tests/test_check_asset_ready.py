"""Tests for tools/blender/check_asset_ready.py — pure Python only."""

from __future__ import annotations

import copy
import io
import json
import shutil
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "blender"))

import check_asset_ready as car  # noqa: E402

SAMPLE_MANIFEST = REPO_ROOT / "examples" / "galley_1000.json"
FIXTURE_GLB = REPO_ROOT / "examples" / "assets" / "galley_1000.glb"


def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _temp_manifest(mutator) -> Path:
    src = _load(SAMPLE_MANIFEST)
    mutator(src)
    fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="manifest_")
    Path(tmp_path).write_text(json.dumps(src), encoding="utf-8")
    return Path(tmp_path)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_committed_fixture_reports_ready() -> None:
    code, lines = car.check(SAMPLE_MANIFEST, FIXTURE_GLB)
    joined = "\n".join(lines)
    assert code == 0, joined
    assert "RESULT: READY" in joined
    assert "[OK]   Manifest readable" in joined
    assert "[OK]   Manifest schema validates" in joined
    assert "[OK]   GLB file exists" in joined


def test_default_glb_path_derived_from_manifest() -> None:
    # Don't pass --glb; the helper should derive
    # examples/assets/galley_1000.glb from the manifest.
    code, lines = car.check(SAMPLE_MANIFEST, glb_path=None)
    joined = "\n".join(lines)
    assert code == 0, joined
    assert "GLB path defaulted to" in joined
    assert "examples/assets/galley_1000.glb" in joined


# ---------------------------------------------------------------------------
# Failure paths — clear messages, exit 1
# ---------------------------------------------------------------------------

def test_missing_glb_file_reports_not_ready_with_hint() -> None:
    code, lines = car.check(SAMPLE_MANIFEST, Path("/tmp/does_not_exist.glb"))
    joined = "\n".join(lines)
    assert code == 1, joined
    assert "GLB file not found" in joined
    assert "RESULT: NOT READY" in joined
    assert "EXPORT_REAL_ASSET.md" in joined


def test_wrong_size_glb_reports_not_ready() -> None:
    # Build a synthetic GLB that is 5 mm too wide.
    sys.path.insert(0, str(REPO_ROOT / "tools" / "assets"))
    import generate_galley_fixture_glb as gen  # noqa: E402
    manifest = _load(SAMPLE_MANIFEST)
    manifest["dimensions_mm"] = {"width": 1005, "depth": 520, "height": 900}
    blob = gen.make_box_glb_from_manifest(manifest)
    # But validate against the *real* manifest (width=1000) → 5 mm drift.
    with tempfile.TemporaryDirectory() as td:
        glb_path = Path(td) / "galley_1000.glb"
        glb_path.write_bytes(blob)
        code, lines = car.check(SAMPLE_MANIFEST, glb_path)
        joined = "\n".join(lines)
        assert code == 1, joined
        assert "RESULT: NOT READY" in joined
        assert "FAIL" in joined and "width" in joined


def test_manifest_schema_failure_reports_not_ready() -> None:
    # Manifest with an invalid id (capitals) — schema should reject.
    bad_manifest = _temp_manifest(lambda m: m.update({"id": "GALLEY_1000"}))
    try:
        # Even with no GLB at all, the schema check must fire first.
        code, lines = car.check(bad_manifest, glb_path=None)
        joined = "\n".join(lines)
        assert code == 1, joined
        assert "Manifest schema validation" in joined
        assert "RESULT: NOT READY" in joined
        assert "fix the manifest" in joined
    finally:
        bad_manifest.unlink(missing_ok=True)


def test_unreadable_manifest_returns_error_exit_2() -> None:
    code, lines = car.check(Path("/tmp/missing_manifest.json"), FIXTURE_GLB)
    joined = "\n".join(lines)
    assert code == 2, joined
    assert "manifest" in joined.lower()


def test_missing_jsonschema_returns_error_exit_2() -> None:
    original = car.Draft202012Validator
    car.Draft202012Validator = None
    try:
        code, lines = car.check(SAMPLE_MANIFEST, FIXTURE_GLB)
    finally:
        car.Draft202012Validator = original
    joined = "\n".join(lines)
    assert code == 2, joined
    assert "jsonschema not installed" in joined
    assert "RESULT: READY" not in joined


# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------

def test_argparse_requires_manifest() -> None:
    parser_argv = ["--glb", "x.glb"]
    try:
        with redirect_stderr(io.StringIO()):
            car.main(parser_argv)
    except SystemExit as e:
        # argparse exits with code 2 when required args are missing.
        assert e.code != 0
        return
    raise AssertionError("missing --manifest should error out")


def test_main_returns_0_for_committed_fixture() -> None:
    with redirect_stdout(io.StringIO()):
        code = car.main(["--manifest", str(SAMPLE_MANIFEST),
                         "--glb", str(FIXTURE_GLB)])
    assert code == 0


# ---------------------------------------------------------------------------
# Default-path resolver helper unit test
# ---------------------------------------------------------------------------

def test_default_glb_resolver_strips_assets_prefix_correctly() -> None:
    manifest = _load(SAMPLE_MANIFEST)
    resolved = car._default_glb_for(SAMPLE_MANIFEST, manifest)
    assert resolved.name == "galley_1000.glb"
    assert resolved.parent.name == "assets"


def main() -> int:
    tests = [
        test_committed_fixture_reports_ready,
        test_default_glb_path_derived_from_manifest,
        test_missing_glb_file_reports_not_ready_with_hint,
        test_wrong_size_glb_reports_not_ready,
        test_manifest_schema_failure_reports_not_ready,
        test_unreadable_manifest_returns_error_exit_2,
        test_missing_jsonschema_returns_error_exit_2,
        test_argparse_requires_manifest,
        test_main_returns_0_for_committed_fixture,
        test_default_glb_resolver_strips_assets_prefix_correctly,
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
