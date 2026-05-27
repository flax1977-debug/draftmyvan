# DraftMyVan — Handoff

> **Status:** the DraftMyVan foundation now lives in its own repository.
> It has eleven CI-gated pure-Python suites, a permanent generated GLB
> contract fixture, current-asset acceptance metadata, candidate acceptance,
> review, and visual-audit metadata, two GLB validators (one for CI, one for
> human use in Blender), material-slot and collision-proxy enforcement, a
> runtime reference consumer + package report, and documented Blender export
> and local visual-audit procedures.

This document is the briefing for whoever picks the project up next —
whether that's the same author moving the code to a new repository,
or someone else inheriting it.

## What exists today

```
manifest.schema.json             # JSON Schema (Draft 2020-12), millimetres
examples/
  galley_1000.json               # First module manifest
  assets/
    galley_1000.glb              # Current manifest asset; still generated box today
    galley_1000.asset_acceptance.json  # Current asset acceptance state
    galley_1000.glb.md           # Per-asset explainer
    candidates/
      README.md                  # Candidate directory rules
      PROMOTION_CRITERIA.md      # Human promotion criteria
      candidate_review_checklist.md
      galley_1000_candidate.glb  # Simple Blender-exported candidate, not manifest asset
      galley_1000_candidate.asset_acceptance.json
      galley_1000_candidate_review.json
      galley_1000_candidate_review.md
      galley_1000_candidate_visual_audit.json
      galley_1000_candidate_visual_audit.md
    README.md                    # Asset directory rules
runtime/                         # Reference consumer (PR #8, #9)
  __init__.py                    # Package docstring, boundary doc, re-exports
  module.py                      # Module + Dimensions + ConsumerError
  load_module.py                 # Loader + `python -m runtime.load_module` CLI
  package_report.py              # Catalog scanner + `python -m runtime.package_report` CLI
tools/
  validate_manifest.py           # JSON-Schema validator CLI (PR #3)
  assets/
    generate_galley_fixture_glb.py  # Deterministic GLB generator (PR #6)
    validate_asset_acceptance.py    # Fixture-swap metadata guard
    validate_candidate_asset.py     # Candidate workflow metadata + GLB gate
    validate_candidate_review.py    # Candidate review metadata + SHA gate
    validate_candidate_visual_audit.py  # Visual audit metadata + SHA gate
  blender/
    validate_glb_against_manifest.py  # Pure-Python GLB-vs-manifest gate (PR #4)
    validate_in_blender.py            # Authoritative bpy variant (PR #4)
    _anchor_contract.py               # Shared anchor enforcement (PR #5)
    EXPORT_REAL_ASSET.md              # Human Blender export procedure (PR #2)
    RENDER_CANDIDATE_AUDIT.md         # Local visual audit render procedure
    asset_export_checklist.md         # Per-asset sign-off sheet (PR #2)
    check_asset_ready.py              # One-command readiness wrapper (PR #2)
    README.md
  handoff/
    check_handoff_ready.py       # Extraction-readiness gate
tests/                           # Pure-Python; no Blender required
  fixtures/
    galley_1000_contract_box.glb # Permanent golden generated fixture
    README.md
  test_validator.py              # 10 tests
  test_blender_manifest_contract.py  # 38 tests
  test_check_asset_ready.py      # 12 tests
  test_galley_fixture.py         # 15 tests
  test_asset_acceptance.py       # 12 tests
  test_candidate_asset.py        # 13 tests
  test_candidate_review.py       # 13 tests
  test_candidate_visual_audit.py # 11 tests
  test_runtime_consumer.py       # 18 tests
  test_package_report.py         # 16 tests
  test_handoff_ready.py          # 10 tests
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
| #6 | deterministic galley_1000 GLB fixture and generator | `tools/assets/generate_galley_fixture_glb.py` (stdlib-only deterministic GLB box from manifest), the first generated `examples/assets/galley_1000.glb`, `tests/test_galley_fixture.py` (8 tests including byte-determinism), per-fixture explainer + assets dir README |
| #8 | runtime reference consumer for the manifest contract | `runtime/` package: `Module`/`Dimensions`/`ConsumerError` frozen dataclasses, `load_module(path)`, `python -m runtime.load_module` CLI, 18 tests. First **non-validator** consumer of the manifest. |
| #9 | package readiness report for `examples/` catalog | `runtime/package_report.py`, `PackageReport` aggregator + `scan_package()` + `format_report()`, `python -m runtime.package_report` CLI, 16 tests; structural-integrity checks (duplicate ids, duplicate resolved asset paths, empty/missing inputs) |

Left behind during PaperAI incubation, then redone in this repository:

| PR | Status | Why it matters |
|---|---|---|
| PaperAI **#7** | redone as draftmyvan PR #2 | Adds `tools/blender/EXPORT_REAL_ASSET.md` (the documented Blender export procedure for real cabinet art), `tools/blender/asset_export_checklist.md` (printable per-asset sign-off), `tools/blender/check_asset_ready.py` (one-command readiness wrapper), and `tests/test_check_asset_ready.py` (10 tests). It is the prerequisite for ever replacing the generated fixture with human-authored art. |
| draftmyvan **#3** | merged | Extends the GLB validators and deterministic fixture so `visual.material_slots` and `visual.collision_proxy` are enforced before any real art can land. |
| draftmyvan **#4** | merged | Separates the permanent generated contract fixture (`tests/fixtures/galley_1000_contract_box.glb`) from the current manifest asset (`examples/assets/galley_1000.glb`) and adds acceptance metadata/validation so a future real-art swap cannot weaken schema, dimension, anchor, material-slot, or collision-proxy gates. |
| Candidate workflow PR | merged | Adds the first candidate asset area and a simple Blender-exported `galley_1000_candidate.glb`, plus candidate-only metadata and validation. It does not replace the manifest asset or polished real art. |
| Candidate review PR | merged | Adds SHA-pinned review metadata, a review report, checklist, promotion criteria, and a validator that keeps the candidate non-production and non-promotable. |
| Candidate visual audit PR | this slice | Adds SHA-pinned visual audit metadata and a local Blender render/audit procedure. It records findings without committing render images or promoting the candidate. |

## Current command suite

Full reference: `COMMANDS.md`. Headline commands:

```bash
# Manifest validation
python tools/validate_manifest.py --all

# Generate / regenerate the golden contract fixture
python tools/assets/generate_galley_fixture_glb.py

# Validate a GLB against its manifest (pure Python, CI-safe)
python tools/blender/validate_glb_against_manifest.py \
    --manifest examples/galley_1000.json \
    --glb examples/assets/galley_1000.glb

# Run the real-asset readiness wrapper
python tools/blender/check_asset_ready.py \
    --manifest examples/galley_1000.json

# Validate current asset acceptance metadata
python tools/assets/validate_asset_acceptance.py

# Validate candidate asset metadata and candidate GLB
python tools/assets/validate_candidate_asset.py \
    examples/assets/candidates/galley_1000_candidate.asset_acceptance.json

# Validate candidate review metadata
python tools/assets/validate_candidate_review.py \
    examples/assets/candidates/galley_1000_candidate_review.json

# Validate candidate visual audit metadata
python tools/assets/validate_candidate_visual_audit.py \
    examples/assets/candidates/galley_1000_candidate_visual_audit.json

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
python -m tests.test_galley_fixture               # 15 tests
python -m tests.test_asset_acceptance             # 12 tests
python -m tests.test_candidate_asset              # 13 tests
python -m tests.test_candidate_review             # 13 tests
python -m tests.test_candidate_visual_audit       # 11 tests
python -m tests.test_runtime_consumer             # 18 tests
python -m tests.test_package_report               # 16 tests
python -m tests.test_handoff_ready                # 10 tests
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
- **No real cabinet art.** The committed `galley_1000.glb` is still the
  generated box, but it is now only the current manifest asset. The
  permanent golden generated reference lives at
  `tests/fixtures/galley_1000_contract_box.glb`, and
  `examples/assets/galley_1000.asset_acceptance.json` records that no
  production art has been reviewed or accepted. The candidate GLB under
  `examples/assets/candidates/` is a process test only and is not referenced
  by the manifest. Candidate review metadata is SHA-pinned and explicitly
  says the candidate is not production art and not promotion-ready. Candidate
  visual audit metadata is also SHA-pinned and currently says
  `not_production_ready` / `do_not_promote`; render images are not committed
  yet.
- **Catalog of one.** `examples/galley_1000.json` is the only module.
- **No UE5, Fusion 360, or CNC integration.** Every PR deferred them
  deliberately.

## What must happen before moving to Unity / UE5 / Fusion

The gates above all live before the manifest reaches a renderer or a
manufacturing tool. Before that handoff, in priority order:

1. **Promote a reviewed candidate through the acceptance metadata gate.**
   The candidate must pass schema, dimensions, `floor_back_left` anchor,
   material-slot, and collision-proxy validation; its review metadata must
   match the exact candidate SHA; its visual audit metadata must match the
   exact candidate SHA and record current findings; human visual/manufacturing
   sign-off must be recorded; promotion replaces only
   `examples/assets/galley_1000.glb`; and the golden generated fixture under
   `tests/fixtures/` stays as the byte-for-byte regression reference.
2. **Add anchor support beyond `floor_back_left`** as the catalog
   grows. The enforcement table is in
   `tools/blender/_anchor_contract.py:expected_corners_mm`.
3. **Decide axis-convention conversion** at the UE5 / Fusion boundary,
   not by mutating the source GLB. The contract is documented in
   `tools/blender/README.md` and `_anchor_contract.py`.
