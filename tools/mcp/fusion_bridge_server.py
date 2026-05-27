#!/usr/bin/env python3
"""Small stdio MCP bridge for DraftMyVan Fusion validation.

This server intentionally exposes a tiny allowlist only. It imports the local
DraftMyVan Fusion validators directly instead of running arbitrary shell
commands, and it never creates CNC, DXF, drawing, or manufacturing output.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[2]
FUSION_TOOLS = REPO_ROOT / "tools" / "fusion"
if str(FUSION_TOOLS) not in sys.path:
    sys.path.insert(0, str(FUSION_TOOLS))

import check_fusion_geometry_plan  # noqa: E402
import check_fusion_payload  # noqa: E402
import fusion_command_bridge  # noqa: E402
import fusion_create_galley_v1  # noqa: E402


SERVER_NAME = "draftmyvan-fusion-bridge"
PROTOCOL_VERSION = "2024-11-05"

TMP_JSON_ALLOWLIST = (
    re.compile(r"^galley_[A-Za-z0-9_-]+_fusion_parameters\.json$"),
    re.compile(r"^galley_[A-Za-z0-9_-]+_panels\.json$"),
    re.compile(r"^draftmyvan_fusion_(command|status|manual_status)\.json$"),
)
TMP_ROOT = Path("/tmp").resolve(strict=False)


class BridgeValidationError(ValueError):
    """Raised when a bridge request is outside the local allowlist."""


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _is_allowed_tmp_json(path: Path) -> bool:
    return path.parent == TMP_ROOT and any(
        pattern.match(path.name) for pattern in TMP_JSON_ALLOWLIST
    )


def _resolve_repo_or_tmp_json(value: Any, *, must_exist: bool = True) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise BridgeValidationError("path must be a non-empty string")
    raw = Path(value.strip())
    path = raw if raw.is_absolute() else REPO_ROOT / raw
    resolved = path.resolve(strict=False)
    if resolved.suffix != ".json":
        raise BridgeValidationError(f"path must point to a JSON file: {resolved}")
    if not (_is_relative_to(resolved, REPO_ROOT) or _is_allowed_tmp_json(resolved)):
        raise BridgeValidationError(
            "path must be under the DraftMyVan repo or match an allowlisted /tmp DraftMyVan JSON name"
        )
    if must_exist and not resolved.is_file():
        raise BridgeValidationError(f"file does not exist: {resolved}")
    return resolved


def _require_exact_keys(args: dict[str, Any], allowed: set[str], required: set[str]) -> None:
    missing = sorted(required - set(args))
    if missing:
        raise BridgeValidationError("missing required argument(s): " + ", ".join(missing))
    extra = sorted(set(args) - allowed)
    if extra:
        raise BridgeValidationError("unsupported argument(s): " + ", ".join(extra))


def _result_payload(payload: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, indent=2, sort_keys=True),
            }
        ],
        "isError": is_error,
    }


def _lines_result(
    *,
    ok: bool,
    status: str,
    lines: list[str],
    path: Path,
    command: str,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "command": command,
        "status": status,
        "path": str(path),
        "lines": lines,
        "manufacturing_ready": False,
        "generated_outputs": {
            "drawings": False,
            "dxf": False,
            "cnc": False,
            "cut_lists": False,
        },
    }


def _resolve_bridge_write_path(value: str, *, kind: str) -> Path:
    try:
        return fusion_command_bridge.resolve_bridge_write_path(value, kind=kind)
    except fusion_command_bridge.FusionCommandBridgeError as e:
        raise BridgeValidationError(str(e)) from e


def tool_check_fusion_payload(args: dict[str, Any]) -> dict[str, Any]:
    _require_exact_keys(args, {"payload_path"}, {"payload_path"})
    payload_path = _resolve_repo_or_tmp_json(args["payload_path"])
    status, lines = check_fusion_payload.validate_payload_file(payload_path)
    return _lines_result(
        ok=status == check_fusion_payload.STATUS_VALID,
        status=status,
        lines=lines,
        path=payload_path,
        command="check_fusion_payload",
    )


def tool_check_geometry_plan(args: dict[str, Any]) -> dict[str, Any]:
    _require_exact_keys(args, {"panel_payload_path", "verbose"}, {"panel_payload_path"})
    verbose = args.get("verbose", False)
    if not isinstance(verbose, bool):
        raise BridgeValidationError("verbose must be a boolean")
    payload_path = _resolve_repo_or_tmp_json(args["panel_payload_path"])
    status, lines = check_fusion_geometry_plan.check_geometry_plan(payload_path, verbose=verbose)
    return _lines_result(
        ok=status == check_fusion_geometry_plan.STATUS_VALID,
        status=status,
        lines=lines,
        path=payload_path,
        command="check_geometry_plan",
    )


def tool_dry_run_geometry(args: dict[str, Any]) -> dict[str, Any]:
    _require_exact_keys(args, {"panel_payload_path"}, {"panel_payload_path"})
    payload_path = _resolve_repo_or_tmp_json(args["panel_payload_path"])
    status, lines = fusion_create_galley_v1.dry_run(payload_path)
    return _lines_result(
        ok=status == "FUSION GEOMETRY DRY RUN VALID",
        status=status,
        lines=lines,
        path=payload_path,
        command="dry_run_geometry",
    )


def tool_report_manual_verification_status(args: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "status_path",
        "request_status_from_fusion",
        "command_path",
        "payload_path",
        "reviewer",
        "notes",
    }
    _require_exact_keys(args, allowed, set())

    request_status = args.get("request_status_from_fusion", False)
    if not isinstance(request_status, bool):
        raise BridgeValidationError("request_status_from_fusion must be a boolean")

    status_path = _resolve_bridge_write_path(
        args.get("status_path") or str(fusion_command_bridge.DEFAULT_STATUS_FILE),
        kind="status_path",
    )
    response: dict[str, Any] = {
        "ok": status_path.is_file(),
        "command": "report_manual_verification_status",
        "status_path": str(status_path),
        "manufacturing_ready": False,
        "generated_outputs": {
            "drawings": False,
            "dxf": False,
            "cnc": False,
            "cut_lists": False,
        },
    }

    if status_path.is_file():
        try:
            response["status"] = fusion_command_bridge.load_status_file(status_path)
        except fusion_command_bridge.FusionCommandBridgeError as e:
            raise BridgeValidationError(str(e)) from e
    else:
        response["status"] = {
            "status": "manual_verification_status_unavailable",
            "message": "No Fusion status file has been written yet.",
        }

    if request_status:
        command_path = _resolve_bridge_write_path(
            args.get("command_path") or str(fusion_command_bridge.DEFAULT_COMMAND_FILE),
            kind="command_path",
        )
        command_payload = {
            "command": "report_manual_verification_status",
            "status_path": str(status_path),
        }
        if "payload_path" in args:
            command_payload["payload_path"] = str(_resolve_repo_or_tmp_json(args["payload_path"]))
        if "reviewer" in args:
            if not isinstance(args["reviewer"], str):
                raise BridgeValidationError("reviewer must be a string")
            command_payload["reviewer"] = args["reviewer"]
        if "notes" in args:
            if not isinstance(args["notes"], str):
                raise BridgeValidationError("notes must be a string")
            command_payload["notes"] = args["notes"]
        try:
            written = fusion_command_bridge.write_command_file(command_payload, command_path)
        except fusion_command_bridge.FusionCommandBridgeError as e:
            raise BridgeValidationError(str(e)) from e
        response["request_status_from_fusion"] = {
            "command_path": str(written),
            "next_step": "Run tools/fusion/fusion_command_bridge.py inside Fusion to write the status file.",
        }

    return response


TOOL_HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "check_fusion_payload": tool_check_fusion_payload,
    "check_geometry_plan": tool_check_geometry_plan,
    "dry_run_geometry": tool_dry_run_geometry,
    "report_manual_verification_status": tool_report_manual_verification_status,
}


TOOLS = [
    {
        "name": "check_fusion_payload",
        "description": "Validate a DraftMyVan galley_v1 Fusion parameter payload JSON file.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "payload_path": {"type": "string"},
            },
            "required": ["payload_path"],
        },
    },
    {
        "name": "check_geometry_plan",
        "description": "Validate and summarize a galley_v1 panel payload geometry plan.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "panel_payload_path": {"type": "string"},
                "verbose": {"type": "boolean"},
            },
            "required": ["panel_payload_path"],
        },
    },
    {
        "name": "dry_run_geometry",
        "description": "Run the existing galley_v1 geometry dry-run without Fusion geometry execution.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "panel_payload_path": {"type": "string"},
            },
            "required": ["panel_payload_path"],
        },
    },
    {
        "name": "report_manual_verification_status",
        "description": "Read the local Fusion manual verification status file, optionally writing a fixed status-request command file for the Fusion add-in.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "status_path": {"type": "string"},
                "request_status_from_fusion": {"type": "boolean"},
                "command_path": {"type": "string"},
                "payload_path": {"type": "string"},
                "reviewer": {"type": "string"},
                "notes": {"type": "string"},
            },
        },
    },
]


def dispatch_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(name, str) or name not in TOOL_HANDLERS:
        raise BridgeValidationError(f"unsupported tool: {name}")
    args = arguments or {}
    if not isinstance(args, dict):
        raise BridgeValidationError("tool arguments must be an object")
    return TOOL_HANDLERS[name](args)


def _jsonrpc_result(message_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _jsonrpc_error(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def handle_jsonrpc_message(message: dict[str, Any]) -> dict[str, Any] | None:
    message_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}
    if not isinstance(params, dict):
        return _jsonrpc_error(message_id, -32602, "params must be an object")

    if method == "notifications/initialized":
        return None
    if method == "initialize":
        requested_version = params.get("protocolVersion")
        protocol_version = requested_version if isinstance(requested_version, str) else PROTOCOL_VERSION
        return _jsonrpc_result(
            message_id,
            {
                "protocolVersion": protocol_version,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": "0.1.0"},
            },
        )
    if method == "ping":
        return _jsonrpc_result(message_id, {})
    if method == "tools/list":
        return _jsonrpc_result(message_id, {"tools": TOOLS})
    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            payload = dispatch_tool(tool_name, arguments)
        except BridgeValidationError as e:
            return _jsonrpc_result(
                message_id,
                _result_payload({"ok": False, "error": str(e)}, is_error=True),
            )
        return _jsonrpc_result(message_id, _result_payload(payload))
    if message_id is None:
        return None
    return _jsonrpc_error(message_id, -32601, f"unsupported method: {method}")


def serve_stdio() -> int:
    """Serve newline-delimited JSON-RPC messages on stdin/stdout."""
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
            if not isinstance(message, dict):
                raise ValueError("message root must be an object")
            response = handle_jsonrpc_message(message)
        except Exception as e:  # Keep the server alive for malformed client input.
            response = _jsonrpc_error(None, -32700, str(e))
        if response is not None:
            sys.stdout.write(json.dumps(response, separators=(",", ":")) + os.linesep)
            sys.stdout.flush()
    return 0


def main() -> int:
    return serve_stdio()


if __name__ == "__main__":
    sys.exit(main())
