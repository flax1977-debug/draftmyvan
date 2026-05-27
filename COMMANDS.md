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

## GLB validation (PR #4, PR #5)

| Command | Purpose | Exit |
|---|---|---|
| `python tools/blender/validate_glb_against_manifest.py --manifest examples/galley_1000.json --glb examples/assets/galley_1000.glb` | Pure-Python dimension + origin/anchor gate. Runs in CI. | 0 pass, 1 fail, 2 IO/parse error |

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
| `python tools/blender/check_asset_ready.py --manifest examples/galley_1000.json` | One-command wrapper around manifest schema, GLB path, dimension, and anchor checks. Defaults to the committed fixture from `visual.glb_path`. | 0 READY, 1 NOT READY, 2 ERROR |
| `python tools/blender/check_asset_ready.py --manifest examples/galley_1000.json --glb /tmp/candidate.glb` | Check a candidate GLB before it is committed. | same |

The full human export procedure is `tools/blender/EXPORT_REAL_ASSET.md`;
the printable sign-off sheet is `tools/blender/asset_export_checklist.md`.

## Generated fixture (PR #6)

| Command | Purpose |
|---|---|
| `python tools/assets/generate_galley_fixture_glb.py` | Regenerate `examples/assets/galley_1000.glb` deterministically from `examples/galley_1000.json`. |

`--manifest` and `--out` available as overrides; defaults match the canonical paths. Output is byte-for-byte stable; the file's bytes are pinned by `test_committed_fixture_matches_generator_byte_for_byte`.

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
python -m tests.test_blender_manifest_contract    # 30 tests — Blender gate, anchor enforcement
python -m tests.test_check_asset_ready            # 9 tests — real-asset readiness wrapper
python -m tests.test_galley_fixture               # 8 tests — committed fixture + generator determinism
python -m tests.test_runtime_consumer             # 18 tests — manifest read as typed runtime data
python -m tests.test_package_report               # 16 tests — catalog/package readiness
python -m tests.test_handoff_ready                # 10 tests — extraction readiness helper
```

Run them all:

```bash
for t in tests.test_validator tests.test_blender_manifest_contract \
         tests.test_check_asset_ready tests.test_galley_fixture \
         tests.test_runtime_consumer tests.test_package_report \
         tests.test_handoff_ready ; do
    echo "=== $t" ; python -m $t || break
done
```

## What is NOT here

These commands are still deliberately absent: UE5 import, Fusion 360,
CNC/post-processing, dashboard/UI, catalog expansion, material-slot
enforcement, collision-proxy enforcement, and real cabinet art.
