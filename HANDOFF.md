# DraftMyVan — Handoff

> **Status:** the DraftMyVan foundation now lives in its own repository.
> It has eight CI-gated pure-Python suites, a generated GLB fixture
> split into a permanent golden contract fixture and a swappable
> manifest asset (with sign-off metadata + validator), two GLB
> validators (one for CI, one for human use in Blender), material-slot
> and collision-proxy enforcement, a runtime reference consumer +
> package report, and the documented Blender export procedure with a
> concrete fixture-swap procedure for replacing the manifest asset with
> real cabinet art.

This document is the briefing for whoever picks the project up next —
whether that's the same author moving the code to a new repository,
or someone else inheriting it.

## What exists today

```
manifest.schema.json             # JSON Schema (Draft 2020-12), millimetres
examples/
  galley_1000.json               # First module manifest
  assets/
    galley_1000.glb                          # Current manifest asset (today: same bytes as the golden fixture)
    galley_1000.glb.md                       # Per-asset explainer
    galley_1000.asset_acceptance.json        # Per-asset acceptance metadata (this PR, #4)
    README.md                                # Asset directory rules
runtime/                         # Reference consumer (PR #8, #9)
  __init__.py                    # Package docstring, boundary doc, re-exports
  module.py                      # Module + Dimensions + ConsumerError
  load_module.py                 # Loader + `python -m runtime.load_module` CLI
  package_report.py              # Catalog scanner + `python -m runtime.package_report` CLI
tools/
  validate_manifest.py           # JSON-Schema validator CLI (PR #3)
  assets/
    generate_galley_fixture_glb.py    # Deterministic GLB generator (PR #6; PR #4 added the dual-output + safety net)
    validate_asset_acceptance.py      # Acceptance metadata validator (this PR, #4)
  blender/
    validate_glb_against_manifest.py  # Pure-Python GLB-vs-manifest gate (PR #4)
    validate_in_blender.py            # Authoritative bpy variant (PR #4)
    _anchor_contract.py               # Shared anchor enforcement (PR #5)
    EXPORT_REAL_ASSET.md              # Human Blender export procedure + step-9 fixture-swap procedure (PR #2 + this PR, #4)
    asset_export_checklist.md         # Per-asset sign-off sheet (PR #2)
    check_asset_ready.py              # One-command readiness wrapper (PR #2)
    README.md
  handoff/
    check_handoff_ready.py       # Extraction-readiness gate
tests/                           # Pure-Python; no Blender required
  fixtures/
    galley_1000_contract_box.glb       # Golden contract fixture — permanent regression reference (this PR, #4)
    README.md                          # Fixture-directory rules
  test_validator.py              # 10 tests
  test_blender_manifest_contract.py  # 38 tests
  test_check_asset_ready.py      # 12 tests
  test_galley_fixture.py         # 16 tests (golden + manifest asset + generator determinism + fixture-swap safety)
  test_runtime_consumer.py       # 18 tests
  test_package_report.py         # 16 tests
  test_handoff_ready.py          # 10 tests
  test_asset_acceptance.py       # 15 tests (this PR, #4)
README.md
HANDOFF.md                       # this file
EXTRACT_TO_REAL_REPO.md          # extraction checklist/archive
COMMANDS.md                      # exhaustive command reference
.github/workflows/ci.yml         # pure-Python CI
```

CI workflow lives at `.github/workflows/ci.yml`. The repository is all
DraftMyVan, so the workflow has no PaperAI path filters and no
`working-directory: draftmyvan` wrapper.

## Extraction history

PaperAI was an incubation host of convenience. DraftMyVan was extracted
into this standalone repository after PaperAI PR #10 merged. This file is
kept as project history plus a working handoff checklist for the remaining
guardrails.

## Incubation PRs that built this — what each added

Merged into PaperAI `main` before extraction:

| PR | Title | What it added |
|---|---|---|
| #3 | manifest schema, galley_1000 sample, validator, and CI gate | `manifest.schema.json` (Draft 2020-12, mm canonical, strict additionalProperties), `examples/galley_1000.json`, `tools/validate_manifest.py`, `tests/test_validator.py` (10 tests), `.github/workflows/draftmyvan.yml` scoped to `draftmyvan/**` |
| #4 | Blender-side manifest validator (scale-drift gate) | `tools/blender/validate_glb_against_manifest.py` (pure-Python GLB parser using accessor min/max), `tools/blender/validate_in_blender.py` (bpy variant for local authoritative checks), `tests/test_blender_manifest_contract.py` (23 → 30 tests) |
| #5 | enforce origin/anchor alignment for `floor_back_left` | `tools/blender/_anchor_contract.py` (shared enforcement), `floor_back_left` rule (`bbox_min ≈ (0,0,0)`, `bbox_max ≈ (W,D,H)`), other anchors fail loudly with `"anchor enforcement not implemented for <anchor>"`, 7 new tests |
| #6 | deterministic galley_1000 GLB fixture and generator | `tools/assets/generate_galley_fixture_glb.py` (stdlib-only deterministic GLB box from manifest), `examples/assets/galley_1000.glb` (804 bytes, pinned byte-for-byte), `tests/test_galley_fixture.py` (8 tests including byte-determinism), per-fixture explainer + assets dir README |
| #8 | runtime reference consumer for the manifest contract | `runtime/` package: `Module`/`Dimensions`/`ConsumerError` frozen dataclasses, `load_module(path)`, `python -m runtime.load_module` CLI, 18 tests. First **non-validator** consumer of the manifest. |
| #9 | package readiness report for `examples/` catalog | `runtime/package_report.py`, `PackageReport` aggregator + `scan_package()` + `format_report()`, `python -m runtime.package_report` CLI, 16 tests; structural-integrity checks (duplicate ids, duplicate resolved asset paths, empty/missing inputs) |

Left behind during PaperAI incubation, then redone in this repository:

| PR | Status | Why it matters |
|---|---|---|
| PaperAI **#7** | redone as draftmyvan PR #2 | Adds `tools/blender/EXPORT_REAL_ASSET.md` (the documented Blender export procedure for real cabinet art), `tools/blender/asset_export_checklist.md` (printable per-asset sign-off), `tools/blender/check_asset_ready.py` (one-command readiness wrapper), and `tests/test_check_asset_ready.py` (10 tests). It is the prerequisite for ever replacing the generated fixture with human-authored art. |
| draftmyvan **#3** | merged | Extended the GLB validators and deterministic fixture so `visual.material_slots` and `visual.collision_proxy` are enforced before any real art can land. |
| draftmyvan **#4** | this PR | Adds the fixture-swap / real-asset acceptance mechanism. Splits the generated box into a permanent golden contract fixture (`tests/fixtures/galley_1000_contract_box.glb`) and a swappable current manifest asset (`examples/assets/galley_1000.glb`). Adds per-asset acceptance metadata (`examples/assets/<id>.asset_acceptance.json`), its validator (`tools/assets/validate_asset_acceptance.py`), and its test suite (`tests/test_asset_acceptance.py`). Documents the swap procedure in `tools/blender/EXPORT_REAL_ASSET.md` step 9. No real cabinet art is added. |

## Current command suite

Full reference: `COMMANDS.md`. Headline commands:

```bash
# Manifest validation
python tools/validate_manifest.py --all

# Generate / regenerate the test fixture
python tools/assets/generate_galley_fixture_glb.py

# Validate a GLB against its manifest (pure Python, CI-safe)
python tools/blender/validate_glb_against_manifest.py \
    --manifest examples/galley_1000.json \
    --glb examples/assets/galley_1000.glb

# Run the real-asset readiness wrapper
python tools/blender/check_asset_ready.py \
    --manifest examples/galley_1000.json

# Read one manifest as typed runtime data
python -m runtime.load_module examples/galley_1000.json

# Scan the whole catalog
python -m runtime.package_report examples/

# Extraction readiness gate
python tools/handoff/check_handoff_ready.py
```

Test suites (all pure Python):

```bash
python -m tests.test_validator                    # 10 tests
python -m tests.test_blender_manifest_contract    # 38 tests
python -m tests.test_check_asset_ready            # 12 tests
python -m tests.test_galley_fixture               # 16 tests
python -m tests.test_runtime_consumer             # 18 tests
python -m tests.test_package_report               # 16 tests
python -m tests.test_handoff_ready                # 10 tests
python -m tests.test_asset_acceptance             # 15 tests
```

## Current CI assumptions

- Runner: `ubuntu-latest`.
- Python: 3.11 (`actions/setup-python@v5`).
- Third-party deps: **only** `jsonschema`. Installed via
  `python -m pip install --upgrade pip jsonschema`.
- Blender is **not** installed. The `bpy` validator
  (`tools/blender/validate_in_blender.py`) is documented as a
  local-only authoritative gate.
- Trigger scope: `workflow_dispatch`, `push`, and `pull_request`.
  No path filters are needed because the whole repository is DraftMyVan.
- Permissions: `contents: read`. Nothing more.

## Current limitations (deliberate, documented)

- **Only `floor_back_left` is enforced.** Other schema-valid anchors
  (`floor_back_right`, `floor_front_*`, `ceiling_*`, `wall_*`) fail
  loudly rather than passing silently.
- **The pure-Python GLB parser assumes identity transforms.** It reads
  POSITION-accessor `min`/`max`. For hierarchies, use the bpy variant
  (locally).
- **No real cabinet art.** The committed `examples/assets/galley_1000.glb`
  is the deterministic generated box. The fixture-swap mechanism is in
  place (this PR, #4) so real art can replace it, but no real art has
  been authored or committed yet.
- **Catalog of one.** `examples/galley_1000.json` is the only module.
- **No UE5, Fusion 360, or CNC integration.** Every PR deferred them
  deliberately.

## What must happen before moving to Unity / UE5 / Fusion

The gates above all live before the manifest reaches a renderer or a
manufacturing tool. Before that handoff, in priority order:

1. **Author real cabinet art** and swap it into
   `examples/assets/galley_1000.glb`. The fixture-swap mechanism is
   already in place — see step 9 of
   `tools/blender/EXPORT_REAL_ASSET.md`. Flip the flags in
   `examples/assets/galley_1000.asset_acceptance.json`, tighten the
   phase invariants in `tools/assets/validate_asset_acceptance.py`,
   and confirm the bpy validator agrees with the pure-Python one.
   The golden contract fixture at
   `tests/fixtures/galley_1000_contract_box.glb` stays untouched.
2. **Add anchor support beyond `floor_back_left`** as the catalog
   grows. The enforcement table is in
   `tools/blender/_anchor_contract.py:expected_corners_mm`.
3. **Decide axis-convention conversion** at the UE5 / Fusion boundary,
   not by mutating the source GLB. The contract is documented in
   `tools/blender/README.md` and `_anchor_contract.py`.
