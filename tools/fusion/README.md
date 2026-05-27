# Fusion planning

This directory is the first manufacturing-side proof for DraftMyVan. It is pure
Python and planning-only in CI: no Autodesk API dependency, no Fusion 360
install, no CNC post processors, and no DXF output.

## Purpose

The Fusion stage will eventually turn the same manifest truth used by visual
assets and runtime consumers into manufacturing artifacts. The first template is
`galley_v1`, a future parametric cabinet template for the `galley_1000`
manifest family.

## Fusion Owns Later

- Parametric cabinet template definitions.
- Cut lists derived from manifest dimensions and manufacturing metadata.
- Drawings derived from accepted manufacturing geometry.
- DXF/CNC exports after a later explicit manufacturing PR.

## Fusion Must Not Own

- Visual GLB truth. GLB assets remain under the visual pipeline and its gates.
- UE5 placement rules. Runtime placement comes from the manifest contract.
- Manifest schema truth. Fusion consumes validated manifests; it does not define
  the schema.

## Current Slices

`galley_v1_parameter_map.json` declares how manifest fields map to Fusion-style
parameters, and `export_galley_v1_parameters.py` writes a deterministic JSON
dry-run payload.

`fusion_galley_v1_skeleton.py` is the first Fusion script/add-in skeleton. It
can be imported and tested in normal Python because Autodesk `adsk` imports are
guarded inside the future Fusion message path. The skeleton reads the dry-run
payload, validates the required galley parameters, and produces a summary for a
future Fusion run. It does not create geometry yet.

`check_fusion_payload.py` is the CI-safe wrapper for that skeleton. It validates
payload JSON and prints the same summary without launching Fusion.

`compute_galley_panels.py` turns a validated `galley_v1` payload into
deterministic simple carcass panel math. The current panel assumptions are:

- Side panels are `Height x Depth x PlyThickness`.
- Top and bottom panels fit between the side panels:
  `(Width - 2 * PlyThickness) x Depth`.
- Back panel fits between side panels and between top/bottom panels:
  `(Width - 2 * PlyThickness) x (Height - 2 * PlyThickness)`.
- No kerf, rabbets, dados, edging, door/drawer fronts, sink cut-out, or
  hardware drilling.

`export_galley_v1_panels.py` writes that panel breakdown as JSON and prints a
summary. This is not a real cut list yet.

`fusion_create_galley_v1.py` consumes that panel payload and produces a
deterministic Fusion geometry plan. Normal Python can import it without
Autodesk installed; `adsk` imports stay inside Fusion-only message helpers. The
plan is not geometry execution. It records the future component/body names,
sketch plane, extrude axis, extrusion distance, and provisional placement origin
for every panel, all with `planned_not_executed` status.

`check_fusion_geometry_plan.py` is the CI-safe wrapper for that plan:

```bash
python tools/fusion/check_fusion_geometry_plan.py \
    tests/fixtures/galley_1000_panels.expected.json

python tools/fusion/check_fusion_geometry_plan.py --verbose \
    tests/fixtures/galley_1000_panels.expected.json
```

Current five-panel carcass diagram:

```text
+---------------- top_panel ----------------+
| left_side      back_panel      right_side |
|                                          |
+-------------- bottom_panel --------------+
```

Current sequence:

```text
manifest -> parameter payload -> panel math -> geometry plan -> future Fusion geometry
```

The generated dry-run output is for review only and lives under `build/` by
default, which is ignored by Git.

## Still Deferred

- Fusion geometry creation and manual Fusion verification.
- Real cut lists, drawings, DXF, CNC, and post processors.
- Manufacturing-ready output or sign-off.

The next Fusion proof should create a simple parametric box/carcass inside
Fusion from the validated geometry plan, still without CNC or production claims.
