# Fusion MCP Opt-In Configuration

This repository provides a local, repo-owned Fusion MCP bridge, but it does
not modify global MCP configuration. Nothing in this repo edits `~/.codex`,
`~/.claude`, Claude Desktop settings, Codex settings, or any other global
assistant configuration.

Use this page only when you intentionally want to enable the bridge by hand.

## Prerequisites

- DraftMyVan checked out at `/Users/florin/draftmyvan`.
- Python 3.11+ available as `python3`.
- Repo tests passing, especially:

```bash
cd /Users/florin/draftmyvan
python3 -m tests.test_fusion_mcp_bridge
python3 -m tests.test_fusion_local_availability
python3 tools/mcp/smoke_fusion_bridge.py
```

- No need to install Fusion, Autodesk modules, or third-party MCP packages for
  the stdio validation bridge.

## What The Bridge Exposes

Only these four allowlisted tools exist:

- `check_fusion_payload`
- `check_geometry_plan`
- `dry_run_geometry`
- `report_manual_verification_status`

The bridge does not expose arbitrary shell execution, `eval`, generic command
running, file deletion, a localhost server, or arbitrary Fusion Python
execution. It does not create CNC, DXF, drawings, cut lists, or
manufacturing-ready output.

## Run The Bridge Manually

From the repository root:

```bash
cd /Users/florin/draftmyvan
python3 tools/mcp/fusion_bridge_server.py
```

That command starts a stdio MCP process. It waits for JSON-RPC messages on
stdin and writes JSON-RPC responses to stdout. Press `Ctrl+C` or close stdin to
stop it.

## Smoke Test Tools/List

You can send a single `tools/list` JSON-RPC request:

```bash
cd /Users/florin/draftmyvan
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
  | python3 tools/mcp/fusion_bridge_server.py
```

Expected result: a JSON-RPC response whose `tools` array contains exactly the
four allowlisted tools listed above.

## Smoke Test Dry-Run Geometry

This invokes `dry_run_geometry` through the bridge against the committed panel
fixture. It does not run Fusion and does not create geometry.

```bash
cd /Users/florin/draftmyvan
printf '%s\n' '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"dry_run_geometry","arguments":{"panel_payload_path":"tests/fixtures/galley_1000_panels.expected.json"}}}' \
  | python3 tools/mcp/fusion_bridge_server.py
```

Expected result: the response payload includes:

```text
FUSION GEOMETRY DRY RUN VALID
```

You can also run the repo smoke helper:

```bash
cd /Users/florin/draftmyvan
python3 tools/mcp/smoke_fusion_bridge.py
```

Expected final line:

```text
RESULT: FUSION MCP BRIDGE SMOKE PASS
```

## Codex Config Example

Example only. Codex MCP config shape and location can vary by app/version, so
verify the exact current Codex documentation before editing your own config.
Do not paste this blindly.

```toml
# PSEUDO-CONFIG ONLY
# Add a local MCP server named draftmyvan-fusion.
[mcp_servers.draftmyvan-fusion]
command = "python3"
args = ["/Users/florin/draftmyvan/tools/mcp/fusion_bridge_server.py"]
cwd = "/Users/florin/draftmyvan"
```

Disable it by removing this example block from your Codex config and restarting
the Codex app/session that loaded it.

## Claude Config Example

Example only. Claude MCP config shape and location can vary by Claude product
and version. Some Claude clients use an `mcpServers` JSON object, but you must
verify the exact location and schema for your installed client before editing.

```json
{
  "mcpServers": {
    "draftmyvan-fusion": {
      "command": "python3",
      "args": [
        "/Users/florin/draftmyvan/tools/mcp/fusion_bridge_server.py"
      ],
      "cwd": "/Users/florin/draftmyvan"
    }
  }
}
```

Disable it by removing the `draftmyvan-fusion` entry from your Claude MCP
config and restarting the Claude app/session that loaded it.

## Security Notes

- This repo never edits global MCP configuration automatically.
- The bridge is stdio-only and starts no localhost listener.
- The bridge imports allowlisted DraftMyVan validation helpers directly; it does
  not run arbitrary shell commands.
- File reads are restricted to repo JSON files and allowlisted DraftMyVan JSON
  payload names in `/tmp`.
- Command/status file writes are restricted to `/tmp/draftmyvan_fusion_*.json`
  or `build/fusion/`.
- Fusion status reporting is manual and can become stale. Re-run the manual
  Fusion status flow when you need fresh evidence.
- Fusion geometry execution remains manual/deferred and separate from this
  opt-in MCP configuration.

## Remove Or Disable Later

To disable the bridge:

1. Remove the `draftmyvan-fusion` MCP server entry from your assistant config.
2. Restart the assistant app/session.
3. Confirm `tools/list` no longer shows `draftmyvan-fusion`.

No repository file needs to change to disable a local opt-in config.
