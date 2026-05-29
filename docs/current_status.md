# DraftMyVan Current Status

This document is the current "where are we?" status for the DraftMyVan Fusion
galley verification milestone.

The manual Fusion verification was completed on 2026-05-29: the script created
five rectangular panel bodies successfully. See
[Fusion verification result 2026-05-29](fusion_verification_result_2026-05-29.md).
Two naming/path discrepancies were recorded as follow-ups (see that document).

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
| Rerun cleanup / idempotency (code) | Implemented (syntax compile only; Fusion runtime rerun pending) |
| Manufacturing output | Explicitly not started |

## Script Fix And Rerun Cleanup (2026-05-29)

The live galley script (the self-contained replacement run from the Fusion
Scripts folder, `.../API/Scripts/fusion_create_galley_v1/fusion_create_galley_v1.py`)
received two code changes.

Completed (code written, Python syntax compile passed):

1. Fixed the parametric-mode error `RuntimeError: 3 : A valid targetBaseFeature
   is required` by creating a `"DraftMyVan Galley"` BaseFeature in
   `_create_galley`, calling `startEdit()`, passing that base feature into
   `_add_box`, and always calling `finishEdit()` in a `finally`.
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
   `/tmp/draftmyvan_fusion_last_error.txt` is left intact.

This resolves the earlier follow-up about leftover/empty base features
accumulating on rerun (implementation only).

Not yet verified — pending a real run inside Fusion 360 (the `adsk.core` and
`adsk.fusion` modules exist only inside Fusion's embedded Python, so this
environment can only check syntax):

- Full runtime inside Fusion 360.
- Running the script twice in the same Fusion design.
- No duplicate bodies after the second run.
- No stale/empty `"DraftMyVan Galley"` base features accumulate.
- The expected five bodies appear: `Galley_LeftSide`, `Galley_RightSide`,
  `Galley_BottomPanel`, `Galley_TopPanel`, `Galley_BackPanel`.
- The dimensions message box still appears.
- `/tmp/draftmyvan_fusion_last_error.txt` still captures tracebacks on failure.

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
bodies, and it does not replace the pending manual Fusion geometry step.

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

## What Remains Manual

The remaining milestone step is the local manual Fusion run.

Fusion script:

```text
tools/fusion/fusion_create_galley_v1.py
```

Payload path:

```text
/tmp/galley_1000_panels.json
```

Required environment variable for the future manual run:

```text
DRAFTMYVAN_FUSION_PANEL_PAYLOAD=/tmp/galley_1000_panels.json
```

Expected manual verification result: five rectangular panel bodies/components
only.

Expected mapping:

```text
Galley_LeftSide -> left_side_body
Galley_RightSide -> right_side_body
Galley_BottomPanel -> bottom_panel_body
Galley_TopPanel -> top_panel_body
Galley_BackPanel -> back_panel_body
```

## Exact Next Manual Fusion Step

On the Mac with Fusion 360 installed:

1. Ensure `DRAFTMYVAN_FUSION_PANEL_PAYLOAD` is available to Fusion with value
   `/tmp/galley_1000_panels.json`.
2. Open Fusion 360.
3. Create or open a blank test design.
4. Go to `Utilities` > `Add-Ins` > `Scripts and Add-Ins`.
5. Select `tools/fusion/fusion_create_galley_v1.py`.
6. Run the script.
7. Record the result using
   [Fusion verification result template](fusion_verification_result_template.md).

## Exact Next Non-Manual Task Options

These tasks do not require running Fusion:

- Push this status document commit after it is created.
- Review the three verification docs for consistency after this status document
  lands.
- Add a repo issue or task note for the pending manual Fusion run.
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
