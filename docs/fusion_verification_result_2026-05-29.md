# Fusion Verification Result — 2026-05-29

Manual Fusion 360 verification run for the DraftMyVan `galley_v1` panel
geometry path, recorded from the result template.

## Warning

This verification result must not be treated as CNC, DXF, drawings, cut lists,
joinery, toolpaths, fabrication instructions, or manufacturing-ready output.
This record is for verification-only geometry.

## Run Metadata

| Field | Value |
| --- | --- |
| Date/time | 2026-05-29 16:56 local |
| Operator | Florin |
| Machine | macOS (Darwin 25.5.0) |
| Fusion 360 version | webdeploy build `a706025f86435b2ccd17930d01721ef22d0fd507` (Trial) |
| Repo path | `/Users/florin/draftmyvan` |
| Repo SHA | `f6a1d459393a3b57b7c1bd592b9ad6959e86ab0d` |
| Git status before run | clean |
| Payload path | `/tmp/galley_1000_panels.json` |
| Payload manifest_id | `galley_1000_sink_left_oak` |
| Canonical runtime source (repo) | `tools/fusion/scripts/fusion_create_galley_v1/fusion_create_galley_v1.py` (vendored 2026-05-29) |
| Script actually run (deployed copy) | `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/fusion_create_galley_v1/fusion_create_galley_v1.py` |
| `DRAFTMYVAN_FUSION_PANEL_PAYLOAD` value | `/tmp/galley_1000_panels.json` (default) |

## Code Fix Applied Before This Run

The first run failed with:

```text
RuntimeError: 3 : A valid targetBaseFeature is required
```

Root cause: in a parametric Fusion design, `BRepBodies.add(transient_body)`
must target a `BaseFeature` that is currently in edit mode. The script was
calling `root.bRepBodies.add(temp_body)` with no base feature.

Fix: `_add_box` now accepts an optional `target_base_feature`; `_create_galley`
creates one `BaseFeature` named "DraftMyVan Galley", calls `startEdit()`, adds
all five bodies, and `finishEdit()` in a `finally` block. Body names are
captured inside the edit to avoid stale proxies after `finishEdit()`.

## Fusion Run Record

| Check | Result |
| --- | --- |
| Fusion opened a blank test design | yes (`Untitled*` (DraftMyVan)) |
| Fusion opened or selected the script successfully | yes |
| Script run completed | yes |
| Fusion displayed an error message | no (success dialog shown) |
| Observed component count | 1 (root only; no per-panel components) |
| Observed body count | 5 |
| Extra geometry observed | no |
| Units looked consistent with millimetre-scale geometry | yes (document units `mm, g`) |

### Fusion Messages Or Errors

```text
DraftMyVan galley created.

Payload: /tmp/galley_1000_panels.json
Manifest: galley_1000_sink_left_oak

Bodies:
- Galley_LeftSide
- Galley_RightSide
- Galley_BottomPanel
- Galley_TopPanel
- Galley_BackPanel

Dimensions:
Width: 1000.0 mm
Depth: 520.0 mm
Height: 900.0 mm
Ply: 18.0 mm

Verification geometry only. No DXF, CNC, drawings, kerf, dados, edging, hardware
drilling, or manufacturing sign-off.
```

## Observed Component And Body Names

The script that ran is the self-contained replacement, which creates five
**root-level bodies** (not per-panel components) named with the `Galley_*`
convention. This differs from the older dry-run plan's expected
`<component> -> <body>` mapping.

| Expected (dry-run plan) | Observed body | Body created | Naming match |
| --- | --- | --- | --- |
| `Galley_LeftSide -> left_side_body` | `Galley_LeftSide` | yes | no (`Galley_LeftSide`, not `left_side_body`) |
| `Galley_RightSide -> right_side_body` | `Galley_RightSide` | yes | no |
| `Galley_BottomPanel -> bottom_panel_body` | `Galley_BottomPanel` | yes | no |
| `Galley_TopPanel -> top_panel_body` | `Galley_TopPanel` | yes | no |
| `Galley_BackPanel -> back_panel_body` | `Galley_BackPanel` | yes | no |

## Pass/Fail Result

- [x] Pass for verification-only geometry (with documented naming deviation).
- [ ] Fail.
- [ ] Inconclusive.

Rationale: the milestone objective — "Fusion 360 can create the expected five
rectangular panel bodies from the validated payload" — was fully met. Five
rectangular bodies were created, no extra geometry, dimensions consistent with
the payload (Width 1000, Depth 520, Height 900, Ply 18 mm), units in mm.

The strict template criterion "component and body names match the expected
mapping exactly" is **not** met, because the live self-contained replacement
script intentionally uses root bodies named `Galley_*` rather than per-panel
components containing `*_body` bodies. This is a naming/structure convention
drift between the docs and the live script, not a geometry defect. See
follow-ups.

## Follow-Up Issues

```text
1. Naming/structure drift: ADDRESSED 2026-05-29. The verification-flow docs
   (runbook, result template, current_status, and this record) now describe the
   live runtime convention: five root bodies named `Galley_*` owned by a single
   `DraftMyVan Galley` base feature. The component->body `*_body` mapping is now
   labelled as the dry-run/geometry-plan VALIDATION module's output only, not
   the runtime structure. (See follow-up 4: the two implementations still
   diverge and should be unified.)

2. Script-path drift: RESOLVED 2026-05-29. The working runtime script was
   vendored into the repo as the canonical runtime source at
   `tools/fusion/scripts/fusion_create_galley_v1/fusion_create_galley_v1.py`
   (mirrors Fusion's API/Scripts/<name>/<name>.py layout; deploy = copy the
   folder). The flat `tools/fusion/fusion_create_galley_v1.py` is kept as the
   CI-importable dry-run/geometry-plan validation module (4 tests + tooling
   depend on it; a test forbids top-level adsk imports in it, so it could not
   be overwritten). Both files carry headers explaining the split.

4. Two divergent galley implementations (NEW, OPEN): the runtime script uses
   transient BRep boxes -> BaseFeature -> root bodies (`Galley_*`); the
   validation module uses per-panel components + sketch/extrude (`Galley_*`
   components containing `*_body` bodies). They produce different structures and
   names. Decide a single canonical geometry strategy and unify or retire one.

3. Re-run timeline hygiene (parametric): IMPLEMENTED 2026-05-29 (code only,
   Fusion runtime rerun still PENDING). `_delete_existing_galley` was rewritten
   to delete old "DraftMyVan Galley" BaseFeatures first (prefix match, backwards
   iteration), then clean orphan `Galley_*` bodies and legacy `Galley_*`
   component occurrences, leaving unrelated geometry untouched, and to collect
   cleanup errors into a single RuntimeError (outer run() still logs the full
   traceback to /tmp/draftmyvan_fusion_last_error.txt). Python syntax compile
   passed. Still to verify inside Fusion 360: run the script twice in one
   design and confirm exactly five bodies (no duplicates) and a single
   "DraftMyVan Galley" base feature (no empties accumulating).
```

## Final Statement

This record documents a manual verification run only. It does not approve the
geometry for manufacture and does not create CNC, DXF, drawings, cut lists,
joinery, toolpaths, fabrication instructions, or manufacturing-ready output.
