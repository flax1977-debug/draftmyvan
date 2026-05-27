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
| `python tools/assets/validate_candidate_asset.py examples/assets/candidates/galley_1000_candidate.asset_acceptance.json` | Validate candidate metadata and, when the candidate GLB exists, run the same GLB gates with manifest path mismatch explicitly allowed for candidate storage. | 0 ready or plan-only, 1 invalid |

Candidate states:

| result | meaning |
|---|---|
| `CANDIDATE READY` | Candidate metadata is valid, the candidate GLB exists, and the GLB gate passes. |
| `CANDIDATE PLAN ONLY` | Metadata explicitly documents a candidate plan but does not claim a GLB exists yet. |
| `CANDIDATE INVALID` | Metadata is malformed, claims production/promotion too early, references missing required files, or the candidate GLB fails a gate. |

The current `galley_1000_candidate.glb` is a simple Blender-exported process
test. It does not replace `examples/assets/galley_1000.glb`.

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
python -m tests.test_runtime_consumer             # 18 tests — manifest read as typed runtime data
python -m tests.test_package_report               # 16 tests — catalog/package readiness
python -m tests.test_handoff_ready                # 10 tests — extraction readiness helper
```

Run them all:

```bash
for t in tests.test_validator tests.test_blender_manifest_contract \
         tests.test_check_asset_ready tests.test_galley_fixture \
         tests.test_asset_acceptance tests.test_candidate_asset \
         tests.test_runtime_consumer \
         tests.test_package_report \
         tests.test_handoff_ready ; do
    echo "=== $t" ; python -m $t || break
done
```

## What is NOT here

These commands are still deliberately absent: UE5 import, Fusion 360,
CNC/post-processing, dashboard/UI, catalog expansion, and real cabinet
art.
