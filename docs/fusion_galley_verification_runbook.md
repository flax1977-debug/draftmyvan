# Fusion Galley Verification Runbook

This runbook covers the manual Fusion 360 verification step for the
DraftMyVan `galley_v1` geometry path. It is verification-only geometry: the
goal is to confirm that the validated panel payload can create the expected
five rectangular panel bodies/components inside a blank Fusion test design.

It does not create or approve manufacturing output.

## Purpose

Use this run to verify that:

- Fusion 360 can load the canonical runtime script deployed from
  `tools/fusion/scripts/fusion_create_galley_v1/fusion_create_galley_v1.py`.
- The script can read the already validated panel payload at
  `/tmp/galley_1000_panels.json`.
- The manual Fusion result contains exactly the expected five rectangular panel
  bodies/components.
- Names, count, rough placement, and basic units match the dry-run plan.

The dry-run has already validated this payload:

```text
RESULT: FUSION GEOMETRY DRY RUN VALID
planned_panel_count: 5
```

## Preconditions

- Autodesk Fusion 360 is installed locally.
- The repository is checked out at `/Users/florin/draftmyvan`.
- The dry-run baseline repository SHA before this runbook change was:

  ```text
  e515035df4ac082a65cf706093c7970d57ffa25f
  ```

- The working tree is clean before the manual run.
- The validated panel payload exists:

  ```text
  /tmp/galley_1000_panels.json
  ```

- Do not regenerate the payload for this run unless explicitly requested.
- Do not use `draftmyvan-unity`.

## macOS Environment Setup

Fusion launched from the macOS UI inherits environment variables from the user
launchd session. Set the payload path with `launchctl` before opening Fusion.

```bash
launchctl setenv DRAFTMYVAN_FUSION_PANEL_PAYLOAD /tmp/galley_1000_panels.json
launchctl getenv DRAFTMYVAN_FUSION_PANEL_PAYLOAD
```

The second command should print:

```text
/tmp/galley_1000_panels.json
```

If Fusion 360 is already open, quit it completely and reopen it after setting
the environment variable.

After the manual run, clear the variable if it is no longer needed:

```bash
launchctl unsetenv DRAFTMYVAN_FUSION_PANEL_PAYLOAD
```

## Fusion UI Steps

1. Open Fusion 360.
2. Create or open a blank test design.
3. Open the `Utilities` workspace/tab.
4. Open `Add-Ins` > `Scripts and Add-Ins`.
5. Deploy the canonical runtime script into Fusion's Scripts folder first
   (Fusion only runs scripts from `API/Scripts`, not from the repo). Copy the
   whole folder:

   ```bash
   cp "/Users/florin/draftmyvan/tools/fusion/scripts/fusion_create_galley_v1/fusion_create_galley_v1.py" \
      "/Users/florin/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/fusion_create_galley_v1/fusion_create_galley_v1.py"
   ```

6. In the `Scripts` area, add or select the deployed script:

   ```text
   ~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/fusion_create_galley_v1/fusion_create_galley_v1.py
   ```

7. Run the script.
8. Wait for the script result message.
9. Inspect the browser tree and bodies in the design.

## Expected Result

The canonical runtime script creates five rectangular **root bodies** only
(no per-panel components), committed into a single `DraftMyVan Galley`
BaseFeature:

```text
Galley_LeftSide
Galley_RightSide
Galley_BottomPanel
Galley_TopPanel
Galley_BackPanel
```

| Root body | Owned by base feature |
| --- | --- |
| `Galley_LeftSide` | `DraftMyVan Galley` |
| `Galley_RightSide` | `DraftMyVan Galley` |
| `Galley_BottomPanel` | `DraftMyVan Galley` |
| `Galley_TopPanel` | `DraftMyVan Galley` |
| `Galley_BackPanel` | `DraftMyVan Galley` |

No other bodies are expected.

Backward-compatibility note: older runs (and the dry-run/geometry-plan
validation module `tools/fusion/fusion_create_galley_v1.py`) used a
component-per-panel layout with bodies named `left_side_body` etc. The cleanup
in the runtime script still removes those legacy `Galley_*` component
occurrences, but they are not the current expected structure.

## Pass/Fail Checklist

Pass only if every item below is true:

- [ ] Fusion ran the script inside a blank test design.
- [ ] Payload path was `/tmp/galley_1000_panels.json`.
- [ ] Exactly five rectangular panel components/bodies were created.
- [ ] Component names match the expected names exactly.
- [ ] Body names match the expected names exactly.
- [ ] No extra bodies/components were created by the script.
- [ ] Overall dimensions look consistent with millimetre-scale cabinet geometry.
- [ ] User parameters are present or visible/logged for `Width`, `Depth`,
      `Height`, and `PlyThickness`.
- [ ] No CNC, DXF, drawings, cut lists, toolpaths, joinery, or fabrication
      instructions were generated.
- [ ] The result is treated as verification-only geometry.

Fail the run if any expected component/body is missing, extra geometry appears,
names differ, the payload path is wrong, units look incorrect, or Fusion reports
an error.

## Troubleshooting

### Environment Variable Missing

Symptom: Fusion opens the script, but no geometry is created and the script
reports that no panel payload path was supplied.

Check:

```bash
launchctl getenv DRAFTMYVAN_FUSION_PANEL_PAYLOAD
```

If it prints nothing, set it again:

```bash
launchctl setenv DRAFTMYVAN_FUSION_PANEL_PAYLOAD /tmp/galley_1000_panels.json
```

Quit and reopen Fusion before retrying.

### Payload File Missing

Symptom: Fusion reports that it cannot read `/tmp/galley_1000_panels.json`.

Check:

```bash
ls -la /tmp/galley_1000_panels.json
```

Stop the manual verification if the file is missing. Do not regenerate it as
part of this run unless explicitly requested.

### Invalid JSON

Symptom: Fusion reports invalid JSON or a payload validation error.

Stop the manual verification. Record the exact error message and payload path.
Do not edit the payload during this run.

### Fusion Script Not Visible

Symptom: `fusion_create_galley_v1.py` is not listed in `Scripts and Add-Ins`.

Use the add/import control in the `Scripts` area and browse to the deployed
script (copy it from the repo first, see step 5):

```text
~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/fusion_create_galley_v1/fusion_create_galley_v1.py
```

If Fusion expects a folder rather than a file, select the containing folder:

```text
/Users/florin/draftmyvan/tools/fusion
```

### No Bodies Created

Symptom: The script runs but the design remains empty.

Check that:

- The environment variable is set with `launchctl`.
- Fusion was restarted after setting the variable.
- The active design is a blank test design.
- Fusion showed no validation or Python error message.

Record the message shown by Fusion and stop the run.

### Wrong Body Count

Symptom: The browser tree shows fewer or more than five bodies/components.

Fail the run. Record the observed count, body names, component names, and any
Fusion message shown by the script.

### Wrong Names

Symptom: Five bodies/components exist, but one or more names differ from the
expected names.

Fail the run. Record the observed names exactly as shown in Fusion.

### Units Look Wrong

Symptom: Geometry appears extremely small, extremely large, or inconsistent
with millimetre-scale cabinet dimensions.

Fail the run. Record the observed dimensions if available and confirm whether
the user parameters `Width`, `Depth`, `Height`, and `PlyThickness` are present.

## Non-Goals

This run must not create, export, or approve:

- CNC output.
- DXF files.
- Drawings.
- Cut lists.
- Joinery details.
- Toolpaths.
- Fabrication instructions.
- Manufacturing-ready output.

## What to Record After the Manual Run

Record:

- Date and reviewer.
- Fusion 360 version.
- Repository path: `/Users/florin/draftmyvan`.
- Repository SHA used for the manual run.
- Dry-run baseline SHA:
  `e515035df4ac082a65cf706093c7970d57ffa25f`.
- Payload path: `/tmp/galley_1000_panels.json`.
- Whether the run passed or failed.
- Exact component and body names observed.
- Body/component count observed.
- Any Fusion messages or errors.
- Notes on unit/dimension checks.
- Optional screenshot paths for overview, browser tree, and parameters.

Do not describe the result as manufacturing-ready.
