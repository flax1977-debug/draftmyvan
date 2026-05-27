# DraftMyVan Fusion MCP Bridge

This bridge is a local, repo-owned starting point for controlled DraftMyVan
Fusion checks. It is intentionally narrow, is not globally enabled, and is not
manufacturing sign-off.

## Recommended Design

Use Option A first, with an Option B status-file bridge available when manual
Fusion verification needs to report back.

- Option A: `tools/mcp/fusion_bridge_server.py` runs local validation and
  dry-run checks outside Fusion by importing the existing DraftMyVan scripts.
- Option B: `tools/fusion/fusion_command_bridge.py` lets Fusion read one fixed
  JSON command file and write one fixed status JSON file for manual verification
  status only.
- Option C: a localhost HTTP server in Fusion is deferred.

## Why Not Option C Yet

A localhost server adds lifecycle, port, authentication, and request-filtering
risks. It is useful only when we need interactive Fusion actions. The current
goal is validation and manual verification reporting, so a stdio MCP server plus
file-based Fusion status bridge is smaller and easier to audit.

## Supported MCP Tools

The MCP bridge exposes only:

- `check_fusion_payload`
- `check_geometry_plan`
- `dry_run_geometry`
- `report_manual_verification_status`

It does not expose shell access or arbitrary Fusion Python execution.

## Explicitly Unsupported

- Arbitrary Python execution inside Fusion
- Arbitrary shell commands
- File deletion
- CNC export
- DXF export
- Drawings
- Cut lists
- Manufacturing-ready output or sign-off

## Path Restrictions

Read paths must be JSON files under this DraftMyVan repository, or allowlisted
DraftMyVan payload names in `/tmp`, such as:

- `/tmp/galley_1000_fusion_parameters.json`
- `/tmp/galley_1000_panels.json`

Bridge command/status files must be either:

- `/tmp/draftmyvan_fusion_command.json`
- `/tmp/draftmyvan_fusion_status.json`
- JSON files under `build/fusion/`

## Local Validation

From the repo root:

```bash
python3 tools/fusion/fusion_create_galley_v1.py \
  --dry-run /tmp/galley_1000_panels.json

python3 tests/test_fusion_local_availability.py
python3 tests/test_fusion_mcp_bridge.py
```

## MCP Server Command

Do not wire this into global Codex or Claude config until the repo tests pass
and the user approves the config change.

The eventual stdio server command is:

```bash
python3 /Users/florin/draftmyvan/tools/mcp/fusion_bridge_server.py
```

This repository intentionally does not edit `~/.codex`, `~/.claude`, or any
other global MCP config. Wiring this command into an assistant requires
explicit user approval in a later step.

Opt-in configuration examples are documented in
`docs/FUSION_MCP_OPT_IN_CONFIG.md`. They are examples only and are not applied
automatically by this repository.

Run a local stdio smoke test with:

```bash
python3 tools/mcp/smoke_fusion_bridge.py
```

## Manual Fusion Status Flow

To ask Fusion for manual verification status without opening a localhost server:

1. Use the MCP tool `report_manual_verification_status` with
   `request_status_from_fusion=true`, or write this command file manually:

```json
{
  "command": "report_manual_verification_status",
  "payload_path": "/tmp/galley_1000_panels.json",
  "status_path": "/tmp/draftmyvan_fusion_status.json"
}
```

2. In Fusion 360, run:

```text
tools/fusion/fusion_command_bridge.py
```

3. Read the status through the MCP tool `report_manual_verification_status`.

The Fusion-side command bridge only reports component/body/parameter status. It
does not create geometry. Continue to run `fusion_create_galley_v1.py` manually
for the current five-panel geometry proof.

## Current Limitations

- Status reporting depends on manually running the Fusion bridge script.
- The MCP server is stdio-only and has no network listener.
- Geometry creation remains manual and separate.
- All output is workflow evidence only and not manufacturing-ready.
