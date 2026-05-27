"""Tests for the local Fusion availability advisory helper."""

from __future__ import annotations

import io
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "fusion"))

import check_fusion_local_availability as availability  # noqa: E402


def test_candidate_paths_include_expected_app_names() -> None:
    root = Path("/tmp/fusion_root")
    paths = availability.candidate_app_paths([root])
    assert root / "Autodesk Fusion.app" in paths
    assert root / "Fusion 360.app" in paths
    assert root / "Autodesk Fusion 360.app" in paths
    assert root / "Autodesk" / "Autodesk Fusion.app" in paths


def test_find_fusion_apps_returns_empty_for_missing_root() -> None:
    with tempfile.TemporaryDirectory(prefix="dmv_no_fusion_") as tmp:
        assert availability.find_fusion_apps([Path(tmp)]) == []


def test_find_fusion_apps_finds_fake_app_bundle() -> None:
    with tempfile.TemporaryDirectory(prefix="dmv_fake_fusion_") as tmp:
        root = Path(tmp)
        fake_app = root / "Autodesk Fusion.app"
        fake_app.mkdir()
        assert availability.find_fusion_apps([root]) == [fake_app]


def test_format_report_available() -> None:
    found = [Path("/Applications/Autodesk Fusion.app")]
    report = availability.format_report(found, found)
    assert "RESULT: FUSION LOCAL AVAILABLE" in report
    assert "found: /Applications/Autodesk Fusion.app" in report


def test_cli_returns_0_for_fake_app_bundle() -> None:
    with tempfile.TemporaryDirectory(prefix="dmv_fake_fusion_cli_") as tmp:
        root = Path(tmp)
        (root / "Fusion 360.app").mkdir()
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = availability.main(["--search-root", str(root)])
    assert code == 0
    assert "RESULT: FUSION LOCAL AVAILABLE" in buf.getvalue()


def test_cli_returns_1_when_not_found() -> None:
    with tempfile.TemporaryDirectory(prefix="dmv_missing_fusion_cli_") as tmp:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = availability.main(["--search-root", tmp])
    assert code == 1
    assert "RESULT: FUSION LOCAL NOT FOUND" in buf.getvalue()


def main() -> int:
    tests = [
        test_candidate_paths_include_expected_app_names,
        test_find_fusion_apps_returns_empty_for_missing_root,
        test_find_fusion_apps_finds_fake_app_bundle,
        test_format_report_available,
        test_cli_returns_0_for_fake_app_bundle,
        test_cli_returns_1_when_not_found,
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
