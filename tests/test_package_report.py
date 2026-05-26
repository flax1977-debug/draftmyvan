"""Tests for the DraftMyVan package readiness report.

Pure Python only — no Blender, no UE5.

Covers:
  * the committed examples/ scans as PACKAGE READY (exit 0),
  * a missing asset flips it to PACKAGE NOT READY (exit 1),
  * a malformed manifest is reported, not skipped (exit 2),
  * duplicate ids fail clearly (exit 2),
  * duplicate resolved asset paths fail clearly (exit 2),
  * empty / non-existent / non-directory inputs are explicit (exit 2),
  * the CLI exit codes match the documented contract,
  * subdirectories (e.g. examples/assets/) are not scanned recursively.
"""

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
sys.path.insert(0, str(REPO_ROOT))

from runtime import package_report as pr  # noqa: E402

SAMPLE_MANIFEST = REPO_ROOT / "examples" / "galley_1000.json"
EXAMPLES_DIR = REPO_ROOT / "examples"


def _load_sample() -> dict:
    with SAMPLE_MANIFEST.open("r", encoding="utf-8") as f:
        return json.load(f)


def _make_pkg_with(
    manifests: dict[str, dict],
    *,
    fixtures: dict[str, bytes] | None = None,
) -> Path:
    """Build a temp package directory.

    `manifests` keyed by filename → manifest dict.
    `fixtures` keyed by relative path under `assets/` → GLB bytes.
    """
    tmp = Path(tempfile.mkdtemp(prefix="dmv_pkg_"))
    (tmp / "assets").mkdir()
    for name, content in manifests.items():
        (tmp / name).write_text(json.dumps(content), encoding="utf-8")
    if fixtures:
        for rel, blob in fixtures.items():
            (tmp / "assets" / rel).write_bytes(blob)
    return tmp


def _fixture_bytes() -> bytes:
    """Read the committed galley_1000.glb so temp packages can have a real asset."""
    return (EXAMPLES_DIR / "assets" / "galley_1000.glb").read_bytes()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_committed_examples_scan_as_package_ready() -> None:
    report = pr.scan_package(EXAMPLES_DIR)
    assert not report.errors, report.errors
    assert report.total_modules == 1
    assert report.consumable_modules == 1
    assert report.missing_assets == 0
    assert report.exit_code() == 0
    assert report.ok is True


def test_scan_does_not_recurse_into_assets_subdirectory() -> None:
    # examples/assets/ contains .glb and .md files but no manifest.
    # Non-recursive glob must ignore that subdirectory entirely.
    report = pr.scan_package(EXAMPLES_DIR)
    for p in report.manifest_paths:
        assert "assets" not in p.parts, f"recursed into subdirectory: {p}"


def test_cli_committed_examples_returns_0_and_prints_ready() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = pr.main([str(EXAMPLES_DIR)])
    assert code == 0
    out = buf.getvalue()
    assert "RESULT: PACKAGE READY" in out
    assert "galley_1000_sink_left_oak" in out
    assert "[OK]  " in out


# ---------------------------------------------------------------------------
# Missing assets → PACKAGE NOT READY, exit 1
# ---------------------------------------------------------------------------

def test_missing_asset_flips_to_not_ready() -> None:
    src = _load_sample()
    pkg = _make_pkg_with({"galley_1000.json": src})  # no GLB written
    try:
        report = pr.scan_package(pkg)
        assert not report.errors, report.errors
        assert report.total_modules == 1
        assert report.consumable_modules == 0
        assert report.missing_assets == 1
        assert report.exit_code() == 1
    finally:
        shutil.rmtree(pkg)


def test_cli_missing_asset_returns_exit_1() -> None:
    src = _load_sample()
    pkg = _make_pkg_with({"galley_1000.json": src})
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = pr.main([str(pkg)])
        assert code == 1
        out = buf.getvalue()
        assert "RESULT: PACKAGE NOT READY" in out
        assert "[WARN]" in out
        assert "MISSING" in out
    finally:
        shutil.rmtree(pkg)


# ---------------------------------------------------------------------------
# Malformed manifest → ERROR, exit 2 (and the bad file is NOT silently skipped)
# ---------------------------------------------------------------------------

def test_malformed_manifest_reports_error_exit_2() -> None:
    pkg = Path(tempfile.mkdtemp(prefix="dmv_pkg_bad_"))
    try:
        (pkg / "assets").mkdir()
        (pkg / "bad.json").write_text("{not json", encoding="utf-8")
        report = pr.scan_package(pkg)
        assert report.errors, "malformed manifest should produce an error"
        assert any("bad.json" in e for e in report.errors)
        assert report.exit_code() == 2
    finally:
        shutil.rmtree(pkg)


def test_missing_required_field_reports_error_naming_the_field() -> None:
    src = _load_sample()
    del src["id"]
    pkg = _make_pkg_with({"broken.json": src})
    try:
        report = pr.scan_package(pkg)
        assert any("id" in e and "broken.json" in e for e in report.errors), report.errors
        assert report.exit_code() == 2
    finally:
        shutil.rmtree(pkg)


def test_error_manifests_do_NOT_appear_in_modules_list() -> None:
    # We accumulate errors but must not also count the bad file as a module.
    src = _load_sample()
    del src["id"]
    good = _load_sample()
    pkg = _make_pkg_with(
        {"broken.json": src, "good.json": good},
        fixtures={"galley_1000.glb": _fixture_bytes()},
    )
    try:
        report = pr.scan_package(pkg)
        # broken.json failed → 1 module loaded, 1 error.
        assert report.total_modules == 1
        assert len(report.errors) == 1
        assert report.exit_code() == 2  # any error → exit 2 even if other modules are fine
    finally:
        shutil.rmtree(pkg)


# ---------------------------------------------------------------------------
# Duplicates — both id and resolved asset path
# ---------------------------------------------------------------------------

def test_duplicate_module_ids_fail_clearly() -> None:
    a = _load_sample()
    b = _load_sample()
    # Same id but different visual paths → only the id collides.
    b["visual"]["glb_path"] = "assets/galley_1000_b.glb"
    pkg = _make_pkg_with(
        {"a.json": a, "b.json": b},
        fixtures={
            "galley_1000.glb": _fixture_bytes(),
            "galley_1000_b.glb": _fixture_bytes(),
        },
    )
    try:
        report = pr.scan_package(pkg)
        assert report.exit_code() == 2
        joined = " ".join(report.errors)
        assert "duplicate module id" in joined
        assert "galley_1000_sink_left_oak" in joined
        assert "a.json" in joined and "b.json" in joined
    finally:
        shutil.rmtree(pkg)


def test_duplicate_resolved_asset_paths_fail_clearly() -> None:
    a = _load_sample()
    b = _load_sample()
    # Different ids but same visual.glb_path → resolved-path collision.
    b["id"] = "galley_1000_sink_right_oak"
    pkg = _make_pkg_with(
        {"a.json": a, "b.json": b},
        fixtures={"galley_1000.glb": _fixture_bytes()},
    )
    try:
        report = pr.scan_package(pkg)
        assert report.exit_code() == 2
        joined = " ".join(report.errors)
        assert "duplicate resolved asset path" in joined
        assert "galley_1000.glb" in joined
        assert "a.json" in joined and "b.json" in joined
    finally:
        shutil.rmtree(pkg)


# ---------------------------------------------------------------------------
# Empty / non-existent / non-directory paths
# ---------------------------------------------------------------------------

def test_empty_directory_is_explicit_error() -> None:
    pkg = Path(tempfile.mkdtemp(prefix="dmv_pkg_empty_"))
    try:
        report = pr.scan_package(pkg)
        assert report.exit_code() == 2
        assert any("no manifest files" in e for e in report.errors)
        # Must not silently report PACKAGE READY for an empty dir.
        rendered = "\n".join(pr.format_report(report))
        assert "RESULT: PACKAGE READY" not in rendered
        assert "RESULT: ERROR" in rendered
    finally:
        shutil.rmtree(pkg)


def test_nonexistent_directory_is_explicit_error() -> None:
    report = pr.scan_package(Path("/tmp/does_not_exist_dmv_pkg"))
    assert report.exit_code() == 2
    assert any("directory not found" in e for e in report.errors)


def test_file_passed_as_directory_is_explicit_error() -> None:
    fd, tmp = tempfile.mkstemp()
    try:
        report = pr.scan_package(Path(tmp))
        assert report.exit_code() == 2
        assert any("not a directory" in e for e in report.errors)
    finally:
        Path(tmp).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# CLI exit codes — happy / not ready / error
# ---------------------------------------------------------------------------

def test_cli_empty_dir_returns_exit_2() -> None:
    pkg = Path(tempfile.mkdtemp(prefix="dmv_pkg_empty_cli_"))
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = pr.main([str(pkg)])
        assert code == 2
        assert "RESULT: ERROR" in buf.getvalue()
    finally:
        shutil.rmtree(pkg)


def test_cli_duplicate_ids_return_exit_2() -> None:
    a = _load_sample()
    b = _load_sample()
    b["visual"]["glb_path"] = "assets/galley_1000_b.glb"
    pkg = _make_pkg_with(
        {"a.json": a, "b.json": b},
        fixtures={
            "galley_1000.glb": _fixture_bytes(),
            "galley_1000_b.glb": _fixture_bytes(),
        },
    )
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = pr.main([str(pkg)])
        assert code == 2
        assert "duplicate module id" in buf.getvalue()
    finally:
        shutil.rmtree(pkg)


def test_format_report_summary_counts_match_aggregates() -> None:
    report = pr.scan_package(EXAMPLES_DIR)
    rendered = "\n".join(pr.format_report(report))
    assert "total modules:    1" in rendered
    assert "consumable:       1" in rendered
    assert "missing assets:   0" in rendered
    assert "manifest errors:  0" in rendered


def main() -> int:
    tests = [
        test_committed_examples_scan_as_package_ready,
        test_scan_does_not_recurse_into_assets_subdirectory,
        test_cli_committed_examples_returns_0_and_prints_ready,
        test_missing_asset_flips_to_not_ready,
        test_cli_missing_asset_returns_exit_1,
        test_malformed_manifest_reports_error_exit_2,
        test_missing_required_field_reports_error_naming_the_field,
        test_error_manifests_do_NOT_appear_in_modules_list,
        test_duplicate_module_ids_fail_clearly,
        test_duplicate_resolved_asset_paths_fail_clearly,
        test_empty_directory_is_explicit_error,
        test_nonexistent_directory_is_explicit_error,
        test_file_passed_as_directory_is_explicit_error,
        test_cli_empty_dir_returns_exit_2,
        test_cli_duplicate_ids_return_exit_2,
        test_format_report_summary_counts_match_aggregates,
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
