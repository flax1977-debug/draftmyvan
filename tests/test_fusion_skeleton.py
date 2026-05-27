"""Tests for the Fusion galley_v1 script skeleton."""

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

import check_fusion_payload as cli  # noqa: E402
import fusion_galley_v1_skeleton as skeleton  # noqa: E402


EXPECTED_PAYLOAD = REPO_ROOT / "tests" / "fixtures" / "galley_1000_fusion_parameters.expected.json"


def _load_expected() -> dict:
    with EXPECTED_PAYLOAD.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_temp_payload(payload: dict) -> Path:
    root = Path(tempfile.mkdtemp(prefix="dmv_fusion_payload_"))
    path = root / "payload.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _cleanup_temp_payload(path: Path) -> None:
    shutil.rmtree(path.parent)


def _validation_error(payload: dict) -> str:
    try:
        skeleton.validate_parameter_payload(payload)
    except skeleton.FusionPayloadError as e:
        return str(e)
    raise AssertionError("payload unexpectedly validated")


def test_skeleton_module_imports_without_adsk_installed() -> None:
    assert skeleton.EXPECTED_TEMPLATE == "galley_v1"
    assert "adsk" not in sys.modules


def test_expected_payload_validates() -> None:
    payload = skeleton.load_parameter_payload(EXPECTED_PAYLOAD)
    assert skeleton.validate_parameter_payload(payload) is payload


def test_missing_template_fails() -> None:
    payload = _load_expected()
    payload.pop("template")
    assert "template must be a non-empty string" in _validation_error(payload)


def test_wrong_template_fails() -> None:
    payload = _load_expected()
    payload["template"] = "galley_v2"
    assert 'template must be "galley_v1"' in _validation_error(payload)


def test_missing_manifest_id_fails() -> None:
    payload = _load_expected()
    payload.pop("manifest_id")
    assert "manifest_id must be a non-empty string" in _validation_error(payload)


def test_missing_required_parameters_fail() -> None:
    for name in skeleton.REQUIRED_PARAMETERS:
        payload = _load_expected()
        payload["parameters"].pop(name)
        message = _validation_error(payload)
        assert f"parameters.{name} must be a positive integer millimetre value" in message


def test_float_string_bool_and_non_positive_parameters_fail() -> None:
    bad_values = (1000.5, "1000", True, 0, -1)
    for bad_value in bad_values:
        payload = _load_expected()
        payload["parameters"]["Width"] = bad_value
        message = _validation_error(payload)
        assert "parameters.Width must be a positive integer millimetre value" in message


def test_parameter_summary_contains_expected_values() -> None:
    summary = skeleton.parameter_summary(_load_expected())
    for expected in (
        "template: galley_v1",
        "manifest_id: galley_1000_sink_left_oak",
        "Width: 1000",
        "Depth: 520",
        "Height: 900",
        "PlyThickness: 18",
        "hardware_count: 2",
    ):
        assert expected in summary


def test_check_fusion_payload_cli_exits_0_for_expected_fixture() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cli.main([str(EXPECTED_PAYLOAD)])
    out = buf.getvalue()
    assert code == 0
    assert "RESULT: FUSION PAYLOAD VALID" in out
    assert "hardware_count: 2" in out


def test_check_fusion_payload_cli_exits_nonzero_for_invalid_fixture() -> None:
    payload = copy.deepcopy(_load_expected())
    payload["parameters"]["Width"] = False
    path = _write_temp_payload(payload)
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main([str(path)])
        out = buf.getvalue()
        assert code == 1
        assert "RESULT: FUSION PAYLOAD INVALID" in out
        assert "parameters.Width must be a positive integer millimetre value" in out
    finally:
        _cleanup_temp_payload(path)


def main() -> int:
    tests = [
        test_skeleton_module_imports_without_adsk_installed,
        test_expected_payload_validates,
        test_missing_template_fails,
        test_wrong_template_fails,
        test_missing_manifest_id_fails,
        test_missing_required_parameters_fail,
        test_float_string_bool_and_non_positive_parameters_fail,
        test_parameter_summary_contains_expected_values,
        test_check_fusion_payload_cli_exits_0_for_expected_fixture,
        test_check_fusion_payload_cli_exits_nonzero_for_invalid_fixture,
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
