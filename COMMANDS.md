# Command reference

Every command currently shipped in this repository. Run from the repository
root unless otherwise noted.

## Setup

```bash
pip install jsonschema   # only third-party dep
```

Python 3.11+ recommended.

## Manifest validation (PR #3)

| Command | Purpose | Exit |
|---|---|---|
| `python tools/validate_manifest.py examples/galley_1000.json` | Validate one manifest against the schema. | 0 valid, 1 invalid, 2 schema/IO error |
| `python tools/validate_manifest.py --all` | Validate every manifest under `examples/`. | same |

## GLB validation (PR #4, PR #5, PR #3)

| Command | Purpose | Exit |
|---|---|---|
| `python tools/blender/validate_glb_against_manifest.py --manifest examples/galley_1000.json --glb examples/assets/galley_1000.glb` | Pure-Python dimension + origin/anchor + material-slot + collision-proxy gate. Runs in CI. | 0 pass, 1 fail, 2 IO/parse error |

Optional flags: `--tolerance-mm <float>` (default 1.0), `--glb-units meters|millimeters` (default meters), `--ignore-path-mismatch`.

```bash
# Blender / bpy variant — authoritative, local only
blender --background --python \
    tools/blender/validate_in_blender.py -- \
    --manifest examples/galley_1000.json \
    --glb examples/assets/galley_1000.glb
```

## Asset readiness wrapper (PR #2)

| Command | Purpose | Exit |
|---|---|---|
| `python tools/blender/check_asset_ready.py --manifest examples/galley_1000.json` | One-command wrapper around manifest schema, GLB path, dimension, anchor, material-slot, and collision-proxy checks. Defaults to the current manifest asset from `visual.glb_path`. | 0 READY, 1 NOT READY, 2 ERROR |
| `python tools/blender/check_asset_ready.py --manifest examples/galley_1000.json --glb /tmp/candidate.glb` | Check a candidate GLB before it is committed. | same |

The full human export procedure is `tools/blender/EXPORT_REAL_ASSET.md`;
the printable sign-off sheet is `tools/blender/asset_export_checklist.md`.

## Generated fixture (PR #6)

| Command | Purpose |
|---|---|
| `python tools/assets/generate_galley_fixture_glb.py` | Regenerate `tests/fixtures/galley_1000_contract_box.glb` deterministically from `examples/galley_1000.json`. |
| `python tools/assets/generate_galley_fixture_glb.py --out examples/assets/galley_1000.glb` | Intentionally refresh the current manifest asset from the generator while it is still a generated fixture. Do not use this after real art replaces the manifest asset. |

`--manifest` and `--out` available as overrides. The default output is the
permanent golden contract fixture under `tests/fixtures/`; output is
byte-for-byte stable and pinned by
`test_golden_contract_fixture_matches_generator_byte_for_byte`.

## Asset acceptance metadata (PR #4)

| Command | Purpose | Exit |
|---|---|---|
| `python tools/assets/validate_asset_acceptance.py` | Validate `examples/assets/galley_1000.asset_acceptance.json`: manifest/asset references, full gate list, current generated-fixture state, and golden-fixture byte match. | 0 valid, 1 invalid |

The current manifest asset `examples/assets/galley_1000.glb` is still the
generated box. Future real art may replace that file only by updating the
acceptance metadata to an explicit real-art sign-off state while keeping
`tests/fixtures/galley_1000_contract_box.glb` as the permanent generated
reference.

## Candidate asset workflow

| Command | Purpose | Exit |
|---|---|---|
| `blender --background --python tools/blender/create_galley_candidate.py -- --manifest examples/galley_1000.json --out examples/assets/candidates/galley_1000_candidate.glb` | Regenerate the script-generated Blender cabinet blockout candidate. Local only; does not replace the manifest asset. | Blender exit code |
| `python tools/assets/validate_candidate_asset.py examples/assets/candidates/galley_1000_candidate.asset_acceptance.json` | Validate candidate metadata and, when the candidate GLB exists, run the same GLB gates with manifest path mismatch explicitly allowed for candidate storage. | 0 ready or plan-only, 1 invalid |

Candidate states:

| result | meaning |
|---|---|
| `CANDIDATE READY` | Candidate metadata is valid, the candidate GLB exists, and the GLB gate passes. |
| `CANDIDATE PLAN ONLY` | Metadata explicitly documents a candidate plan but does not claim a GLB exists yet. |
| `CANDIDATE INVALID` | Metadata is malformed, claims production/promotion too early, references missing required files, or the candidate GLB fails a gate. |

The current `galley_1000_candidate.glb` is a script-generated Blender cabinet
blockout. The generator strictly requires integer manifest dimensions and
rejects strings, floats, booleans, missing fields, and non-positive values
before any geometry is authored. The candidate has visible panel seams, a
countertop break, plinth, and sink marker, but it is still not production art
and does not replace `examples/assets/galley_1000.glb`.

## Candidate review metadata

| Command | Purpose | Exit |
|---|---|---|
| `python tools/assets/validate_candidate_review.py examples/assets/candidates/galley_1000_candidate_review.json` | Validate candidate review metadata, candidate/golden SHA pins, linked candidate acceptance metadata, non-production state, and non-promotion state. | 0 valid, 1 invalid |

Candidate validation means the GLB passes the contract gate. It does not mean
visual quality, topology quality, UV/material quality, manufacturability, or
promotion readiness has been accepted. Candidate review metadata must stay in
sync with the exact candidate SHA, and promotion requires a future explicit PR.

## Candidate visual audit metadata

| Command | Purpose | Exit |
|---|---|---|
| `python tools/assets/validate_candidate_visual_audit.py examples/assets/candidates/galley_1000_candidate_visual_audit.json` | Validate SHA-synced visual audit metadata, non-production visual status, do-not-promote recommendation, findings, and required visual improvements. | 0 valid, 1 invalid |

Visual audit is separate from validation and review. It records current visual
findings and required improvements, but does not make the candidate
production-ready. The committed render evidence records six review views of
the current blockout only; those PNGs are not product screenshots and do not
promote the candidate. The local procedure is
`tools/blender/RENDER_CANDIDATE_AUDIT.md`.

## Candidate render evidence workflow

| Command | Purpose | Exit |
|---|---|---|
| `python tools/assets/validate_render_evidence.py examples/assets/candidates/galley_1000_candidate_render_evidence.json` | Validate render-evidence metadata: candidate SHA, visual-audit reference, render script path, expected views, committed PNG paths/sizes/SHA256 values, and non-promotion flags. | 0 valid, 1 invalid |
| `blender --background --python tools/blender/render_candidate_views.py -- --candidate examples/assets/candidates/galley_1000_candidate.glb --out examples/assets/candidates/render_evidence/galley_1000_candidate/` | Generate local PNG evidence views when Blender is available. The renderer orients the GLB contract axes for Blender review and hides `UCX_` collision proxies from the visual output. | Blender exit code |

Render evidence supports human review only. The six approved PNGs under
`examples/assets/candidates/render_evidence/galley_1000_candidate/` are
committed review evidence for the current blockout, not product screenshots.
Their metadata records the 1024 x 1024 Workbench render setup and local area
key light description from `tools/blender/render_candidate_views.py`.
Other generated PNG output under `examples/assets/candidates/render_evidence/`
remains ignored. Future candidate changes require regenerating the PNGs and
updating their pinned file sizes and SHA256 values.

## Candidate human visual review metadata

| Command | Purpose | Exit |
|---|---|---|
| `python tools/assets/validate_human_visual_review.py examples/assets/candidates/galley_1000_candidate_human_visual_review.json` | Validate human review observations against the committed render evidence, linked visual audit metadata, non-production state, and do-not-promote recommendation. | 0 valid, 1 invalid |

Human visual review records what the committed render evidence actually shows.
It does not equal production approval, visual sign-off, manufacturability
approval, or promotion readiness. The current review says the blockout is
useful for visual review but still not production-ready. The next recommended
action is either to improve the candidate again or begin a separate Fusion
proof while the visual candidate remains blockout-only.

## Fusion parameter map, panel math, and manual geometry path

| Command | Purpose | Exit |
|---|---|---|
| `python tools/fusion/validate_fusion_parameter_map.py tools/fusion/galley_v1_parameter_map.json` | Validate the pure-Python manifest-to-`galley_v1` parameter map, required integer millimetre parameters, explicit ignored fields, and no visual-field consumption. | 0 valid, 1 invalid |
| `python tools/fusion/export_galley_v1_parameters.py --manifest examples/galley_1000.json --out build/fusion/galley_1000_fusion_parameters.json` | Write deterministic dry-run parameters for later Fusion work. The `build/` output is ignored by Git. | 0 written, 1 error |
| `python tools/fusion/check_fusion_payload.py tests/fixtures/galley_1000_fusion_parameters.expected.json` | Validate a `galley_v1` payload through the Fusion script skeleton helpers and print template, manifest id, dimensions, plywood thickness, and hardware count. | 0 valid, 1 invalid |
| `python tools/fusion/export_galley_v1_panels.py --payload tests/fixtures/galley_1000_fusion_parameters.expected.json --out build/fusion/galley_1000_panels.json` | Export deterministic simple carcass panel math and documented assumptions. This is not a real cut list. | 0 exported, 1 invalid |
| `python tools/fusion/check_fusion_geometry_plan.py tests/fixtures/galley_1000_panels.expected.json` | Validate the deterministic planned-not-executed Fusion component/body plan from the panel payload. | 0 valid, 1 invalid |
| `python tools/fusion/check_fusion_geometry_plan.py --verbose tests/fixtures/galley_1000_panels.expected.json` | Print each planned panel sketch plane, extrude axis, extrude distance, and placement origin. | 0 valid, 1 invalid |
| `python tools/fusion/fusion_create_galley_v1.py --dry-run tests/fixtures/galley_1000_panels.expected.json` | Validate the panel payload and summarize the manual Fusion body-creation path without Fusion installed. | 0 valid, 1 invalid |

Fusion execution is local/manual only. The scripts guard Autodesk `adsk`
imports so normal Python CI can import and test them without Fusion installed.
Panel math is simple carcass explanation only: no kerf, rabbets/dados, edging,
door/drawer fronts, sink cut-out, or hardware drilling. The geometry plan maps
those five panels to future Fusion component/body names, sketch planes, extrude
axes, extrusion distances, and provisional placement origins. The manual Fusion
path can create the five rectangular panel bodies only when run inside Fusion
with a valid payload. CI exercises `--dry-run` only; it does not generate Fusion
bodies, drawings, real cut lists, or DXF/CNC files, and does not claim
manufacturing-ready output.

```text
+---------------- top_panel ----------------+
| left_side      back_panel      right_side |
|                                          |
+-------------- bottom_panel --------------+
```

Sequence:

```text
payload -> panel math -> geometry plan -> manual Fusion geometry
```

Manual run docs:

- `tools/fusion/RUN_FUSION_GEOMETRY_MANUAL.md`
- `tools/fusion/MANUAL_FUSION_GEOMETRY_CHECKLIST.md`

## Fusion MCP bridge skeleton

| Command | Purpose | Exit |
|---|---|---|
| `python tools/mcp/fusion_bridge_server.py` | Start the local stdio MCP bridge process. It is not globally enabled by repo code. | MCP stdio process |
| `python tools/fusion/fusion_command_bridge.py --validate-command /tmp/draftmyvan_fusion_command.json` | Validate the narrow Fusion file-command bridge request shape outside Fusion. | 0 valid, 1 invalid |
| `python -m tests.test_fusion_local_availability` | Verify Fusion absence is reported clearly and report-only status does not create output. | 0 pass, 1 fail |
| `python -m tests.test_fusion_mcp_bridge` | Verify the MCP bridge allowlist and report-only command validation. | 0 pass, 1 fail |

The bridge exposes only four allowlisted tools:

- `check_fusion_payload`
- `check_geometry_plan`
- `dry_run_geometry`
- `report_manual_verification_status`

The design is Option A plus a narrow Option B: stdio validation outside Fusion,
plus an optional fixed command/status JSON file for manual Fusion status
reporting. It does not wire global Codex/Claude MCP config, does not start a
localhost server, does not execute arbitrary shell or Fusion Python, and does
not generate drawings, cut lists, DXF, CNC, or manufacturing-ready output.
Manual config wiring requires explicit user approval later.

## Runtime consumer (PR #8)

| Command | Purpose | Exit |
|---|---|---|
| `python -m runtime.load_module examples/galley_1000.json` | Read one manifest as a typed `Module`; print id/dimensions/anchor/etc. + asset-present yes/no. | 0 CONSUMABLE, 1 NOT CONSUMABLE (GLB missing), 2 ERROR |

## Package readiness report (PR #9)

| Command | Purpose | Exit |
|---|---|---|
| `python -m runtime.package_report examples/` | Scan a directory of manifests, load each, aggregate, detect duplicate ids and resolved asset paths. | 0 PACKAGE READY, 1 PACKAGE NOT READY, 2 ERROR (malformed / duplicates / empty dir) |

## Extraction readiness (this PR, #10)

| Command | Purpose | Exit |
|---|---|---|
| `python tools/handoff/check_handoff_ready.py` | Static checks: required files present, no host-app references in DraftMyVan Python files. CI-safe. | 0 ready, 1 not ready |
| `python tools/handoff/check_handoff_ready.py --include-dynamic` | All static checks + the package report + every test module via subprocess. Local-only (slower). | same |

## Test suites — pure Python, no Blender

```bash
python -m tests.test_validator                    # 10 tests — schema + manifest
python -m tests.test_blender_manifest_contract    # 38 tests — Blender gate, anchor/material/proxy enforcement
python -m tests.test_check_asset_ready            # 12 tests — real-asset readiness wrapper
python -m tests.test_galley_fixture               # 15 tests — golden fixture + current manifest asset
python -m tests.test_asset_acceptance             # 12 tests — fixture-swap metadata guard
python -m tests.test_candidate_asset              # 13 tests — candidate workflow guard
python -m tests.test_create_galley_candidate      # 7 tests — candidate generator manifest guard
python -m tests.test_candidate_review             # 13 tests — candidate review guard
python -m tests.test_candidate_visual_audit       # 11 tests — candidate visual audit guard
python -m tests.test_render_evidence              # 20 tests — render evidence metadata guard
python -m tests.test_human_visual_review          # 14 tests — human visual review guard
python -m tests.test_fusion_parameter_map         # 10 tests — Fusion dry-run mapping guard
python -m tests.test_fusion_skeleton              # 10 tests — Fusion skeleton payload guard
python -m tests.test_fusion_panel_math            # 11 tests — Fusion panel math guard
python -m tests.test_fusion_geometry_plan         # 17 tests — Fusion geometry plan guard
python -m tests.test_fusion_geometry_execution_skeleton # 11 tests — guarded Fusion execution skeleton
python -m tests.test_fusion_local_availability    # 4 tests — local Fusion availability boundary
python -m tests.test_fusion_mcp_bridge            # 12 tests — allowlisted Fusion MCP bridge
python -m tests.test_runtime_consumer             # 18 tests — manifest read as typed runtime data
python -m tests.test_package_report               # 16 tests — catalog/package readiness
python -m tests.test_handoff_ready                # 10 tests — extraction readiness helper
```

Run them all:

```bash
for t in tests.test_validator tests.test_blender_manifest_contract \
         tests.test_check_asset_ready tests.test_galley_fixture \
         tests.test_asset_acceptance tests.test_candidate_asset \
         tests.test_create_galley_candidate tests.test_candidate_review \
         tests.test_candidate_visual_audit tests.test_render_evidence \
         tests.test_human_visual_review \
         tests.test_fusion_parameter_map \
         tests.test_fusion_skeleton \
         tests.test_fusion_panel_math \
         tests.test_fusion_geometry_plan \
         tests.test_fusion_geometry_execution_skeleton \
         tests.test_fusion_local_availability \
         tests.test_fusion_mcp_bridge \
         tests.test_runtime_consumer \
         tests.test_package_report \
         tests.test_handoff_ready ; do
    echo "=== $t" ; python -m $t || break
done
```

## What is NOT here

These commands are still deliberately absent: UE5 import, globally enabled
Fusion automation, localhost Fusion MCP server, arbitrary shell execution,
CNC/post-processing, drawings, dashboard/UI, catalog expansion, and real
cabinet art.
