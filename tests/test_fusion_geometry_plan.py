"""Tests for galley_v1 Fusion geometry planning."""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "fusion"))

import check_fusion_geometry_plan as cli  # noqa: E402
import fusion_create_galley_v1 as geometry  # noqa: E402


EXPECTED_PANELS = REPO_ROOT / "tests" / "fixtures" / "galley_1000_panels.expected.json"
EXPECTED_PLAN = (
    REPO_ROOT / "tests" / "fixtures" / "galley_1000_fusion_geometry_plan.expected.json"
)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _panel_payload() -> dict:
    return _load_json(EXPECTED_PANELS)


def _geometry_plan(payload: dict | None = None) -> dict:
    return geometry.fusion_geometry_plan(payload or _panel_payload())


def _payload_error(payload: dict) -> str:
    try:
        geometry.validate_panel_payload(payload)
    except geometry.FusionGeometryPlanError as e:
        return str(e)
    raise AssertionError("panel payload unexpectedly validated")


def _plan_error(plan: dict) -> str:
    try:
        geometry.validate_geometry_plan(plan)
    except geometry.FusionGeometryPlanError as e:
        return str(e)
    raise AssertionError("geometry plan unexpectedly validated")


def test_skeleton_imports_without_adsk_or_fusion() -> None:
    assert callable(geometry.load_panel_payload)
    assert callable(geometry.validate_panel_payload)
    assert callable(geometry.fusion_geometry_plan)
    assert callable(geometry.geometry_plan_summary)


def test_expected_panel_payload_validates() -> None:
    payload = _panel_payload()
    assert geometry.validate_panel_payload(payload) is payload


def test_geometry_plan_matches_expected_fixture() -> None:
    assert _geometry_plan() == _load_json(EXPECTED_PLAN)


def test_missing_panel_field_fails() -> None:
    payload = _panel_payload()
    payload["panels"][0].pop("notes")
    assert "missing fields: notes" in _payload_error(payload)


def test_invalid_panel_dimensions_fail() -> None:
    payload = _panel_payload()
    payload["panels"][0]["length_mm"] = 0
    assert "field length_mm must be a positive integer" in _payload_error(payload)


def test_duplicate_panel_names_fail() -> None:
    payload = _panel_payload()
    payload["panels"][1]["name"] = payload["panels"][0]["name"]
    assert "duplicate panel name: left_side" in _payload_error(payload)


def test_duplicate_component_names_fail() -> None:
    plan = _geometry_plan()
    plan["panels"][1]["component_name"] = plan["panels"][0]["component_name"]
    assert "duplicate component_name: Galley_LeftSide" in _plan_error(plan)


def test_duplicate_body_names_fail() -> None:
    plan = _geometry_plan()
    plan["panels"][1]["body_name"] = plan["panels"][0]["body_name"]
    assert "duplicate body_name: left_side_body" in _plan_error(plan)


def test_missing_sketch_plane_fails() -> None:
    plan = _geometry_plan()
    plan["panels"][0].pop("sketch_plane")
    assert "missing fields: sketch_plane" in _plan_error(plan)


def test_missing_extrude_axis_fails() -> None:
    plan = _geometry_plan()
    plan["panels"][0].pop("extrude_axis")
    assert "missing fields: extrude_axis" in _plan_error(plan)


def test_missing_placement_origin_fails() -> None:
    plan = _geometry_plan()
    plan["panels"][0].pop("placement_origin_mm")
    assert "missing fields: placement_origin_mm" in _plan_error(plan)


def test_invalid_placement_origin_fails() -> None:
    plan = _geometry_plan()
    plan["panels"][0]["placement_origin_mm"] = [0, True, 0]
    assert "placement_origin_mm must be a 3-number list" in _plan_error(plan)


def test_geometry_status_must_be_planned_not_executed() -> None:
    plan = _geometry_plan()
    plan["geometry_status"] = "executed"
    assert 'plan.geometry_status must be "planned_not_executed"' in _plan_error(plan)


def test_cli_valid_path_exits_0() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cli.main([str(EXPECTED_PANELS)])
    assert code == 0
    text = buf.getvalue()
    assert "planned_panel_count: 5" in text
    assert "Galley_LeftSide -> left_side_body" in text
    assert "RESULT: FUSION GEOMETRY PLAN VALID" in text


def test_cli_invalid_path_exits_nonzero() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cli.main(["/path/does/not/exist.json"])
    assert code == 1
    assert "RESULT: FUSION GEOMETRY PLAN INVALID" in buf.getvalue()


def test_cli_verbose_exits_0_and_includes_panel_details() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cli.main(["--verbose", str(EXPECTED_PANELS)])
    assert code == 0
    text = buf.getvalue()
    assert "left_side: sketch_plane=YZ extrude_axis=X" in text
    assert "placement_origin_mm=[0, 0, 0]" in text
    assert "RESULT: FUSION GEOMETRY PLAN VALID" in text


def test_run_entrypoint_is_present_but_not_executed_in_ci() -> None:
    assert callable(geometry.run)


def main() -> int:
    tests = [
        test_skeleton_imports_without_adsk_or_fusion,
        test_expected_panel_payload_validates,
        test_geometry_plan_matches_expected_fixture,
        test_missing_panel_field_fails,
        test_invalid_panel_dimensions_fail,
        test_duplicate_panel_names_fail,
        test_duplicate_component_names_fail,
        test_duplicate_body_names_fail,
        test_missing_sketch_plane_fails,
        test_missing_extrude_axis_fails,
        test_missing_placement_origin_fails,
        test_invalid_placement_origin_fails,
        test_geometry_status_must_be_planned_not_executed,
        test_cli_valid_path_exits_0,
        test_cli_invalid_path_exits_nonzero,
        test_cli_verbose_exits_0_and_includes_panel_details,
        test_run_entrypoint_is_present_but_not_executed_in_ci,
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
