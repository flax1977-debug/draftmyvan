# Exporting a real DraftMyVan asset (Blender → GLB)

This is the procedure a human (or a future helper script) must follow
when replacing a generated fixture under `examples/assets/`
with a real cabinet GLB. Until this procedure passes for a candidate
asset, the generated fixture stays — the generated box is the **golden
boring reference**, not a placeholder to be silently overwritten.

> **Why a procedure at all?** Every prior PR (#3–#6) was about closing
> the gap between "looks fine" and "actually buildable." Hand-exported
> GLBs are exactly where that gap reopens: wrong unit, wrong axis,
> non-applied transform, mesh origin slightly off the corner. This
> document is the checklist that keeps the existing gates honest when
> the source moves from a deterministic Python script to a person
> opening Blender.

## Hard rules

These are not preferences. A GLB that violates any of them fails the
existing validators and must not be committed.

1. **Units.** Blender object data is in **metres**. The manifest's truth
   is **millimetres**. The validator converts metres → mm; the manifest
   is never expressed in metres, and the GLB is never expressed in mm.
2. **Axes.** `+X` = width across the van, `+Y` = module depth (back is
   `+Y`), `+Z` = floor → roof. UE5 / Fusion 360 axis conversion happens
   **on import in those tools** — never by rotating, scaling, or moving
   the source Blender asset.
3. **Origin / anchor.** For `anchor = "floor_back_left"`:
   - `bbox_min` must be `(0, 0, 0)` within `--tolerance-mm` (default 1 mm).
   - `bbox_max` must equal `(width_mm, depth_mm, height_mm)` converted
     to metres.
4. **Transforms.** All object transforms must be **applied** (Object →
   Apply → All Transforms) before export. No baked-in rotations,
   scales, or translations leaking through node matrices.
5. **No post-export fix-ups.** UE5 import scale, Datasmith fudge,
   manual `matrix_world` tweaks — all forbidden. If a downstream tool
   thinks the asset is wrong, the asset is wrong. Fix the source.
6. **File path.** Exported GLB basename must equal the basename of
   `visual.glb_path` in the manifest. The committed location is
   `examples/assets/<basename>`.

## Step-by-step

### 1. Confirm the manifest

```bash
cd /path/to/draftmyvan
python tools/validate_manifest.py examples/<module>.json
```

Expected: `1/1 valid`. If the manifest is broken, fix the manifest
first — every later step depends on it.

Note the manifest's `dimensions_mm`, `anchor`, and `visual.glb_path`.
Also note `visual.material_slots` and `visual.collision_proxy`; the GLB
must declare those exact names before it is committable.

### 2. Set up the Blender scene

* Scene units: **Metric → Metres**.
* Unit scale: **1.0**.
* Length units: metres (not centimetres, not millimetres).
* Add a 1 m reference cube at the origin for sanity-checking while
  you model. Remove it before export.

### 3. Author the geometry at the correct origin

For `anchor = "floor_back_left"`:

* The rear-left-bottom corner of the cabinet's outer bounding box must
  sit at world `(0, 0, 0)`.
* The cabinet must extend into `+X` (its width), `+Y` (its depth), and
  `+Z` (its height).
* No part of the mesh may go below `Z = 0`, behind `Y = 0`, or to the
  left of `X = 0`.

### 4. Apply transforms

```
Object menu → Apply → All Transforms
```

Or with the object selected: `Ctrl + A → All Transforms`.

Confirm in the N-panel that Location is `(0, 0, 0)`, Rotation is
`(0°, 0°, 0°)`, Scale is `(1.000, 1.000, 1.000)` for every object you
intend to export.

### 5. Export to GLB

`File → Export → glTF 2.0 (.glb/.gltf)`

Recommended settings:

| setting | value |
|---|---|
| Format | **glTF Binary (.glb)** |
| Include → Limit to → Selected Objects | on (export only the module) |
| Transform → +Y Up | **off** (keep Blender's Z-up so our contract holds) |
| Geometry → Apply Modifiers | on |
| Geometry → UVs / Normals / Tangents | on if/when you have them (V1 fixture has none) |
| Compression | off (use a plain GLB until size becomes a problem) |

Save to a scratch path first (e.g. `/tmp/<module>.glb`). Do **not**
overwrite the committed fixture yet.

### 6. Run the pure-Python validator (CI gate)

```bash
cd /path/to/draftmyvan
python tools/blender/validate_glb_against_manifest.py \
    --manifest examples/<module>.json \
    --glb /tmp/<module>.glb
```

Expected last line: `RESULT: PASS`.

If it fails:

| failure | most likely cause |
|---|---|
| `bounding box exceeds tolerance` | wrong unit scale in Blender, or a part of the mesh extends beyond the declared dimensions |
| `origin/anchor alignment violates contract` | transforms not applied; cabinet not authored with back-left-bottom at origin |
| `POSITION accessor … missing min/max` | exporter wrote no accessor extents — re-export, the Blender glTF add-on normally writes them |
| `basename … != manifest` | exported filename does not match `visual.glb_path` — rename and rerun |
| `missing material slot …` | Blender material name does not match `visual.material_slots` exactly |
| `missing collision proxy …` | no node/mesh is named exactly as `visual.collision_proxy` |

### 7. (Optional) Run the bpy validator

For non-trivial scenes (multiple objects, parent hierarchies), the pure
Python path uses accessor min/max, which assumes identity transforms.
For peace of mind, run the authoritative variant inside Blender:

```bash
blender --background --python \
    tools/blender/validate_in_blender.py -- \
    --manifest examples/<module>.json \
    --glb /tmp/<module>.glb
```

The two checks should agree. If they disagree, the source has
non-applied transforms (see step 4) — fix Blender, re-export, restart.

### 8. Compare against the generated fixture

Before swapping the committed fixture for your candidate, eyeball the
size delta:

```bash
python -c "
from pathlib import Path
import sys; sys.path.insert(0, 'tools/blender')
import validate_glb_against_manifest as v
a = v.load_glb_bbox(Path('examples/assets/<module>.glb')).scaled(1000)
b = v.load_glb_bbox(Path('/tmp/<module>.glb')).scaled(1000)
print('fixture:', a.size_xyz, 'candidate:', b.size_xyz)
"
```

If the candidate's bounding box doesn't match the fixture's to the mm,
the candidate is wrong — the fixture's dimensions are derived from
the manifest, and so should the candidate's be.

### 9. Replace the current manifest asset with real art

PR #4 added the **fixture-swap mechanism** that this step depends on.
The roles of the two GLBs are now distinct:

* `examples/assets/<module>.glb` is the **current manifest asset** —
  what every downstream consumer reads through `visual.glb_path`.
* `tests/fixtures/<module>_contract_box.glb` is the **golden contract
  fixture** — a permanent regression reference, pinned byte-for-byte
  to `tools/assets/generate_galley_fixture_glb.py`'s output. It does
  **not** appear in any manifest. It does **not** get replaced by real
  art. The byte-determinism test
  (`test_golden_fixture_matches_generator_byte_for_byte`) keeps
  running forever.

The acceptance metadata at
`examples/assets/<module>.asset_acceptance.json` is the per-asset
record that captures the phase change.

To swap real art into the manifest asset slot:

1. Pass every check above (steps 1–8). Run
   `python tools/blender/check_asset_ready.py
   --manifest examples/<module>.json --glb /tmp/<module>.glb` against
   the candidate and confirm `RESULT: READY`.
2. Copy the candidate over `examples/assets/<module>.glb`.
   Do **not** touch `tests/fixtures/<module>_contract_box.glb`.
3. Edit `examples/assets/<module>.asset_acceptance.json`:
   * `generated_fixture_replaced` → `true`
   * `asset_kind` → an honest label (e.g. `"production_art"`)
   * `human_signoff.visual_reviewed` → `true`
   * `human_signoff.production_art` → `true`
   * `human_signoff.reviewer` → the human who signed off
   * `human_signoff.notes` → what changed, when, why
4. Update `tools/assets/validate_asset_acceptance.py` (and its tests)
   so the phase invariants for "no real art yet"
   (`generated_fixture_replaced` is `false`,
   `human_signoff.production_art` is `false`) are inverted for the
   real-art phase — the invariants progress with the project state.
5. The parity test
   (`test_manifest_asset_equals_golden_while_fixture_not_replaced`)
   short-circuits automatically when the flag is flipped, so real art
   with different bytes does not fail it. The golden fixture's own
   determinism test still pins
   `tests/fixtures/<module>_contract_box.glb`.
6. Run the bpy validator (`validate_in_blender.py`) and confirm it
   agrees with the pure-Python one. Both reports must be `RESULT: PASS`.

The default `python tools/assets/generate_galley_fixture_glb.py` is
safe to keep running after the swap: it always refreshes the golden
fixture, but it refuses to overwrite the manifest asset once
`generated_fixture_replaced` is `true`.

## Anti-patterns (never do this)

* **"I'll just fix the scale in UE5."** Then UE5 disagrees with Fusion,
  Fusion disagrees with the cut list, and the rebuild loop starts
  over. The contract lives in the manifest; the GLB must match it.
* **Re-exporting with `+Y Up`.** Breaks the floor_back_left contract on
  every axis simultaneously.
* **Hand-editing the GLB binary** (in a hex editor, Draco compressor,
  etc.). The fixture test fails immediately; for real assets the
  Blender source becomes a lie. Always go back to Blender.
* **Skipping "Apply All Transforms".** Bounding box looks right in the
  viewport, but the node transforms quietly displace everything at
  runtime.
* **Committing a "WIP" GLB to make CI green.** CI will be green and
  the asset will still be wrong. Always run the validators locally,
  always read the output, never commit a GLB you haven't seen pass.

## See also

* `tools/blender/README.md` — the validator's user manual.
* `tools/blender/asset_export_checklist.md` — printable
  one-pager of the steps above.
* `tools/blender/check_asset_ready.py` — one-command
  end-to-end validator wrapper.
