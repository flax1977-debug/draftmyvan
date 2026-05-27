# Asset export checklist

A one-pager. The full procedure with explanations lives in
`EXPORT_REAL_ASSET.md`. Use this as a printable sign-off sheet for
every real GLB before commit.

Module: `____________________`         Anchor: `floor_back_left`

| # | Step | Done |
|---|---|---|
| 1 | Manifest validates: `python tools/validate_manifest.py examples/<module>.json` → `1/1 valid` | ☐ |
| 2 | Confirm from manifest: width=`____` mm, depth=`____` mm, height=`____` mm, `visual.glb_path`=`assets/____.glb`, material slots=`________________`, collision proxy=`UCX_____________` | ☐ |
| 3 | Blender scene → Metric → Metres, unit scale `1.000` | ☐ |
| 4 | Cabinet authored with rear-left-bottom corner at world `(0, 0, 0)`; extends into `+X`, `+Y`, `+Z` only | ☐ |
| 5 | `Object → Apply → All Transforms`; Location `(0,0,0)`, Rotation `(0°,0°,0°)`, Scale `(1,1,1)` confirmed | ☐ |
| 6 | Export → glTF Binary (`.glb`); **`+Y Up` is OFF**; Apply Modifiers ON; output basename matches `visual.glb_path` | ☐ |
| 7 | Pure-Python validator passes: `python tools/blender/validate_glb_against_manifest.py --manifest … --glb /tmp/<module>.glb` → `RESULT: PASS` | ☐ |
| 8 | (Optional) bpy validator agrees: `blender --background --python tools/blender/validate_in_blender.py -- --manifest … --glb /tmp/<module>.glb` → `RESULT: PASS` | ☐ |
| 9 | Validator output includes `[OK] material slot …` for every manifest slot and `[OK] collision proxy …` for the expected proxy | ☐ |
| 10 | Bounding box equals the generated fixture's to the mm (step 8 in `EXPORT_REAL_ASSET.md`) | ☐ |
| 11 | `check_asset_ready.py --manifest … --glb /tmp/<module>.glb` → `RESULT: READY` | ☐ |
| 12 | **Do not** hand-edit the GLB binary; **do not** rely on a downstream tool to "fix" scale or axis | ☐ |
| 13 | For a future real-art swap: keep `tests/fixtures/galley_1000_contract_box.glb`, replace only `examples/assets/<module>.glb`, update acceptance metadata, and run `python tools/assets/validate_asset_acceptance.py` | ☐ |

If any row is unchecked, the GLB does not ship.
