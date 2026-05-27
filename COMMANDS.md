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
| `python tools/blender/check_asset_ready.py --manifest examples/galley_1000.json` | One-command wrapper around manifest schema, GLB path, dimension, anchor, material-slot, and collision-proxy checks. Defaults to the committed fixture from `visual.glb_path`. | 0 READY, 1 NOT READY, 2 ERROR |
| `python tools/blender/check_asset_ready.py --manifest examples/galley_1000.json --glb /tmp/candidate.glb` | Check a candidate GLB before it is committed. | same |

The full human export procedure is `tools/blender/EXPORT_REAL_ASSET.md`;
the printable sign-off sheet is `tools/blender/asset_export_checklist.md`.

## Generated fixture (PR #6, PR #4)

| Command | Purpose |
|---|---|
| `python tools/assets/generate_galley_fixture_glb.py` | Regenerate both the **golden contract fixture** (`tests/fixtures/galley_1000_contract_box.glb`) and the **current manifest asset** (`examples/assets/galley_1000.glb`) deterministically from `examples/galley_1000.json`. The manifest-asset write is skipped automatically once `examples/assets/galley_1000.asset_acceptance.json` declares `generated_fixture_replaced: true`. |
| `python tools/assets/generate_galley_fixture_glb.py --out /tmp/x.glb` | Generate a candidate GLB at an arbitrary path; never touches the canonical defaults. |
| `python tools/assets/generate_galley_fixture_glb.py --skip-manifest-asset` | Refresh only the golden fixture; always leave the manifest asset alone. |

The golden fixture is the permanent regression reference: its bytes are pinned by `test_golden_fixture_matches_generator_byte_for_byte`. The manifest asset is the file `examples/galley_1000.json` actually points at; while no real cabinet art has landed, its bytes are kept identical to the golden fixture by `test_manifest_asset_equals_golden_while_fixture_not_replaced`.

## Asset-acceptance metadata (this PR, #4)

| Command | Purpose | Exit |
|---|---|---|
| `python tools/assets/validate_asset_acceptance.py examples/assets/galley_1000.asset_acceptance.json` | Validate one acceptance metadata file: manifest/asset existence, manifest_id match, validator command present, full gate list declared, phase invariants for the "no real art yet" state (`generated_fixture_replaced: false`, `human_signoff.production_art: false`). | 0 valid, 1 invalid, 2 IO error |
| `python tools/assets/validate_asset_acceptance.py --all` | Validate every `*.asset_acceptance.json` under `examples/assets/`. | same |

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
python -m tests.test_galley_fixture               # 16 tests — golden fixture + manifest asset + generator determinism
python -m tests.test_runtime_consumer             # 18 tests — manifest read as typed runtime data
python -m tests.test_package_report               # 16 tests — catalog/package readiness
python -m tests.test_handoff_ready                # 10 tests — extraction readiness helper
python -m tests.test_asset_acceptance             # 15 tests — acceptance metadata validator
```

Run them all:

```bash
for t in tests.test_validator tests.test_blender_manifest_contract \
         tests.test_check_asset_ready tests.test_galley_fixture \
         tests.test_runtime_consumer tests.test_package_report \
         tests.test_handoff_ready tests.test_asset_acceptance ; do
    echo "=== $t" ; python -m $t || break
done
```

## What is NOT here

These commands are still deliberately absent: UE5 import, Fusion 360,
CNC/post-processing, dashboard/UI, catalog expansion, and real cabinet
art.

The **fixture-swap mechanism** is now in place (PR #4) — i.e. the
machinery that lets a future PR swap real cabinet art into
`examples/assets/galley_1000.glb` without weakening the golden
contract fixture or its determinism test. PR #4 does not introduce
real art; it only documents the procedure, splits the asset roles,
and adds the acceptance metadata + validator.
