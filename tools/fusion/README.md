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

`diagnostic_panel_schedule.py` emits a deterministic text schedule from the
validated panel payload. This is a verification aid only, not manufacturing
output:

```bash
python tools/fusion/diagnostic_panel_schedule.py \
    tests/fixtures/galley_1000_panels.expected.json
```

`fusion_create_galley_v1.py --dry-run <panel-payload>` validates the same
payload and summarizes the manual body-creation path without importing
Autodesk:

```bash
python tools/fusion/fusion_create_galley_v1.py \
    --dry-run tests/fixtures/galley_1000_panels.expected.json
```

When run manually inside Fusion 360 with a valid panel payload, this module's
guarded `run(context)` path can create the five panels via per-panel components
+ sketch/extrude. Outside Fusion, Fusion-only functions fail clearly with:

```text
Fusion 360 API unavailable; run this inside Fusion 360 or use --dry-run
```

### Two scripts, two roles (do not confuse them)

- `tools/fusion/fusion_create_galley_v1.py` (this module) is the canonical
  **dry-run / geometry-plan validation** library. It is CI-importable (no
  top-level `adsk` import) and its `run(context)` uses the component +
  sketch/extrude approach (`Galley_*` components containing `*_body` bodies).
- `tools/fusion/scripts/fusion_create_galley_v1/fusion_create_galley_v1.py` is
  the canonical **Fusion runtime body-creation** script. It is self-contained
  (imports `adsk` at top level, not CI-importable) and creates five **root
  bodies** named `Galley_*` from transient BRep boxes committed into a
  `DraftMyVan Galley` BaseFeature (required in parametric designs). This is the
  script that was actually run and verified in Fusion. Deploy it by copying the
  folder into Fusion's `API/Scripts/`; see the verification runbook.

These two use different geometry strategies and naming. Unifying or retiring
one is a tracked follow-up (see `docs/current_status.md`).

Manual execution and verification are documented in:

- `RUN_FUSION_GEOMETRY_MANUAL.md`
- `MANUAL_FUSION_GEOMETRY_CHECKLIST.md`

Current five-panel carcass diagram:

```text
+---------------- top_panel ----------------+
| left_side      back_panel      right_side |
|                                          |
+-------------- bottom_panel --------------+
```

Current sequence:

```text
manifest -> parameter payload -> panel math -> geometry plan -> manual Fusion geometry
```

The generated dry-run output is for review only and lives under `build/` by
default, which is ignored by Git.

## Still Deferred

- Manual Fusion verification evidence.
- Real cut lists, drawings, DXF, CNC, and post processors.
- Manufacturing-ready output or sign-off.

The next Fusion proof should run the manual checklist and record evidence for
the simple five-panel carcass, still without CNC or production claims.
