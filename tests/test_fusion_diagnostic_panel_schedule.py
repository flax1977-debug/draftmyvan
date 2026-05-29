"""Tests for the diagnostic Fusion panel schedule."""

from __future__ import annotations

import ast
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "fusion"))

import diagnostic_panel_schedule as schedule  # noqa: E402


EXPECTED_PANELS = REPO_ROOT / "tests" / "fixtures" / "galley_1000_panels.expected.json"


def _schedule_text() -> str:
    status, lines = schedule.generate_schedule(EXPECTED_PANELS)
    assert status == schedule.STATUS_VALID
    return "\n".join(lines)


def test_module_imports_without_adsk_or_fusion() -> None:
    assert callable(schedule.diagnostic_schedule_lines)
    assert callable(schedule.generate_schedule)


def test_no_top_level_adsk_import_exists() -> None:
    tree = ast.parse((REPO_ROOT / "tools" / "fusion" / "diagnostic_panel_schedule.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Import):
            assert all(not alias.name.startswith("adsk") for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith("adsk")


def test_schedule_contains_required_warning() -> None:
    text = _schedule_text()
    assert schedule.WARNING in text
    assert text.count(schedule.WARNING) == 2


def test_schedule_contains_exactly_five_panel_rows() -> None:
    lines = schedule.diagnostic_schedule_lines(EXPECTED_PANELS)
    panel_rows = [line for line in lines if line.startswith("| `")]
    assert len(panel_rows) == 5


def test_schedule_contains_expected_mapping_and_dimensions() -> None:
    text = _schedule_text()
    expected_lines = (
        "Galley_LeftSide -> left_side_body",
        "Galley_RightSide -> right_side_body",
        "Galley_BottomPanel -> bottom_panel_body",
        "Galley_TopPanel -> top_panel_body",
        "Galley_BackPanel -> back_panel_body",
        "| `left_side` | `Galley_LeftSide` | `left_side_body` | 1 | `900 x 520 x 18 mm` |",
        "| `right_side` | `Galley_RightSide` | `right_side_body` | 1 | `900 x 520 x 18 mm` |",
        "| `bottom_panel` | `Galley_BottomPanel` | `bottom_panel_body` | 1 | `964 x 520 x 18 mm` |",
        "| `top_panel` | `Galley_TopPanel` | `top_panel_body` | 1 | `964 x 520 x 18 mm` |",
        "| `back_panel` | `Galley_BackPanel` | `back_panel_body` | 1 | `964 x 864 x 18 mm` |",
    )
    for line in expected_lines:
        assert line in text


def test_schedule_is_deterministic() -> None:
    assert schedule.diagnostic_schedule_lines(EXPECTED_PANELS) == schedule.diagnostic_schedule_lines(
        EXPECTED_PANELS
    )


def test_cli_valid_payload_exits_0() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = schedule.main([str(EXPECTED_PANELS)])
    assert code == 0
    text = buf.getvalue()
    assert "panel_count: 5" in text
    assert "Galley_LeftSide -> left_side_body" in text
    assert "RESULT: DIAGNOSTIC PANEL SCHEDULE VALID" in text


def test_cli_invalid_path_exits_nonzero() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = schedule.main(["/path/does/not/exist.json"])
    assert code == 1
    text = buf.getvalue()
    assert "[FAIL] cannot read /path/does/not/exist.json" in text
    assert "RESULT: DIAGNOSTIC PANEL SCHEDULE INVALID" in text


def main() -> int:
    tests = [
        test_module_imports_without_adsk_or_fusion,
        test_no_top_level_adsk_import_exists,
        test_schedule_contains_required_warning,
        test_schedule_contains_exactly_five_panel_rows,
        test_schedule_contains_expected_mapping_and_dimensions,
        test_schedule_is_deterministic,
        test_cli_valid_payload_exits_0,
        test_cli_invalid_path_exits_nonzero,
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
