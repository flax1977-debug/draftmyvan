# Run galley_v1 geometry manually in Fusion 360

This procedure is local/manual only. CI does not install Fusion 360, does not
import Autodesk APIs, and does not create geometry.

## Prerequisites

- Autodesk Fusion 360 installed locally.
- This repository checked out.
- A validated `galley_v1` parameter payload and panel payload.
- No expectation of manufacturing-ready output.

## Generate the parameter payload

```bash
python tools/fusion/export_galley_v1_parameters.py \
    --manifest examples/galley_1000.json \
    --out build/fusion/galley_1000_fusion_parameters.json
```

## Generate the panel payload

```bash
python tools/fusion/export_galley_v1_panels.py \
    --payload build/fusion/galley_1000_fusion_parameters.json \
    --out build/fusion/galley_1000_panels.json
```

## Run the dry-run

```bash
python tools/fusion/fusion_create_galley_v1.py \
    --dry-run build/fusion/galley_1000_panels.json
```

Expected dry-run result:

```text
RESULT: FUSION GEOMETRY DRY RUN VALID
```

## Run inside Fusion 360

1. Open Fusion 360.
2. Create or open a test design.
3. Open the Scripts and Add-Ins dialog.
4. Add or run `tools/fusion/fusion_create_galley_v1.py`.
5. Provide the panel payload path as the script context if your launcher
   supports it, or set `DRAFTMYVAN_FUSION_PANEL_PAYLOAD` to the absolute panel
   payload path before launching Fusion.
6. Run the script.

Expected result: five rectangular panel components/bodies:

- `Galley_LeftSide` / `left_side_body`
- `Galley_RightSide` / `right_side_body`
- `Galley_BottomPanel` / `bottom_panel_body`
- `Galley_TopPanel` / `top_panel_body`
- `Galley_BackPanel` / `back_panel_body`

## Placement Strategy

The script uses each plan entry's `placement_origin_mm` as a first-pass
component occurrence translation:

- `bottom_panel` at the base.
- `left_side` and `right_side` at the width edges.
- `top_panel` at the top.
- `back_panel` at the rear/back plane.

These placements are deterministic but provisional. They require manual Fusion
verification before any geometry can be trusted.

## Manual Inspection

Check:

- Body and component names match the geometry plan.
- Panel count is exactly 5.
- Dimensions match the panel payload.
- Rough placement matches the plan.
- User parameters exist for `Width`, `Depth`, `Height`, and `PlyThickness`.
- No extra bodies were created.
- No CNC, drawings, DXF, or cut lists were generated.

## Screenshot Evidence

If useful, capture screenshots locally for a future evidence PR. Store proposed
paths under a local or ignored evidence folder first. Do not commit screenshots
without a separate explicit evidence PR.

## Current Limitations

- First-pass rectangular panels only.
- No joints.
- No kerf.
- No rabbets or dados.
- No edging.
- No door/drawer fronts.
- No sink cut-out.
- No hardware drilling.
- No drawings, DXF/CNC, or real cut lists.

This is not manufacturing-ready output.
