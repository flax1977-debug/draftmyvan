"""Tests for guarded Fusion geometry execution skeleton."""

from __future__ import annotations

import ast
import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "fusion"))

import fusion_create_galley_v1 as geometry  # noqa: E402


EXPECTED_PANELS = REPO_ROOT / "tests" / "fixtures" / "galley_1000_panels.expected.json"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _plan() -> dict:
    return geometry.fusion_geometry_plan(_load_json(EXPECTED_PANELS))


def _outside_fusion_error(fn, *args) -> str:
    try:
        fn(*args)
    except geometry.FusionGeometryPlanError as e:
        return str(e)
    raise AssertionError("Fusion-only function unexpectedly succeeded outside Fusion")


def _payload_error(payload: dict) -> str:
    try:
        geometry.validate_panel_payload(payload)
    except geometry.FusionGeometryPlanError as e:
        return str(e)
    raise AssertionError("panel payload unexpectedly validated")


def test_module_imports_without_adsk_or_fusion() -> None:
    assert callable(geometry.fusion_geometry_plan)


def test_no_top_level_adsk_import_exists() -> None:
    tree = ast.parse((REPO_ROOT / "tools" / "fusion" / "fusion_create_galley_v1.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Import):
            assert all(not alias.name.startswith("adsk") for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith("adsk")


def test_is_running_in_fusion_returns_false_in_ci() -> None:
    assert geometry.is_running_in_fusion() is False


def test_require_fusion_modules_fails_clearly_outside_fusion() -> None:
    assert geometry.FUSION_UNAVAILABLE in _outside_fusion_error(geometry.require_fusion_modules)


def test_fusion_only_functions_exist() -> None:
    assert callable(geometry.ensure_component)
    assert callable(geometry.set_user_parameter)
    assert callable(geometry.create_panel_body)
    assert callable(geometry.create_galley_carcass_from_panels)


def test_create_panel_body_outside_fusion_fails_clearly() -> None:
    panel = _plan()["panels"][0]
    assert geometry.FUSION_UNAVAILABLE in _outside_fusion_error(geometry.create_panel_body, panel)


def test_create_galley_carcass_outside_fusion_fails_clearly() -> None:
    assert geometry.FUSION_UNAVAILABLE in _outside_fusion_error(
        geometry.create_galley_carcass_from_panels,
        _plan(),
    )


def test_panel_payload_relationship_mismatch_fails() -> None:
    payload = _load_json(EXPECTED_PANELS)
    payload["panels"][4]["width_mm"] += 1
    assert "back_panel width must equal side panel height minus 2 * thickness" in _payload_error(
        payload
    )


def test_dry_run_valid_payload_exits_0() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = geometry.main(["--dry-run", str(EXPECTED_PANELS)])
    assert code == 0
    text = buf.getvalue()
    assert "panel_count: 5" in text
    assert "planned_panel_count: 5" in text
    assert "Galley_LeftSide -> left_side_body" in text
    assert "RESULT: FUSION GEOMETRY DRY RUN VALID" in text


def test_dry_run_invalid_payload_exits_nonzero() -> None:
    with tempfile.TemporaryDirectory(prefix="dmv_bad_fusion_payload_") as tmp:
        bad = Path(tmp) / "bad.json"
        bad.write_text("{}", encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = geometry.main(["--dry-run", str(bad)])
    assert code == 1
    assert "RESULT: FUSION GEOMETRY DRY RUN INVALID" in buf.getvalue()


def test_run_entrypoint_is_present_but_not_executed_in_ci() -> None:
    assert callable(geometry.run)


def main() -> int:
    tests = [
        test_module_imports_without_adsk_or_fusion,
        test_no_top_level_adsk_import_exists,
        test_is_running_in_fusion_returns_false_in_ci,
        test_require_fusion_modules_fails_clearly_outside_fusion,
        test_fusion_only_functions_exist,
        test_create_panel_body_outside_fusion_fails_clearly,
        test_create_galley_carcass_outside_fusion_fails_clearly,
        test_panel_payload_relationship_mismatch_fails,
        test_dry_run_valid_payload_exits_0,
        test_dry_run_invalid_payload_exits_nonzero,
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
