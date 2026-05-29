# Fusion Verification Result Template

Use this template to record a future manual Fusion 360 verification run for the
DraftMyVan `galley_v1` panel geometry path.

The manual Fusion verification has not happened until this template is filled
in by the operator who ran Fusion locally.

## Warning

This verification result must not be treated as CNC, DXF, drawings, cut lists,
joinery, toolpaths, fabrication instructions, or manufacturing-ready output.

This record is for verification-only geometry.

## Run Metadata

| Field | Value |
| --- | --- |
| Date/time | `<fill in>` |
| Operator | `<fill in>` |
| Machine | `<fill in>` |
| macOS version, optional | `<fill in or n/a>` |
| Fusion 360 version | `<fill in>` |
| Repo path | `/Users/florin/draftmyvan` |
| Repo SHA | `<fill in>` |
| Git status before run | `<paste summary or attach output>` |
| Payload path | `/tmp/galley_1000_panels.json` |
| Fusion script path | `tools/fusion/fusion_create_galley_v1.py` |
| `DRAFTMYVAN_FUSION_PANEL_PAYLOAD` value | `/tmp/galley_1000_panels.json` |

## Known Dry-Run Baseline

The payload was previously validated by dry-run with this expected result:

```text
RESULT: FUSION GEOMETRY DRY RUN VALID
planned_panel_count: 5
Galley_LeftSide -> left_side_body
Galley_RightSide -> right_side_body
Galley_BottomPanel -> bottom_panel_body
Galley_TopPanel -> top_panel_body
Galley_BackPanel -> back_panel_body
```

## Fusion Run Record

| Check | Result |
| --- | --- |
| Fusion opened a blank test design | `<yes/no>` |
| Fusion opened or selected the script successfully | `<yes/no>` |
| Script run completed | `<yes/no>` |
| Fusion displayed an error message | `<yes/no; paste message below if yes>` |
| Observed component count | `<fill in>` |
| Observed body count | `<fill in>` |
| Extra geometry observed | `<yes/no>` |
| Units looked consistent with millimetre-scale geometry | `<yes/no/unclear>` |

### Fusion Messages Or Errors

```text
<paste any Fusion message or error here>
```

## Expected Result

Expected manual result: five rectangular panel bodies/components only.

Expected component/body mapping:

```text
Galley_LeftSide -> left_side_body
Galley_RightSide -> right_side_body
Galley_BottomPanel -> bottom_panel_body
Galley_TopPanel -> top_panel_body
Galley_BackPanel -> back_panel_body
```

## Observed Component And Body Names

Record the names exactly as shown in Fusion.

| Expected component | Expected body | Observed component | Observed body | Match |
| --- | --- | --- | --- | --- |
| `Galley_LeftSide` | `left_side_body` | `<fill in>` | `<fill in>` | `<yes/no>` |
| `Galley_RightSide` | `right_side_body` | `<fill in>` | `<fill in>` | `<yes/no>` |
| `Galley_BottomPanel` | `bottom_panel_body` | `<fill in>` | `<fill in>` | `<yes/no>` |
| `Galley_TopPanel` | `top_panel_body` | `<fill in>` | `<fill in>` | `<yes/no>` |
| `Galley_BackPanel` | `back_panel_body` | `<fill in>` | `<fill in>` | `<yes/no>` |

## Pass/Fail Result

Select one:

- [ ] Pass for verification-only geometry.
- [ ] Fail.
- [ ] Inconclusive.

Pass requires all of the following:

- Exactly five rectangular panel bodies/components were created.
- Component and body names match the expected mapping exactly.
- No extra bodies/components were created by the script.
- Payload path was `/tmp/galley_1000_panels.json`.
- Script path was `tools/fusion/fusion_create_galley_v1.py`.
- `DRAFTMYVAN_FUSION_PANEL_PAYLOAD` was
  `/tmp/galley_1000_panels.json`.
- No CNC, DXF, drawings, cut lists, joinery, toolpaths, fabrication
  instructions, or manufacturing-ready output were created.

## Screenshots, Optional

| View | Filename or path |
| --- | --- |
| Overview | `<fill in or n/a>` |
| Browser tree / component names | `<fill in or n/a>` |
| Body names | `<fill in or n/a>` |
| Parameters / units | `<fill in or n/a>` |
| Error message, if any | `<fill in or n/a>` |

## Notes

```text
<fill in>
```

## Follow-Up Issues

Record any follow-up work as issue titles or local notes. Do not include
fabrication instructions.

```text
<fill in or n/a>
```

## Final Statement

This record documents a manual verification attempt only. It does not approve
the geometry for manufacture and does not create CNC, DXF, drawings, cut lists,
joinery, toolpaths, fabrication instructions, or manufacturing-ready output.
