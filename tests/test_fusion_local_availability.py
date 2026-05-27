"""Tests for local Fusion availability boundaries.

These tests are deliberately pure Python. They document that Fusion can be
absent from CI while local/manual Fusion scripts still fail clearly and keep
manufacturing output disabled.
"""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "fusion"))

import fusion_command_bridge as command_bridge  # noqa: E402
import fusion_create_galley_v1 as geometry  # noqa: E402


EXPECTED_PANELS = REPO_ROOT / "tests" / "fixtures" / "galley_1000_panels.expected.json"


def test_dry_run_geometry_is_available_without_fusion() -> None:
    status, lines = geometry.dry_run(EXPECTED_PANELS)
    assert status == "FUSION GEOMETRY DRY RUN VALID"
    assert "RESULT: FUSION GEOMETRY DRY RUN VALID" in lines


def test_fusion_api_absence_is_reported_clearly() -> None:
    assert geometry.is_running_in_fusion() is False
    try:
        geometry.require_fusion_modules()
    except geometry.FusionGeometryPlanError as e:
        assert geometry.FUSION_UNAVAILABLE in str(e)
    else:
        raise AssertionError("Fusion modules unexpectedly loaded in pure-Python test")


def test_command_bridge_status_report_is_safe_outside_fusion() -> None:
    result = command_bridge.execute_command_payload(
        {
            "command": "report_manual_verification_status",
            "payload_path": str(EXPECTED_PANELS),
        }
    )
    assert result["running_in_fusion"] is False
    assert result["status"] == "fusion_unavailable"
    assert result["manufacturing_ready"] is False
    assert result["generated_outputs"] == {
        "drawings": False,
        "dxf": False,
        "cnc": False,
        "cut_lists": False,
    }


def test_command_bridge_supports_only_report_status_command() -> None:
    assert command_bridge.SUPPORTED_COMMANDS == {"report_manual_verification_status"}


def main() -> int:
    tests = [
        test_dry_run_geometry_is_available_without_fusion,
        test_fusion_api_absence_is_reported_clearly,
        test_command_bridge_status_report_is_safe_outside_fusion,
        test_command_bridge_supports_only_report_status_command,
    ]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS  {test.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {test.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"ERROR {test.__name__}: {e}")
    print()
    print(f"{len(tests) - failed}/{len(tests)} passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
