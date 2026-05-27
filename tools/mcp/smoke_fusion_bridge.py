#!/usr/bin/env python3
"""Smoke-test the DraftMyVan Fusion MCP bridge over stdio.

This helper starts the repo-owned bridge as a child Python process, sends a
small JSON-RPC request batch over stdin, and validates the responses. It does
not edit MCP config, start a network server, run Fusion, or create
manufacturing output.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
BRIDGE_SCRIPT = REPO_ROOT / "tools" / "mcp" / "fusion_bridge_server.py"
EXPECTED_PANELS = REPO_ROOT / "tests" / "fixtures" / "galley_1000_panels.expected.json"
PASS_RESULT = "FUSION MCP BRIDGE SMOKE PASS"
FAIL_RESULT = "FUSION MCP BRIDGE SMOKE FAIL"


class FusionMcpSmokeError(RuntimeError):
    """Raised when the Fusion MCP smoke check fails."""


def _jsonrpc(id_: int, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    message: dict[str, Any] = {"jsonrpc": "2.0", "id": id_, "method": method}
    if params is not None:
        message["params"] = params
    return message


def send_jsonrpc_messages(
    messages: list[dict[str, Any]],
    *,
    bridge_script: Path = BRIDGE_SCRIPT,
) -> list[dict[str, Any]]:
    """Run the bridge once and return JSON-RPC responses for `messages`."""
    request_body = "".join(json.dumps(message) + "\n" for message in messages)
    result = subprocess.run(
        [sys.executable, str(bridge_script)],
        input=request_body,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        raise FusionMcpSmokeError(
            f"bridge exited {result.returncode}: {result.stderr.strip() or result.stdout.strip()}"
        )
    responses: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        try:
            response = json.loads(line)
        except json.JSONDecodeError as e:
            raise FusionMcpSmokeError(f"bridge returned invalid JSON: {line}") from e
        if not isinstance(response, dict):
            raise FusionMcpSmokeError("bridge response root must be an object")
        responses.append(response)
    return responses


def _response_by_id(responses: list[dict[str, Any]], id_: int) -> dict[str, Any]:
    for response in responses:
        if response.get("id") == id_:
            return response
    raise FusionMcpSmokeError(f"missing response id {id_}")


def _tool_payload(response: dict[str, Any]) -> dict[str, Any]:
    result = response.get("result")
    if not isinstance(result, dict):
        raise FusionMcpSmokeError("tool response missing result object")
    content = result.get("content")
    if not isinstance(content, list) or not content:
        raise FusionMcpSmokeError("tool response missing content")
    text = content[0].get("text") if isinstance(content[0], dict) else None
    if not isinstance(text, str):
        raise FusionMcpSmokeError("tool response text missing")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise FusionMcpSmokeError("tool response payload must be an object")
    return payload


def smoke_check() -> list[str]:
    """Run tools/list and dry_run_geometry through the stdio bridge."""
    messages = [
        _jsonrpc(1, "tools/list"),
        _jsonrpc(
            2,
            "tools/call",
            {
                "name": "dry_run_geometry",
                "arguments": {"panel_payload_path": str(EXPECTED_PANELS)},
            },
        ),
    ]
    responses = send_jsonrpc_messages(messages)
    tools_response = _response_by_id(responses, 1)
    dry_run_response = _response_by_id(responses, 2)

    tools_result = tools_response.get("result")
    if not isinstance(tools_result, dict) or not isinstance(tools_result.get("tools"), list):
        raise FusionMcpSmokeError("tools/list did not return a tools list")
    tool_names = {tool.get("name") for tool in tools_result["tools"] if isinstance(tool, dict)}
    expected = {
        "check_fusion_payload",
        "check_geometry_plan",
        "dry_run_geometry",
        "report_manual_verification_status",
    }
    if tool_names != expected:
        raise FusionMcpSmokeError(f"unexpected tool list: {sorted(tool_names)}")

    payload = _tool_payload(dry_run_response)
    if payload.get("status") != "FUSION GEOMETRY DRY RUN VALID":
        raise FusionMcpSmokeError(f"dry_run_geometry failed: {payload}")
    if payload.get("manufacturing_ready") is not False:
        raise FusionMcpSmokeError("dry_run_geometry must not claim manufacturing readiness")

    return [
        "tools/list exposed exactly four allowlisted tools",
        "dry_run_geometry returned FUSION GEOMETRY DRY RUN VALID",
        "manufacturing_ready remained false",
    ]


def unknown_tool_rejected() -> bool:
    """Return True when the bridge rejects an unknown tool over stdio."""
    responses = send_jsonrpc_messages(
        [
            _jsonrpc(
                1,
                "tools/call",
                {"name": "run_command", "arguments": {"cmd": "echo nope"}},
            )
        ]
    )
    payload = _tool_payload(_response_by_id(responses, 1))
    return payload.get("ok") is False and "unsupported tool" in str(payload.get("error", ""))


def main() -> int:
    try:
        lines = smoke_check()
        if not unknown_tool_rejected():
            raise FusionMcpSmokeError("unknown tool was not rejected")
    except Exception as e:
        print(f"[FAIL] {e}")
        print(f"RESULT: {FAIL_RESULT}")
        return 1

    for line in lines:
        print(f"[OK] {line}")
    print("[OK] unknown run_command tool was rejected")
    print(f"RESULT: {PASS_RESULT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
