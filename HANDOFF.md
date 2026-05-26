# DraftMyVan — Handoff

> **Status (as of this PR):** the DraftMyVan foundation is self-contained
> under `draftmyvan/`. It has six CI-gated pure-Python suites, a
> generated GLB fixture, two validators (one for CI, one for human use in
> Blender), and a runtime reference consumer + package report. It is
> ready to be extracted out of the PaperAI repository and live in its
> own home.

This document is the briefing for whoever picks the project up next —
whether that's the same author moving the code to a new repository,
or someone else inheriting it.

## What exists today

```
draftmyvan/
  manifest.schema.json           # JSON Schema (Draft 2020-12), millimetres
  examples/
    galley_1000.json             # First module manifest
    assets/
      galley_1000.glb            # Deterministic 1000×520×900 mm fixture box
      galley_1000.glb.md         # Per-fixture explainer
      README.md                  # Asset directory rules
  runtime/                       # Reference consumer (PR #8, #9)
    __init__.py                  # Package docstring, boundary doc, re-exports
    module.py                    # Module + Dimensions + ConsumerError
    load_module.py               # Loader + `python -m runtime.load_module` CLI
    package_report.py            # Catalog scanner + `python -m runtime.package_report` CLI
  tools/
    validate_manifest.py         # JSON-Schema validator CLI (PR #3)
    assets/
      generate_galley_fixture_glb.py  # Deterministic GLB generator (PR #6)
    blender/
      validate_glb_against_manifest.py  # Pure-Python GLB-vs-manifest gate (PR #4)
      validate_in_blender.py            # Authoritative bpy variant (PR #4)
      _anchor_contract.py               # Shared anchor enforcement (PR #5)
      README.md
    handoff/
      check_handoff_ready.py     # This PR — extraction-readiness gate
  tests/                         # Pure-Python; no Blender / Flutter required
    test_validator.py            # 10 tests
    test_blender_manifest_contract.py  # 30 tests
    test_galley_fixture.py       # 8 tests
    test_runtime_consumer.py     # 18 tests
    test_package_report.py       # 16 tests
    test_handoff_ready.py        # This PR
  README.md
  HANDOFF.md                     # this file
  EXTRACT_TO_REAL_REPO.md        # step-by-step extraction checklist
  COMMANDS.md                    # exhaustive command reference
```

CI workflow lives at `.github/workflows/draftmyvan.yml` in the host
repository. It is path-scoped to `draftmyvan/**` and the workflow
file itself, so changes to PaperAI's Flutter code never trigger it
and vice versa.

## Why this lives under PaperAI today

PaperAI was an incubation host of convenience. The remote-execution
environment that authored these PRs is scoped to the `paperai`
repository, and the alternative — creating a new GitHub repo from
scratch — was outside the environment's permissions. Co-locating in
`draftmyvan/` was the documented compromise (see PR #3's audit
report). The Flutter app under `lib/` and DraftMyVan under
`draftmyvan/` have **zero** build coupling.

PaperAI gains nothing from DraftMyVan continuing to grow inside it.
The next slice (UE5 importer? Blender export procedure follow-up?
A Unity reference port?) would be the first time the two projects'
constraints actively conflict — when DraftMyVan wants its own
release cadence, its own LICENSE, its own contributors, its own
issue tracker.

## PRs that built this — what each added

Merged into `main`:

| PR | Title | What it added |
|---|---|---|
| #3 | manifest schema, galley_1000 sample, validator, and CI gate | `manifest.schema.json` (Draft 2020-12, mm canonical, strict additionalProperties), `examples/galley_1000.json`, `tools/validate_manifest.py`, `tests/test_validator.py` (10 tests), `.github/workflows/draftmyvan.yml` scoped to `draftmyvan/**` |
| #4 | Blender-side manifest validator (scale-drift gate) | `tools/blender/validate_glb_against_manifest.py` (pure-Python GLB parser using accessor min/max), `tools/blender/validate_in_blender.py` (bpy variant for local authoritative checks), `tests/test_blender_manifest_contract.py` (23 → 30 tests) |
| #5 | enforce origin/anchor alignment for `floor_back_left` | `tools/blender/_anchor_contract.py` (shared enforcement), `floor_back_left` rule (`bbox_min ≈ (0,0,0)`, `bbox_max ≈ (W,D,H)`), other anchors fail loudly with `"anchor enforcement not implemented for <anchor>"`, 7 new tests |
| #6 | deterministic galley_1000 GLB fixture and generator | `tools/assets/generate_galley_fixture_glb.py` (stdlib-only deterministic GLB box from manifest), `examples/assets/galley_1000.glb` (804 bytes, pinned byte-for-byte), `tests/test_galley_fixture.py` (8 tests including byte-determinism), per-fixture explainer + assets dir README |
| #8 | runtime reference consumer for the manifest contract | `runtime/` package: `Module`/`Dimensions`/`ConsumerError` frozen dataclasses, `load_module(path)`, `python -m runtime.load_module` CLI, 18 tests. First **non-validator** consumer of the manifest. |
| #9 | package readiness report for `examples/` catalog | `runtime/package_report.py`, `PackageReport` aggregator + `scan_package()` + `format_report()`, `python -m runtime.package_report` CLI, 16 tests; structural-integrity checks (duplicate ids, duplicate resolved asset paths, empty/missing inputs) |

Open but not merged:

| PR | Status | Why it matters |
|---|---|---|
| **#7** | open as **draft** on branch `claude/draftmyvan-export-procedure` | Adds `tools/blender/EXPORT_REAL_ASSET.md` (the documented Blender export procedure for real cabinet art), `tools/blender/asset_export_checklist.md` (printable per-asset sign-off), `tools/blender/check_asset_ready.py` (one-command readiness wrapper), and `tests/test_check_asset_ready.py` (9 tests). It is the prerequisite for ever replacing the generated fixture with human-authored art. The new repository should merge or re-do this before any real GLB lands. |

## Current command suite

Full reference: `COMMANDS.md`. Headline commands:

```bash
cd draftmyvan

# Manifest validation
python tools/validate_manifest.py --all

# Generate / regenerate the test fixture
python tools/assets/generate_galley_fixture_glb.py

# Validate a GLB against its manifest (pure Python, CI-safe)
python tools/blender/validate_glb_against_manifest.py \
    --manifest examples/galley_1000.json \
    --glb examples/assets/galley_1000.glb

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
python -m tests.test_blender_manifest_contract    # 30 tests
python -m tests.test_galley_fixture               # 8 tests
python -m tests.test_runtime_consumer             # 18 tests
python -m tests.test_package_report               # 16 tests
python -m tests.test_handoff_ready                # added by this PR
```

## Current CI assumptions

- Runner: `ubuntu-latest`.
- Python: 3.11 (`actions/setup-python@v5`).
- Third-party deps: **only** `jsonschema`. Installed via
  `python -m pip install --upgrade pip jsonschema`.
- Blender is **not** installed. The `bpy` validator
  (`tools/blender/validate_in_blender.py`) is documented as a
  local-only authoritative gate.
- Trigger scope: `push` + `pull_request` on paths
  `draftmyvan/**` and `.github/workflows/draftmyvan.yml`.
  PaperAI / Flutter changes never trigger it.
- Permissions: `contents: read`. Nothing more.

When extracting, this workflow becomes `.github/workflows/ci.yml`
(or similar) at the new repository's root and the `working-directory`
prefix drops away. See `EXTRACT_TO_REAL_REPO.md`.

## Current limitations (deliberate, documented)

- **Only `floor_back_left` is enforced.** Other schema-valid anchors
  (`floor_back_right`, `floor_front_*`, `ceiling_*`, `wall_*`) fail
  loudly rather than passing silently.
- **The pure-Python GLB parser assumes identity transforms.** It reads
  POSITION-accessor `min`/`max`. For hierarchies, use the bpy variant
  (locally).
- **No collision-proxy (`UCX_…`) enforcement.** Schema requires the
  field; the validator does not yet check it inside the GLB.
- **No material-slot enforcement.** Same — declared, not yet enforced.
- **No real cabinet art.** The committed `galley_1000.glb` is the
  deterministic generated box; replacing it needs the PR #7 procedure
  to be merged (or re-done) first.
- **Catalog of one.** `examples/galley_1000.json` is the only module.
- **No UE5, Fusion 360, or CNC integration.** Every PR deferred them
  deliberately.

## What must happen before moving to Unity / UE5 / Fusion

The gates above all live before the manifest reaches a renderer or a
manufacturing tool. Before that handoff, in priority order:

1. **Merge or redo PR #7** so the export procedure is documented and
   `check_asset_ready.py` exists. Without it, the first real
   human-authored GLB has no on-ramp.
2. **Add the fixture-swap mechanism** — update
   `test_committed_fixture_matches_generator_byte_for_byte` (or make
   it conditional on a "real art committed" marker) and add per-asset
   sign-off metadata. See step 9 of `tools/blender/EXPORT_REAL_ASSET.md`
   (currently in PR #7).
3. **Add collision-proxy and material-slot enforcement** to
   `tools/blender/validate_glb_against_manifest.py`. These are the
   next things the UE5 import side will need to trust.
4. **Add anchor support beyond `floor_back_left`** as the catalog
   grows. The enforcement table is in
   `tools/blender/_anchor_contract.py:expected_corners_mm`.
5. **Decide axis-convention conversion** at the UE5 / Fusion boundary,
   not by mutating the source GLB. The contract is documented in
   `tools/blender/README.md` and `_anchor_contract.py`.

## Recommended next repo structure

In the new home, drop the `draftmyvan/` prefix — the repo itself is
DraftMyVan. Suggested layout:

```
draftmyvan/                  # new repo root (was draftmyvan/ in PaperAI)
  README.md
  HANDOFF.md                 # this file, archived as project history
  COMMANDS.md
  manifest.schema.json
  examples/
  runtime/
  tools/
  tests/
  .github/
    workflows/
      ci.yml                 # was .github/workflows/draftmyvan.yml,
                             # with `working-directory: draftmyvan` removed
                             # and path filters dropped (whole repo is in scope)
  pyproject.toml             # NEW — package metadata so `runtime/` is installable
  LICENSE                    # NEW — pick one before any external contributor PR
```

Suggested repository name: **`draftmyvan`** (lowercase, matches the
existing folder name, GitHub-idiomatic). Description: "Manifest-first
3D campervan configurator: data contract, validators, deterministic
fixtures, runtime reference consumer."

Default branch: `main`. Branch protection: require the
`Validate manifests & run tests` job to be green.

<!-- CI nudge: 2026-05-26 — re-trigger draftmyvan workflow path filter. -->
