"""Tests for the local DraftMyVan Fusion MCP bridge allowlist."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "mcp"))
sys.path.insert(0, str(REPO_ROOT / "tools" / "fusion"))

import fusion_bridge_server as bridge  # noqa: E402
import fusion_command_bridge as command_bridge  # noqa: E402


EXPECTED_PARAMETERS = REPO_ROOT / "tests" / "fixtures" / "galley_1000_fusion_parameters.expected.json"
EXPECTED_PANELS = REPO_ROOT / "tests" / "fixtures" / "galley_1000_panels.expected.json"


def _bridge_error(name: str, args: dict | None = None) -> str:
    try:
        bridge.dispatch_tool(name, args or {})
    except bridge.BridgeValidationError as e:
        return str(e)
    raise AssertionError("bridge request unexpectedly validated")


def _command_error(payload: dict) -> str:
    try:
        command_bridge.validate_command_payload(payload)
    except command_bridge.FusionCommandBridgeError as e:
        return str(e)
    raise AssertionError("command payload unexpectedly validated")


def test_supported_tools_are_exact_allowlist() -> None:
    assert set(bridge.TOOL_HANDLERS) == {
        "check_fusion_payload",
        "check_geometry_plan",
        "dry_run_geometry",
        "report_manual_verification_status",
    }


def test_bridge_rejects_unknown_tool() -> None:
    assert "unsupported tool" in _bridge_error("run_arbitrary_python")


def test_bridge_rejects_unknown_tool_argument() -> None:
    message = _bridge_error(
        "dry_run_geometry",
        {"panel_payload_path": str(EXPECTED_PANELS), "shell": "rm -rf /"},
    )
    assert "unsupported argument(s): shell" in message


def test_bridge_rejects_non_json_or_broad_file_path() -> None:
    message = _bridge_error("check_fusion_payload", {"payload_path": "/etc/passwd"})
    assert "JSON file" in message


def test_check_fusion_payload_valid_fixture() -> None:
    result = bridge.dispatch_tool(
        "check_fusion_payload",
        {"payload_path": str(EXPECTED_PARAMETERS)},
    )
    assert result["ok"] is True
    assert result["status"] == "FUSION PAYLOAD VALID"
    assert result["manufacturing_ready"] is False


def test_check_geometry_plan_valid_fixture() -> None:
    result = bridge.dispatch_tool(
        "check_geometry_plan",
        {"panel_payload_path": str(EXPECTED_PANELS), "verbose": True},
    )
    assert result["ok"] is True
    assert result["status"] == "FUSION GEOMETRY PLAN VALID"
    assert any("placement_origin_mm" in line for line in result["lines"])


def test_dry_run_geometry_valid_fixture() -> None:
    result = bridge.dispatch_tool(
        "dry_run_geometry",
        {"panel_payload_path": str(EXPECTED_PANELS)},
    )
    assert result["ok"] is True
    assert result["status"] == "FUSION GEOMETRY DRY RUN VALID"
    assert any("Galley_BackPanel -> back_panel_body" in line for line in result["lines"])


def test_command_bridge_rejects_unsupported_fusion_action() -> None:
    assert "unsupported command" in _command_error({"command": "create_geometry"})


def test_command_bridge_rejects_extra_fields() -> None:
    message = _command_error(
        {
            "command": "report_manual_verification_status",
            "python": "print('nope')",
        }
    )
    assert "unsupported command field(s): python" in message


def test_command_bridge_normalizes_report_status_command() -> None:
    command = command_bridge.validate_command_payload(
        {
            "command": "report_manual_verification_status",
            "payload_path": str(EXPECTED_PANELS),
            "reviewer": "manual",
        }
    )
    assert command["command"] == "report_manual_verification_status"
    assert command["payload_path"] == str(EXPECTED_PANELS)
    assert command["status_path"] == str(
        command_bridge.resolve_bridge_write_path(
            str(command_bridge.DEFAULT_STATUS_FILE),
            kind="status_path",
        )
    )
    assert command["reviewer"] == "manual"


def test_report_status_can_write_allowlisted_command_file() -> None:
    (REPO_ROOT / "build" / "fusion").mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="dmv_bridge_", dir=REPO_ROOT / "build" / "fusion"))
    try:
        command_path = root / "command.json"
        status_path = root / "status.json"
        result = bridge.dispatch_tool(
            "report_manual_verification_status",
            {
                "request_status_from_fusion": True,
                "command_path": str(command_path),
                "status_path": str(status_path),
                "payload_path": str(EXPECTED_PANELS),
            },
        )
        assert result["ok"] is False
        assert result["status"]["status"] == "manual_verification_status_unavailable"
        assert command_path.is_file()
        written = json.loads(command_path.read_text(encoding="utf-8"))
        assert written["command"] == "report_manual_verification_status"
        assert written["payload_path"] == str(EXPECTED_PANELS)
        assert written["status_path"] == str(status_path)
    finally:
        shutil.rmtree(root)


def test_jsonrpc_tools_call_returns_mcp_tool_payload() -> None:
    response = bridge.handle_jsonrpc_message(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "dry_run_geometry",
                "arguments": {"panel_payload_path": str(EXPECTED_PANELS)},
            },
        }
    )
    assert response is not None
    assert response["id"] == 7
    text = response["result"]["content"][0]["text"]
    payload = json.loads(text)
    assert payload["status"] == "FUSION GEOMETRY DRY RUN VALID"


def main() -> int:
    tests = [
        test_supported_tools_are_exact_allowlist,
        test_bridge_rejects_unknown_tool,
        test_bridge_rejects_unknown_tool_argument,
        test_bridge_rejects_non_json_or_broad_file_path,
        test_check_fusion_payload_valid_fixture,
        test_check_geometry_plan_valid_fixture,
        test_dry_run_geometry_valid_fixture,
        test_command_bridge_rejects_unsupported_fusion_action,
        test_command_bridge_rejects_extra_fields,
        test_command_bridge_normalizes_report_status_command,
        test_report_status_can_write_allowlisted_command_file,
        test_jsonrpc_tools_call_returns_mcp_tool_payload,
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
