# Blender validation tools

This directory holds the GLB contract defence for DraftMyVan visual
assets: scale, origin, material slots, and collision proxy.

## Why this exists

A GLB that looks correct in UE5 but disagrees with `dimensions_mm` in the
manifest, sits at the wrong corner of world space, omits manifest material
slots, or lacks the declared collision proxy silently invalidates downstream
outputs: cut lists, clearance checks, placement snapping, importer material
binding, and collision setup.

Size-only validation is **insufficient**. A cabinet authored 100 mm to the
right of the origin will still be 1000 mm wide and pass a naive bbox-size
check, but every snap point and clearance computed downstream will be off
by 100 mm. Origin/anchor enforcement is what closes that gap.

These scripts answer four questions, at different levels of authority:

  1. Does the GLB's bounding box **size** match the manifest within tolerance?
  2. Are the GLB's bounding box **corners** placed where the manifest's
     declared anchor requires?
  3. Does the GLB declare every name in `visual.material_slots`?
  4. Does the GLB contain a node or mesh named exactly
     `visual.collision_proxy`?

## Authoring coordinate contract

Blender is the source of truth for visual geometry. The authoring
coordinate convention is:

| Axis | Meaning |
|---|---|
| `+X` | width — left/right across the van |
| `+Y` | depth — front/back module depth (back is the wall the module presses against) |
| `+Z` | height — floor → roof |

Units in Blender object data are **metres**; the manifest's truth is
**millimetres**. The validators convert one to the other; the manifest is
never expressed in metres.

For `anchor = "floor_back_left"` the contract is:

* `bbox_min ≈ (0, 0, 0)` mm within tolerance.
* `bbox_max ≈ (width_mm, depth_mm, height_mm)` within tolerance.

i.e. the rear-left-bottom corner of the assembled mesh sits at the world
origin and the module extends into `+X`, `+Y`, `+Z`. Pass example:

```
[OK] min.x: glb=0.000 mm    expected=0.000 mm    delta=+0.000 mm
[OK] max.x: glb=1000.000 mm  expected=1000.000 mm delta=+0.000 mm
…
RESULT: PASS
```

Fail example (cabinet shifted +100 mm in +X):

```
[FAIL] min.x: glb=100.000 mm   expected=0.000 mm    delta=+100.000 mm
[FAIL] max.x: glb=1100.000 mm  expected=1000.000 mm delta=+100.000 mm
…
RESULT: FAIL — origin/anchor alignment violates contract
```

**Downstream axis conversion is downstream's job.** UE5 is Z-up
left-handed; glTF is Y-up; Fusion 360 lives in its own document space.
Each importer is responsible for converting from the contract above into
its own conventions. The source GLB and its manifest entry are never
mutated to suit a viewer.

## Material slots and collision proxy

The manifest's `visual.material_slots` entries are enforced against the
GLB JSON chunk's `materials[].name` values. Every expected name must be
present:

```
[OK] material slot 'oak_body'
[OK] material slot 'sink_metal'
```

A missing name fails the validator:

```
[FAIL] missing material slot 'sink_metal'
```

The manifest's `visual.collision_proxy` is enforced against both GLB node
names and mesh names. The expected collision proxy must appear exactly,
for example:

```
[OK] collision proxy 'UCX_galley_1000'
```

The permanent deterministic fixture at
`tests/fixtures/galley_1000_contract_box.glb` uses placeholder material
definitions and a placeholder `UCX_galley_1000` box mesh only to prove the
contract. It is still not production art or a production collision hull.
The current manifest asset at `examples/assets/galley_1000.glb` matches
that fixture today, but future real art may replace only the manifest
asset after acceptance metadata and all validators pass.

### Supported anchors (V1)

Only `floor_back_left` is enforceable today. Every other anchor declared
in the schema fails the validator with:

```
[FAIL] anchor enforcement not implemented for '<anchor>'
```

This is deliberate: silent acceptance of an unverified anchor is more
dangerous than a noisy failure. New anchors land in
`tools/blender/_anchor_contract.py:expected_corners_mm` when they're
needed.

## Two execution modes

### 1. `validate_glb_against_manifest.py` — pure Python (CI-safe)

Reads the GLB header + JSON chunk and pulls the bounding box straight from
each POSITION accessor's `min`/`max` arrays (mandatory under glTF 2.0
§3.6.2.4). No Blender needed; runs in GitHub Actions.

```bash
python tools/blender/validate_glb_against_manifest.py \
    --manifest examples/galley_1000.json \
    --glb path/to/galley_1000.glb
```

Optional flags:

| Flag | Default | Purpose |
|---|---|---|
| `--tolerance-mm` | `1.0` | Per-axis allowed delta. |
| `--glb-units` | `meters` | Set to `millimeters` if your exporter writes mm directly. |
| `--ignore-path-mismatch` | off | Accept a GLB whose basename differs from `visual.glb_path`. |

**Assumption.** This mode assumes the module is authored at the origin
with identity node transforms — i.e. accessor min/max equals the
world-space bounding box. For complex hierarchies use the Blender mode
below.

### 2. `validate_in_blender.py` — authoritative (manual)

Runs inside Blender. Imports the GLB, walks every mesh object's
`bound_box` through its `matrix_world`, and gives the true assembled
extents. Use it when the pure-Python check disagrees with your eye, or
before promoting a new GLB.

```bash
blender --background --python \
    tools/blender/validate_in_blender.py -- \
    --manifest examples/galley_1000.json \
    --glb path/to/galley_1000.glb
```

The bare `--` is required: Blender forwards everything after it to the
script.

## Pass / fail semantics

* **PASS** — every axis is within `tolerance-mm`, every material slot is
  declared, and the collision proxy exists. Safe to commit the GLB.
* **FAIL** — at least one contract check fails. Do not commit; fix the
  exporter or the manifest, not both at once.
* **ERROR** (exit 2) — manifest malformed or GLB unreadable. The asset
  pipeline itself is broken.

## What is *not* validated here yet

* **Anchors other than `floor_back_left`.** Schema-valid but explicitly
  unsupported by the enforcer — see "Supported anchors (V1)" above.
