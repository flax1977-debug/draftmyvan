# Codex Handoff — After Fusion Galley Setup (2026-05-29)

Handoff summary for resuming work (e.g. in Codex) after the Fusion 360 galley
runtime fix, vendoring, and verification. **No new feature work was started.**

## Status At A Glance

- Fusion runtime verification: **PASSED** (2026-05-29).
- The galley script ran **twice** inside Fusion 360 in the same test design.
- No duplicate `Galley_*` bodies after the second run.
- No empty `DraftMyVan Galley` base-feature pile-up after the second run.
- Dimensions message box appeared (both runs).
- BaseFeature fix: **runtime verified**.
- Rerun / idempotency cleanup: **runtime verified**.
- Branch `main`, working tree clean.
- 5 commits are **local only / unpushed** (see Commits). Do not push without
  explicit instruction.

## What Was Fixed

1. **Parametric BaseFeature error.** The script failed in Fusion with
   `RuntimeError: 3 : A valid targetBaseFeature is required` at
   `root.bRepBodies.add(temp_body)`. In a parametric design, transient BRep
   bodies must be committed into a `BaseFeature` that is in edit mode. Fixed by:
   - `_add_box(..., target_base_feature=None)` — calls
     `root.bRepBodies.add(temp_body, target_base_feature)` when supplied,
     otherwise the bare add (direct-mode fallback).
   - `_create_galley` creates a `"DraftMyVan Galley"` BaseFeature, calls
     `startEdit()`, adds the five bodies, and always `finishEdit()` in a
     `finally`.
   - Body names are captured while still inside the base-feature edit to avoid
     stale proxy references after `finishEdit()`.

2. **Idempotent rerun cleanup.** `_delete_existing_galley(root)` was rewritten
   to: delete old `"DraftMyVan Galley"` BaseFeatures first (prefix match,
   backwards iteration), then clean orphan `Galley_*` bodies and legacy
   `Galley_*` component occurrences, leave unrelated geometry untouched, and
   collect cleanup errors into a single `RuntimeError`. Outer `run()` still
   logs the full traceback to `/tmp/draftmyvan_fusion_last_error.txt`.

3. **Script-path drift resolved.** The working runtime script was vendored into
   the repo as the canonical runtime source (see Canonical Scripts). The
   existing `tools/fusion/fusion_create_galley_v1.py` was kept as the
   CI-importable dry-run / validation module (it could not be overwritten — a
   test forbids top-level `adsk` imports in it, and 4 tests + tooling import it).

## What Was Runtime Verified In Fusion

Operator ran the deployed script twice in the same test design on 2026-05-29:

- First run: no error dialog; dimensions message box appeared; a
  `DraftMyVan Galley` base feature was created; the five root bodies appeared:
  `Galley_LeftSide`, `Galley_RightSide`, `Galley_BottomPanel`,
  `Galley_TopPanel`, `Galley_BackPanel`.
- Second run (same design): still exactly five `Galley_*` bodies; no duplicate
  bodies; no pile-up of empty `DraftMyVan Galley` base features; dimensions
  message box still appeared; `/tmp/draftmyvan_fusion_last_error.txt` not
  needed (no runtime failure).

Observed dimensions (manifest `galley_1000_sink_left_oak`): Width 1000.0 mm,
Depth 520.0 mm, Height 900.0 mm, Ply 18.0 mm.

## Canonical Scripts

There are **two distinct, non-duplicate** galley scripts (do not confuse them):

- **Canonical Fusion runtime body-creation script** (the one verified):
  `tools/fusion/scripts/fusion_create_galley_v1/fusion_create_galley_v1.py`
  Self-contained (imports `adsk` at top level; NOT CI-importable). Creates five
  root bodies named `Galley_*` via transient BRep boxes committed into a
  `DraftMyVan Galley` BaseFeature.

- **Deployed Fusion script** (copy of the canonical runtime script; Fusion only
  runs scripts from `API/Scripts`):
  `/Users/florin/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/fusion_create_galley_v1/fusion_create_galley_v1.py`
  Currently **byte-identical** to the repo canonical script
  (sha256 `680eb3dd75e938eeedd6b280ab6fd5b447424bef006e0e60b3c87dff434efd40`).
  Deploy = copy the repo folder over this path before running in Fusion.

- **Dry-run / geometry-plan validation module** (CI-importable; used by tests
  and tooling):
  `tools/fusion/fusion_create_galley_v1.py`
  Its `run(context)` uses a DIFFERENT strategy: per-panel components +
  sketch/extrude (`Galley_*` components containing `*_body` bodies). This is the
  source of the `*_body` naming seen in dry-run output.

## Which Docs Were Updated

- `docs/current_status.md` — ladder + status flipped to runtime PASSED;
  canonical runtime-vs-planning split documented; deploy steps; live `Galley_*`
  convention.
- `docs/fusion_verification_result_2026-05-29.md` — filled run record + a
  Rerun/Idempotency record; follow-ups #1 (addressed), #2 (resolved), #3
  (implemented + runtime verified), #4 (new, open).
- `docs/fusion_galley_verification_runbook.md` — run steps point at the
  canonical/deployed path with a copy step; expected result is five `Galley_*`
  root bodies under one base feature; `*_body` noted only as backward-compat.
- `docs/fusion_verification_result_template.md` — script path + body-name
  expectations updated to the `Galley_*` root-body convention.
- `tools/fusion/README.md` — added a "two scripts, two roles" section.
- `tools/fusion/fusion_create_galley_v1.py` — docstring note clarifying its role
  (behavior unchanged).
- `tools/fusion/scripts/fusion_create_galley_v1/fusion_create_galley_v1.py` —
  new vendored canonical runtime script with a canonical/deploy header.

## Tests / Compile Checks Passed (2026-05-29)

- `python -m py_compile`: OK on all three —
  - `tools/fusion/scripts/fusion_create_galley_v1/fusion_create_galley_v1.py`
  - the deployed Fusion script
  - `tools/fusion/fusion_create_galley_v1.py`
- Repo test suite: **63/63 passed** —
  - `test_fusion_geometry_execution_skeleton` 11/11
  - `test_fusion_geometry_plan` 17/17
  - `test_fusion_local_availability` 4/4
  - `test_handoff_ready` 10/10
  - `test_fusion_skeleton` 10/10
  - `test_fusion_panel_math` 11/11
- (Tests run as `python -m tests.<name>`; pytest is not installed in this env.)

## Commits (local only — UNPUSHED)

Branch `main` is 5 commits ahead of `origin/main`, 0 behind:

```text
c54c534 docs: mark Fusion galley runtime verification passed
ebba5a5 repo: vendor canonical Fusion galley script and align docs
7a86208 docs: record galley rerun cleanup implementation (runtime pending)
0293a16 docs: record Fusion galley manual verification result
f6a1d45 docs: record diagnostic Fusion panel schedule status
```

(The handoff-doc commit is added on top of these.)

## What Remains Open

### ⚠️ Follow-up #4 — NOT STARTED, STILL OPEN

The canonical **runtime** script and the **dry-run / validation** module use
divergent geometry strategies and naming:

- runtime: transient BRep boxes -> `DraftMyVan Galley` BaseFeature -> root
  bodies named `Galley_*`.
- validation module: per-panel components + sketch/extrude -> `Galley_*`
  components containing `*_body` bodies.

This divergence is intentional for now but unresolved. A single canonical
geometry strategy should be chosen and the two unified (or one retired). **Do
not assume #4 is done.** No unification work has been done.

**Update 2026-05-29 — Option B chosen (keep both, explicit boundaries):** no
unification was performed. A code-level boundary note was added to the
validation module's `run()`, and one concrete drift bug was fixed — the Fusion
command bridge (`tools/fusion/fusion_command_bridge.py`) now checks for the
verified root-body structure (`EXPECTED_ROOT_BODIES` + a `DraftMyVan Galley`
base feature) instead of the legacy `Galley_* -> *_body` component layout
(retained as `LEGACY_EXPECTED_COMPONENT_BODIES`). Follow-up #4 remains OPEN.

## Exact Remaining TODOs

1. **Follow-up #4 (OPEN):** unify or retire one of the two galley
   implementations so runtime and validation share one geometry strategy and
   naming convention.
2. **Push decision:** 5 (soon 6) local commits on `main` are unpushed. Decide
   whether to push to `origin/main` or move them to a branch/PR.
3. **Optional hardening:** payload schema + tests, in a separate change.
4. **Optional:** a docs-only evidence/screenshot folder convention for future
   Fusion verification runs.

## Notes For Whoever Continues

- Working tree is clean; you can continue in the same tree.
- If you edit the canonical runtime script, re-deploy it (copy to the Fusion
  `API/Scripts/fusion_create_galley_v1/` path) before running in Fusion; they
  are currently identical.
- Do not push without explicit instruction from the user.
