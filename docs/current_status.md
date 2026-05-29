# DraftMyVan Current Status

This document is the current "where are we?" status for the DraftMyVan Fusion
galley verification milestone.

The manual Fusion verification PASSED on 2026-05-29: the canonical runtime
script ran twice in the same test design, creating the five `Galley_*` root
bodies with no errors, no duplicate bodies on rerun, and no pile-up of empty
`DraftMyVan Galley` base features. Both the BaseFeature fix and the
rerun/idempotency cleanup are runtime verified. See
[Fusion verification result 2026-05-29](fusion_verification_result_2026-05-29.md).
The script-path and naming follow-ups are resolved/addressed; one architectural
follow-up (#4: unify the runtime script and the validation module) remains open.

## Current Repo State

Repository:

```text
/Users/florin/draftmyvan
```

Known HEAD before this diagnostic schedule status update:

```text
8e4cace7195ecc464e4ffaf5138bd1e007d747d3
```

Branch state before this diagnostic schedule status update:

```text
main pushed to origin/main through the diagnostic Fusion panel schedule commit.
```

Working tree before this status document:

```text
clean
```

## Current Milestone

Current milestone: verification-only Fusion galley geometry.

The objective is to manually verify that Fusion 360 can create the expected
five rectangular panel bodies/components from the already validated panel
payload.

## Current Ladder

| Step | Status |
| --- | --- |
| Parameter mapping + dry-run | Done |
| Panel math/payload planning | Done |
| Fusion geometry skeleton/manual execution path | Done |
| Verification docs | Done |
| Diagnostic panel schedule | Done |
| Manual Fusion geometry creation | Done (2026-05-29, with naming follow-ups) |
| Rerun cleanup / idempotency | Runtime VERIFIED in Fusion 360 (2026-05-29, ran twice; no duplicates, no empty base-feature pile-up) |
| Manufacturing output | Explicitly not started |

## Script Fix And Rerun Cleanup (2026-05-29)

The live galley script (the self-contained replacement run from the Fusion
Scripts folder, `.../API/Scripts/fusion_create_galley_v1/fusion_create_galley_v1.py`)
received two code changes.

Completed and RUNTIME VERIFIED in Fusion 360 on 2026-05-29 (ran twice in the
same test design; Python syntax compile and repo tests also passed):

1. Fixed the parametric-mode error `RuntimeError: 3 : A valid targetBaseFeature
   is required` by creating a `"DraftMyVan Galley"` BaseFeature in
   `_create_galley`, calling `startEdit()`, passing that base feature into
   `_add_box`, and always calling `finishEdit()` in a `finally`. **Runtime
   verified:** first run produced no error and the dimensions message box, the
   `DraftMyVan Galley` base feature, and the five `Galley_*` root bodies.
2. `_add_box` now accepts an optional `target_base_feature` and calls
   `root.bRepBodies.add(temp_body, target_base_feature)` when supplied.
3. `_create_galley` creates the five galley bodies inside the base-feature edit.
4. Body names are captured while still inside the base-feature edit to avoid
   stale body proxy references after `finishEdit()`.
5. `_delete_existing_galley(root)` was rewritten so reruns are idempotent:
   deletes old `"DraftMyVan Galley"` BaseFeatures first (prefix match, so
   Fusion-renamed variants are caught), iterates Fusion collections backwards,
   then cleans remaining orphan `Galley_*` bodies and legacy `Galley_*`
   component occurrences, does not touch unrelated geometry, and collects
   cleanup errors into a single `RuntimeError`. Outer `run()` error logging to
   `/tmp/draftmyvan_fusion_last_error.txt` is left intact. **Runtime verified:**
   running the script a second time in the same design left exactly five
   `Galley_*` bodies with no duplicates and no pile-up of empty
   `DraftMyVan Galley` base features.

This resolves the earlier follow-up about leftover/empty base features
accumulating on rerun (implementation and runtime both confirmed).

Runtime verification (2026-05-29, Fusion 360) — all confirmed by the operator:

- Full runtime inside Fusion 360: PASS (no error dialog on first run).
- Ran the script twice in the same Fusion design: PASS.
- No duplicate bodies after the second run: PASS.
- No stale/empty `"DraftMyVan Galley"` base features accumulated: PASS.
- The expected five bodies appeared: `Galley_LeftSide`, `Galley_RightSide`,
  `Galley_BottomPanel`, `Galley_TopPanel`, `Galley_BackPanel`: PASS.
- The dimensions message box appeared on both runs: PASS.
- `/tmp/draftmyvan_fusion_last_error.txt` was not needed (no runtime failure).

Note: the earlier compile-only / runtime-pending caveat is now superseded by
this verified run. Syntax compile and the repo test suite also pass.

## What Has Been Validated

The payload at this path has passed the Fusion geometry dry-run:

```text
/tmp/galley_1000_panels.json
```

Known dry-run result:

```text
RESULT: FUSION GEOMETRY DRY RUN VALID
planned_panel_count: 5
Galley_LeftSide -> left_side_body
Galley_RightSide -> right_side_body
Galley_BottomPanel -> bottom_panel_body
Galley_TopPanel -> top_panel_body
Galley_BackPanel -> back_panel_body
```

This validates the Python dry-run path and planned component/body names. It
does not prove that Fusion has created bodies yet.

## Diagnostic Panel Schedule

The repo now includes a pure-Python diagnostic panel schedule generator:

```bash
python tools/fusion/diagnostic_panel_schedule.py \
    tests/fixtures/galley_1000_panels.expected.json
```

Purpose: emit a deterministic, human-readable schedule from the validated
galley panel payload so the Fusion verification path has a second text-based
check of the five planned panels and expected component/body mapping.

Warning: this is not CNC, DXF, drawing, cut-list, joinery, nesting, toolpath,
fabrication instructions, or manufacturing-ready output.

Relationship to manual Fusion verification: this diagnostic schedule checks the
same panel data before Fusion is run. It does not create or verify Fusion
bodies, and it did not replace the manual Fusion geometry step (now runtime
verified, 2026-05-29).

## What Has Been Documented

The verification-only safety docs now cover:

- The manual Fusion run procedure.
- The panel payload contract and derived geometry-plan expectations.
- A fill-in template for recording the future manual Fusion result.

Verification docs:

- [Fusion galley verification runbook](fusion_galley_verification_runbook.md)
- [Fusion panel payload contract](fusion_panel_payload_contract.md)
- [Fusion verification result template](fusion_verification_result_template.md)
- [Fusion verification result 2026-05-29 (completed run)](fusion_verification_result_2026-05-29.md)

## Canonical Scripts (runtime vs planning)

The repo now holds two distinct, non-duplicate galley scripts:

- Canonical **Fusion runtime** body-creation script (the one actually run and
  verified in Fusion):

  ```text
  tools/fusion/scripts/fusion_create_galley_v1/fusion_create_galley_v1.py
  ```

  Self-contained (imports `adsk` at top level, not CI-importable). Creates five
  **root bodies** named `Galley_*` via transient BRep boxes committed into a
  `DraftMyVan Galley` BaseFeature. Fusion only runs scripts from `API/Scripts`,
  so it must be copied/synced into the Fusion Scripts folder before running
  (unless that path is symlinked):

  ```text
  ~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/fusion_create_galley_v1/fusion_create_galley_v1.py
  ```

- Canonical **dry-run / geometry-plan validation** module (CI-importable, used
  by tests and tooling):

  ```text
  tools/fusion/fusion_create_galley_v1.py
  ```

  Its `run(context)` uses a different strategy (per-panel components +
  sketch/extrude, `Galley_*` components containing `*_body` bodies). The
  `*_body` / component mapping shown under "dry-run result" above describes
  this module, not the runtime script.

Follow-up #4 (OPEN): the two implementations use different geometry strategies
and naming and should eventually be unified or one retired. **Decision
2026-05-29: keep both with explicit boundaries for now — no unification done.**
The canonical live structure of record is the verified runtime structure: five
root bodies named `Galley_*` owned by a `DraftMyVan Galley` base feature.

As a small boundary-alignment change (not unification), the Fusion command
bridge (`tools/fusion/fusion_command_bridge.py`) status check was fixed to
expect that verified root-body structure (`EXPECTED_ROOT_BODIES` +
`EXPECTED_BASE_FEATURE_NAME`) instead of the legacy `Galley_* -> *_body`
component layout, so a correct verified-runtime design is no longer reported as
missing. The legacy mapping is retained as `LEGACY_EXPECTED_COMPONENT_BODIES`
for backward-compatible recognition only.

## What Remains Manual

The repeatable manual Fusion run (and rerun-idempotency check).

Payload path:

```text
/tmp/galley_1000_panels.json
```

Optional environment variable override:

```text
DRAFTMYVAN_FUSION_PANEL_PAYLOAD=/tmp/galley_1000_panels.json
```

Expected runtime result: five rectangular **root bodies** only, owned by a
single `DraftMyVan Galley` base feature:

```text
Galley_LeftSide
Galley_RightSide
Galley_BottomPanel
Galley_TopPanel
Galley_BackPanel
```

## Exact Next Manual Fusion Step

On the Mac with Fusion 360 installed:

1. Deploy the canonical runtime script into Fusion's Scripts folder (copy from
   `tools/fusion/scripts/fusion_create_galley_v1/fusion_create_galley_v1.py`
   to the `API/Scripts/fusion_create_galley_v1/` path shown above).
2. Optionally set `DRAFTMYVAN_FUSION_PANEL_PAYLOAD=/tmp/galley_1000_panels.json`
   (the script defaults to this path).
3. Open Fusion 360.
4. Create or open a blank test design.
5. Go to `Utilities` > `Add-Ins` > `Scripts and Add-Ins`.
6. Select the deployed `fusion_create_galley_v1.py`.
7. Run the script (run twice to confirm idempotent rerun: no duplicate bodies,
   a single `DraftMyVan Galley` base feature).
8. Record the result using
   [Fusion verification result template](fusion_verification_result_template.md).

## Exact Next Non-Manual Task Options

These tasks do not require running Fusion:

- Push this status document commit after it is created.
- Review the three verification docs for consistency after this status document
  lands.
- Track architectural follow-up #4 (unify the runtime script and the dry-run /
  geometry-plan validation module, which still diverge). Still OPEN.
- Harden the payload schema and tests in a separate future code change, if
  needed.
- Prepare a docs-only evidence folder convention for future screenshots, if
  needed.

Do not mark the manual verification complete until the Fusion run is performed
and recorded.

## Risk Notes

- Fusion has not yet proven actual body creation.
- Scale/origin drift may exist between Python panel math and Fusion bodies.
- Payload schema may still need hardening.
- Component/body naming must be confirmed inside Fusion.
- The dry-run proves payload validation and planned geometry summary only.
- Any partial Fusion result must be treated as a failed or inconclusive manual
  verification, not as success.

## Non-Goals

The current milestone explicitly does not include:

- CNC output.
- DXF files.
- Drawings.
- Cut lists.
- Joinery assumptions.
- Toolpaths.
- Manufacturing-ready output.

Do not describe any current output as manufacturing-ready.

## Recommended Next Commit After This Doc

After this status document is committed, the next recommended commit is either:

- `docs: record Fusion galley manual verification result`, after the manual
  Fusion run is completed and the result template is filled in; or
- `docs: clarify Fusion verification follow-up`, if the manual run exposes a
  docs-only ambiguity that should be captured before code changes.

Do not create a verification-result commit until the manual Fusion run has
actually happened.
