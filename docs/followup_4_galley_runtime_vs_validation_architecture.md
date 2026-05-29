# Follow-up #4: Galley Runtime vs Validation Architecture

Planning-only design note. No code is changed by this document. It records the
options for resolving follow-up #4 (two divergent galley implementations) so a
future, separately-authorized task can act on a clear decision.

Status at time of writing (2026-05-29): Fusion galley runtime verification is
PASSED; follow-up #4 is OPEN and not implemented.

## Current State

There are two galley-related implementations in `tools/fusion/`.

### 1. Runtime Fusion script (verified)

Path: `tools/fusion/scripts/fusion_create_galley_v1/fusion_create_galley_v1.py`

- Runtime-verified inside Fusion 360 on 2026-05-29 (ran twice in one design;
  idempotent; no duplicate bodies; no empty base-feature pile-up; dimensions
  dialog shown).
- Self-contained: imports `adsk.core` / `adsk.fusion` at module top level, so
  it is NOT importable in CI. It is meant to be deployed into Fusion's
  `API/Scripts/fusion_create_galley_v1/` folder and run there.
- Strategy: `TemporaryBRepManager.createBox(...)` →
  `root.bRepBodies.add(temp_body, base_feat)`.
- Creates one `DraftMyVan Galley` BaseFeature (`startEdit` / `finishEdit`) that
  owns five ROOT bodies:
  - `Galley_LeftSide`
  - `Galley_RightSide`
  - `Galley_BottomPanel`
  - `Galley_TopPanel`
  - `Galley_BackPanel`
- `_delete_existing_galley` makes reruns idempotent (deletes prior
  `DraftMyVan Galley` base features first, then orphan `Galley_*` bodies, then
  legacy `Galley_*` component occurrences; raises a single `RuntimeError` on
  cleanup failure).
- Computes geometry from the payload using its own helpers
  (`_compute_panels_from_parameters`, `_infer_dimensions`) — it does NOT import
  the shared `compute_galley_panels` module.

### 2. Dry-run / validation module (load-bearing in CI)

Path: `tools/fusion/fusion_create_galley_v1.py`

- CI-importable outside Fusion; uses `require_fusion_modules()` to load `adsk`
  lazily, so there is no top-level `adsk` import.
- Canonical role: dry-run / geometry-plan VALIDATION. Public API used by
  tooling/tests includes: `load_panel_payload`, `validate_panel_payload`,
  `fusion_geometry_plan`, `validate_geometry_plan`, `geometry_plan_summary`,
  `dry_run`, `main` (`--dry-run`), `is_running_in_fusion`,
  `require_fusion_modules`, `FUSION_UNAVAILABLE`, `FusionGeometryPlanError`.
- Also contains a Fusion execution path (`run(context)` →
  `create_galley_carcass_from_panels` → `create_panel_body` →
  `ensure_component` + `sketches`/`extrudeFeatures`) using the older
  convention: per-panel COMPONENTS named `Galley_*` each containing a body named
  `*_body` (e.g. `left_side_body`).
- Sources panel math from the shared `compute_galley_panels` module.

### Consumers / coupling (confirmed)

- Tests importing the module as `geometry`: `test_fusion_geometry_plan`,
  `test_fusion_geometry_execution_skeleton`, `test_fusion_local_availability`,
  `test_handoff_ready`.
- `test_no_top_level_adsk_import_exists` AST-asserts the module has no
  top-level `adsk` import. `test_handoff_ready` asserts the module path exists.
- Tools referencing the module: `tools/fusion/check_fusion_geometry_plan.py`,
  `tools/fusion/diagnostic_panel_schedule.py`,
  `tools/fusion/fusion_command_bridge.py`,
  `tools/mcp/fusion_bridge_server.py`,
  `tools/handoff/check_handoff_ready.py`.
- Crucial finding: the module's sketch/extrude EXECUTION path
  (`run`/`create_galley_carcass_from_panels`/`create_panel_body`) has NO runtime
  caller. `fusion_command_bridge` only reads status, the MCP server only calls
  `dry_run`, and the bridge already expects the verified root-body structure
  (`EXPECTED_ROOT_BODIES` + `EXPECTED_BASE_FEATURE_NAME`, with
  `LEGACY_EXPECTED_COMPONENT_BODIES` kept for recognition only). So only ONE
  geometry strategy (the BRep runtime) is ever executed; the module's
  sketch/extrude path is effectively an unverified, unreachable skeleton kept
  alive to satisfy `test_fusion_geometry_execution_skeleton` callable / fails-
  clearly asserts.

## Constraints

- The runtime script is Fusion-verified and must not be casually rewritten; any
  change to it requires fresh in-Fusion verification (run twice, idempotent).
- The validation module must remain importable outside Fusion.
- The validation module must not gain top-level `adsk` imports
  (`test_no_top_level_adsk_import_exists` enforces this).
- Existing tests and tools depend on the validation module's API and path; they
  cannot be broken without coordinated updates.
- Runtime truth of record is five ROOT bodies named `Galley_*` owned by a
  `DraftMyVan Galley` base feature.
- Dry-run / validation truth may still use planning structures
  (component / `*_body` / placement plan), but those must NOT be described
  anywhere as the current Fusion runtime output — only as dry-run / plan output.

## Option A: Unify Implementations

Converge on a single canonical geometry strategy + naming.

What unification would mean: there is one source of truth for galley geometry,
so the dry-run plan and the actual Fusion bodies describe the same structure and
names (root `Galley_*` bodies under a `DraftMyVan Galley` base feature).

Which direction is safer — two sub-directions:

- A1 (safer): the **runtime script consumes shared planning logic**. Keep the
  verified BRep/BaseFeature/root-body runtime exactly as-is for body creation,
  but have it (and the module) both derive panel dimensions/placement from the
  shared `compute_galley_panels` (the module already does; the runtime script
  currently reimplements its own math). This unifies the *inputs* without
  touching verified output behavior.
- A2 (riskier): the **validation module adopts BRep/BaseFeature runtime
  conventions** — i.e. rewrite the module's `run()`/`create_*` execution path to
  produce root `Galley_*` bodies via a base feature. This changes a load-bearing
  CI module and the test expectations for its execution path, with no runtime
  payoff (that path is never executed by any sanctioned entry point).

Required code changes:
- A1: factor the runtime script's panel math onto `compute_galley_panels`
  (after verifying the shared math yields identical dimensions); no change to
  body-creation calls.
- A2: rewrite `create_panel_body` / `create_galley_carcass_from_panels` /
  `run` in the module to the BRep/root-body approach; reconcile naming to
  `Galley_*` root bodies.

Required test changes:
- A1: add/adjust a test asserting the runtime script and module agree on the
  derived panel set/dimensions; existing tests unaffected.
- A2: rewrite `test_fusion_geometry_execution_skeleton` expectations
  (component/`*_body` asserts → root-body), keep `test_no_top_level_adsk_import`
  green, update any plan-shape assertions.

Fusion runtime re-verification needed:
- A1: low — runtime body creation unchanged, but re-verify once to confirm the
  shared-math swap produces identical geometry.
- A2: high — the module would gain a new (currently unverified) Fusion path
  that must be run twice in Fusion if it is ever intended to execute.

Risks:
- A2 touches CI-tested, load-bearing code for a path nothing runs — high cost,
  low/no benefit, real chance of breaking the 4 importing tests or the
  no-top-level-`adsk` rule.
- A1 is contained but still requires confirming the shared math exactly matches
  the runtime script's current numbers (otherwise verified geometry drifts).

## Option B: Keep Both With Explicit Boundaries

Runtime script remains the Fusion generator; the validation module remains the
dry-run / planning validator. This is the status quo after PR #22, now made
explicit.

Boundaries docs/tests should enforce:
- Docs already state the runtime-vs-planning split (`current_status.md`,
  `tools/fusion/README.md`, both file headers). Keep "current runtime output =
  root `Galley_*`" and "module `*_body`/component = dry-run/plan only".
- The bridge already checks the verified root-body structure; keep
  `LEGACY_EXPECTED_COMPONENT_BODIES` clearly labelled legacy.

Drift checks that should exist:
- A test asserting the runtime script's `BODY_DISPLAY_NAMES` and the bridge's
  `EXPECTED_ROOT_BODIES` list the same five `Galley_*` names (single source of
  truth for the verified body names). (Note: the runtime script is not
  CI-importable, so this would compare via a small shared constant or a parsed
  literal, not by importing the runtime module.)
- Keep `test_no_top_level_adsk_import_exists` and the module API asserts.
- Optionally, a doc-lint/grep test that fails if a `*_body` mapping appears
  without a nearby "dry-run" / "legacy" / "plan" qualifier.

Risks:
- Ongoing duplication: two places encode the five-panel galley; they can drift
  if the drift checks above are not added.
- The module retains an unreachable, unverified Fusion execution path that a
  newcomer could mistake for the canonical generator (mitigated by the existing
  `run()` boundary note).

Acceptable long-term? Yes, conditionally — acceptable as the stable resting
state provided the drift checks are added and the module's dead execution path
is either kept clearly marked (current) or reduced (Option C). Without drift
checks it is acceptable short-term but fragile.

## Option C: Retire Or Reduce One Implementation

Reduce the **validation module's Fusion execution path** (not the verified
runtime script, and not the module's validation API).

Which implementation could be reduced: the module's `run()` /
`create_galley_carcass_from_panels` / `create_panel_body` / `ensure_component`
sketch-extrude bodies — they are unreachable at runtime and unverified. Replace
their bodies with a clear `NotImplementedError` / `FusionGeometryPlanError`
("use the canonical runtime script") while keeping the symbols callable so tests
still pass, OR keep them but explicitly documented as a non-canonical
reference-only path.

What would change:
- Tests: `test_fusion_geometry_execution_skeleton` currently asserts these
  functions exist and fail clearly *outside* Fusion. If reduced to raise
  always, update those asserts to expect the new clear error and drop any
  "would create geometry inside Fusion" expectation.
- Tools: none break (no tool calls these functions to create geometry).
- Docs: update `GALLEY_V1_PARAMETRIC_PLAN.md` and the payload contract that
  describe the component/`*_body` execution plan to mark it reference-only.

Migration steps (high level): mark/neuter the module execution path → update
the 1 affected test file → update 2 planning docs → keep validation API and
path intact.

Risks:
- Loses the documented sketch/extrude design intent unless preserved in docs
  (it may be the intended future parametric path).
- Mild churn in a load-bearing test file.
- Presumptuous if the team actually plans to build out the sketch/extrude path.

## Recommendation

**Option B (keep both with explicit boundaries) — plus the two cheap drift
guards from Option B — as the resting state, and defer Option A/C.**

Rationale: the runtime script is verified and the module is load-bearing; the
only real risk is silent drift and newcomer confusion, both of which are closed
cheaply by a body-name drift check and the existing boundary notes. Option A2 is
high-cost / no-runtime-benefit; Option A1 is a reasonable *later* tidy (share
panel math) but not urgent. Option C is attractive only once it is confirmed the
module's sketch/extrude path will never be executed; capture that as an open
question first.

## Proposed Next Steps

Small checklist for a future, separately-authorized implementation task (do NOT
perform here):

- [ ] Confirm with the owner whether the module's sketch/extrude execution path
      is ever intended to run in Fusion (decides B-vs-C long term).
- [ ] Add a CI drift test that the verified five `Galley_*` body names are
      identical across the runtime script and the bridge's `EXPECTED_ROOT_BODIES`
      (without importing the non-CI runtime module).
- [ ] (Optional, A1) Verify `compute_galley_panels` reproduces the runtime
      script's exact dimensions, then refactor the runtime script to consume it;
      re-verify once in Fusion.
- [ ] (Optional, C) If the sketch/extrude path is confirmed dead, reduce it to a
      clear error and update `test_fusion_geometry_execution_skeleton` + the two
      planning docs.
- [ ] Keep `test_no_top_level_adsk_import_exists` and the module API/path tests
      green throughout.

## Non-Goals

- No code implementation is performed in this design-note task.
- No change to the verified Fusion runtime behavior or script.
- No change to the dry-run / validation module.
- No change to the runtime verification status (remains PASSED).
- Follow-up #4 remains OPEN; this note documents options, it does not resolve
  them.
