"""Tests for galley_v1 panel math."""

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
sys.path.insert(0, str(REPO_ROOT / "tools" / "fusion"))

import compute_galley_panels as panel_math  # noqa: E402
import export_galley_v1_panels as exporter  # noqa: E402


EXPECTED_PAYLOAD = REPO_ROOT / "tests" / "fixtures" / "galley_1000_fusion_parameters.expected.json"
EXPECTED_PANELS = REPO_ROOT / "tests" / "fixtures" / "galley_1000_panels.expected.json"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _expected_payload() -> dict:
    return _load_json(EXPECTED_PAYLOAD)


def _breakdown(payload: dict | None = None) -> dict:
    return panel_math.build_panel_breakdown(payload or _expected_payload())


def _panel_error(payload: dict) -> str:
    try:
        panel_math.compute_galley_panels(payload)
    except panel_math.GalleyPanelError as e:
        return str(e)
    raise AssertionError("panel math unexpectedly succeeded")


def test_expected_payload_produces_expected_panel_fixture() -> None:
    assert _breakdown() == _load_json(EXPECTED_PANELS)


def test_panel_list_validates() -> None:
    panels = panel_math.compute_galley_panels(_expected_payload())
    assert panel_math.validate_panel_list(panels) is panels


def test_missing_width_fails() -> None:
    payload = _expected_payload()
    payload["parameters"].pop("Width")
    assert "parameters.Width must be a positive integer millimetre value" in _panel_error(payload)


def test_missing_ply_thickness_fails() -> None:
    payload = _expected_payload()
    payload["parameters"].pop("PlyThickness")
    assert "parameters.PlyThickness must be a positive integer millimetre value" in _panel_error(payload)


def test_non_integer_width_depth_height_and_thickness_fail() -> None:
    for key in ("Width", "Depth", "Height", "PlyThickness"):
        payload = _expected_payload()
        payload["parameters"][key] = 1000.5
        assert f"parameters.{key} must be a positive integer millimetre value" in _panel_error(payload)


def test_bool_parameter_fails() -> None:
    payload = _expected_payload()
    payload["parameters"]["Width"] = True
    assert "parameters.Width must be a positive integer millimetre value" in _panel_error(payload)


def test_too_small_width_relative_to_thickness_fails() -> None:
    payload = _expected_payload()
    payload["parameters"]["Width"] = 36
    payload["parameters"]["PlyThickness"] = 18
    assert "parameters.Width must be greater than 2 * parameters.PlyThickness" in _panel_error(payload)


def test_panel_names_are_unique() -> None:
    panels = panel_math.compute_galley_panels(_expected_payload())
    names = [panel["name"] for panel in panels]
    assert len(names) == len(set(names))

    duplicate = copy.deepcopy(panels)
    duplicate[1]["name"] = duplicate[0]["name"]
    try:
        panel_math.validate_panel_list(duplicate)
    except panel_math.GalleyPanelError as e:
        assert "duplicate panel name: left_side" in str(e)
    else:
        raise AssertionError("duplicate panel name unexpectedly validated")


def test_panel_dimensions_are_positive_integers() -> None:
    panels = panel_math.compute_galley_panels(_expected_payload())
    for panel in panels:
        for key in ("length_mm", "width_mm", "thickness_mm"):
            assert isinstance(panel[key], int)
            assert not isinstance(panel[key], bool)
            assert panel[key] > 0


def test_panel_quantity_is_positive_integer() -> None:
    panels = panel_math.compute_galley_panels(_expected_payload())
    for panel in panels:
        assert isinstance(panel["quantity"], int)
        assert not isinstance(panel["quantity"], bool)
        assert panel["quantity"] > 0


def test_cli_writes_expected_output() -> None:
    root = Path(tempfile.mkdtemp(prefix="dmv_panel_export_"))
    try:
        out = root / "galley_1000_panels.json"
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = exporter.main(["--payload", str(EXPECTED_PAYLOAD), "--out", str(out)])
        assert code == 0
        assert out.read_text(encoding="utf-8") == EXPECTED_PANELS.read_text(encoding="utf-8")
        text = buf.getvalue()
        assert "RESULT: GALLEY PANELS EXPORTED" in text
        assert "panel_count: 5" in text
    finally:
        shutil.rmtree(root)


def main() -> int:
    tests = [
        test_expected_payload_produces_expected_panel_fixture,
        test_panel_list_validates,
        test_missing_width_fails,
        test_missing_ply_thickness_fails,
        test_non_integer_width_depth_height_and_thickness_fail,
        test_bool_parameter_fails,
        test_too_small_width_relative_to_thickness_fails,
        test_panel_names_are_unique,
        test_panel_dimensions_are_positive_integers,
        test_panel_quantity_is_positive_integer,
        test_cli_writes_expected_output,
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
