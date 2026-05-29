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
| Canonical runtime script (repo) | `tools/fusion/scripts/fusion_create_galley_v1/fusion_create_galley_v1.py` |
| Fusion deploy path (copy before running) | `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/fusion_create_galley_v1/fusion_create_galley_v1.py` |
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

Expected manual result (canonical runtime script): five rectangular **root
bodies** only (no per-panel components), committed into a single
`DraftMyVan Galley` BaseFeature.

Expected body names:

```text
Galley_LeftSide
Galley_RightSide
Galley_BottomPanel
Galley_TopPanel
Galley_BackPanel
```

## Observed Body Names

Record the names exactly as shown in Fusion.

| Expected root body | Observed body | Match |
| --- | --- | --- |
| `Galley_LeftSide` | `<fill in>` | `<yes/no>` |
| `Galley_RightSide` | `<fill in>` | `<yes/no>` |
| `Galley_BottomPanel` | `<fill in>` | `<yes/no>` |
| `Galley_TopPanel` | `<fill in>` | `<yes/no>` |
| `Galley_BackPanel` | `<fill in>` | `<yes/no>` |

Also confirm exactly one base feature named `DraftMyVan Galley` is present
(re-running must not accumulate empty base features).

## Pass/Fail Result

Select one:

- [ ] Pass for verification-only geometry.
- [ ] Fail.
- [ ] Inconclusive.

Pass requires all of the following:

- Exactly five rectangular panel root bodies were created.
- Body names match the expected `Galley_*` names exactly.
- Exactly one `DraftMyVan Galley` base feature owns them (no empties on rerun).
- No extra bodies were created by the script.
- Payload path was `/tmp/galley_1000_panels.json`.
- Canonical runtime script was
  `tools/fusion/scripts/fusion_create_galley_v1/fusion_create_galley_v1.py`,
  deployed to the Fusion `API/Scripts/fusion_create_galley_v1/` folder.
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
