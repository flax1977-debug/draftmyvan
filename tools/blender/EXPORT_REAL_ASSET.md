# Exporting a real DraftMyVan asset (Blender → GLB)

This is the procedure a human (or a future helper script) must follow when
creating candidate GLBs and, later, replacing the current manifest asset
under `examples/assets/` with accepted real art. Until promotion passes, the
current manifest asset stays generated. The generated box under
`tests/fixtures/galley_1000_contract_box.glb` is the golden reference, not a
placeholder to be silently overwritten.

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
6. **File path.** For a production manifest asset, the exported GLB basename
   must equal the basename of `visual.glb_path` in the manifest. Candidate
   GLBs may live under `examples/assets/candidates/` with a different
   basename, but only when validated by `validate_candidate_asset.py`.

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

Save to a scratch path first (e.g. `/tmp/<module>.glb`). Do not overwrite
`examples/assets/galley_1000.glb` or anything under `tests/fixtures/` while
working on a candidate.

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

Before storing or promoting a candidate, eyeball the
size delta:

```bash
python -c "
from pathlib import Path
import sys; sys.path.insert(0, 'tools/blender')
import validate_glb_against_manifest as v
a = v.load_glb_bbox(Path('tests/fixtures/galley_1000_contract_box.glb')).scaled(1000)
b = v.load_glb_bbox(Path('/tmp/<module>.glb')).scaled(1000)
print('golden fixture:', a.size_xyz, 'candidate:', b.size_xyz)
"
```

If the candidate's bounding box doesn't match the fixture's to the mm,
the candidate is wrong — the fixture's dimensions are derived from
the manifest, and so should the candidate's be.

### 9. Store as a candidate first

Before any promotion, put the exported GLB under
`examples/assets/candidates/` and add candidate metadata:

```bash
python tools/assets/validate_candidate_asset.py \
    examples/assets/candidates/galley_1000_candidate.asset_acceptance.json
```

Candidate metadata must keep:

- `candidate_only: true`
- `production_art: false`
- `promotion_allowed: false`

The candidate validator runs the same GLB gate with manifest path mismatch
allowed for candidate storage. A passing candidate reports
`RESULT: CANDIDATE READY`. It is still not the manifest asset.

### 10. Replace only the manifest asset in a later promotion PR

The fixture-swap gate now exists, but no real art lands until a future
real-art PR. In that PR:

* Keep `tests/fixtures/galley_1000_contract_box.glb` unchanged unless the
  manifest contract itself changed.
* Replace `examples/assets/<module>.glb` with the candidate that passed
  steps 6 and 7.
* Update `examples/assets/<module>.asset_acceptance.json` from
  `asset_kind: "generated_contract_fixture"` to a real-art sign-off state:
  `generated_fixture_replaced: true`, `production_art: true`,
  `visual_reviewed: true`, and a non-null reviewer.
* Run `python tools/assets/validate_asset_acceptance.py`.
* Ensure the bpy validator agrees with the pure-Python validator before
  requesting review.

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
