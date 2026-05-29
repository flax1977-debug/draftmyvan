# DraftMyVan Current Status

This document is the current "where are we?" status for the DraftMyVan Fusion
galley verification milestone.

The manual Fusion verification has not happened yet.

## Current Repo State

Repository:

```text
/Users/florin/draftmyvan
```

Known HEAD before this status document:

```text
8ede5e93c7b839e8db4e46033c3409c941b5a3fd
```

Branch state before this status document:

```text
main pushed to origin/main through the Fusion verification result template
commit.
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
| Manual Fusion geometry creation | Pending |
| Manufacturing output | Explicitly not started |

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

## What Has Been Documented

The verification-only safety docs now cover:

- The manual Fusion run procedure.
- The panel payload contract and derived geometry-plan expectations.
- A fill-in template for recording the future manual Fusion result.

Verification docs:

- [Fusion galley verification runbook](fusion_galley_verification_runbook.md)
- [Fusion panel payload contract](fusion_panel_payload_contract.md)
- [Fusion verification result template](fusion_verification_result_template.md)

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
