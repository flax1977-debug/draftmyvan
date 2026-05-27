# DraftMyVan - Foundation

DraftMyVan is a manufacturing-oriented 3D campervan configurator. This repository
holds the **data contract** — the single source of truth that future visualization,
asset-factory, and manufacturing tooling will read from.

Nothing else. No UE5, no Fusion 360 automation, no UI, no CNC post processors
yet. Blender appears only as optional/local asset-export tooling and candidate
GLB authoring. Fusion work is currently pure-Python mapping, payload checking,
and script-skeleton dry-run only.

## Layout

```
manifest.schema.json       # JSON Schema (Draft 2020-12) for a module
examples/
  galley_1000.json         # First module: 1000 mm galley cabinet
  assets/                  # Current manifest asset, candidates, acceptance metadata
runtime/                   # Reference manifest consumer + package report
tools/
  validate_manifest.py     # CLI validator
  assets/                  # Fixture generator + asset/candidate acceptance validators
  blender/                 # GLB validators and export procedure
  fusion/                  # Pure-Python Fusion parameter mapping + script skeleton
  handoff/                 # Extraction-readiness helper
tests/                     # Pure-Python suites; no Blender required
  fixtures/                # Permanent golden contract fixtures
```

## Ground rules

- **Millimetres are canonical.** Every dimension and clearance is `*_mm` and
  stored as an integer. No cm, no inches, no floats for distances.
- **Schema-first.** A module cannot exist downstream until its manifest entry
  validates. No "we'll add the metadata later."
- **Versioned.** Every entry carries the schema version it was authored against
  (`"version": "0.1.0"` today). Bump on any breaking change.

## Required fields

`version`, `id`, `type`, `dimensions_mm`, `anchor`, `placement`, `clearances`,
`visual`, `manufacturing`, `rules`. See `manifest.schema.json` for the full
shape, allowed enum values, and constraints.

## Validate the sample

```bash
pip install jsonschema           # one-time, if not already installed
python tools/validate_manifest.py examples/galley_1000.json
# or, validate every example at once:
python tools/validate_manifest.py --all
```

Expected output:

```
OK    examples/galley_1000.json

1/1 valid
```

## Run the tests

```bash
python -m tests.test_validator                    # schema + manifest
python -m tests.test_blender_manifest_contract    # Blender gate, anchor enforcement
python -m tests.test_check_asset_ready            # real-asset readiness wrapper
python -m tests.test_galley_fixture               # golden fixture + manifest asset
python -m tests.test_asset_acceptance             # fixture-swap acceptance metadata
python -m tests.test_candidate_asset              # candidate export workflow
python -m tests.test_create_galley_candidate      # candidate generator manifest guard
python -m tests.test_candidate_review             # candidate review metadata
python -m tests.test_candidate_visual_audit       # candidate visual audit metadata
python -m tests.test_render_evidence              # local render evidence metadata
python -m tests.test_human_visual_review          # human visual review metadata
python -m tests.test_fusion_parameter_map         # Fusion parameter map dry-run
python -m tests.test_fusion_skeleton              # Fusion skeleton payload guard
python -m tests.test_runtime_consumer             # manifest read as typed runtime data
python -m tests.test_package_report               # catalog/package readiness
python -m tests.test_handoff_ready                # extraction-readiness helper
```

Each suite prints `N/N passed` on success. None of them require Blender —
the fixture suite uses a pure-Python GLB generator
(`tools/assets/generate_galley_fixture_glb.py`) and pins the permanent
golden fixture at `tests/fixtures/galley_1000_contract_box.glb` to that
generator's output byte-for-byte. The current manifest asset
`examples/assets/galley_1000.glb` still validates against the manifest;
today it matches the golden fixture, but future real art can replace only
the manifest asset without weakening the golden regression reference.

## Runtime consumer (reference implementation)

`runtime/` is the **reference consumer** of a module manifest.
It is deliberately distinct from `tools/`: the tools directory holds
**gates** (schema validator, GLB validator) that run before code is
committed; `runtime/` is what something downstream — an editor
importer, a build script, an actual app — calls to **read** an
already-validated manifest into typed in-memory data.

```bash
python -m runtime.load_module examples/galley_1000.json
```

Expected output:

```
module id:        galley_1000_sink_left_oak
type:             cabinet
dimensions:       width=1000 depth=520 height=900 (mm)
anchor:           floor_back_left
placement:        floor
glb_path:         assets/galley_1000.glb
resolved path:    .../draftmyvan/examples/assets/galley_1000.glb
asset present:    yes
RESULT: CONSUMABLE
```

Exit 0 = CONSUMABLE (manifest + GLB both present). Exit 1 = GLB
missing. Exit 2 = manifest malformed (clear error to stderr).

This package proves the manifest contract is consumable by something
**other than a validator** — a downstream importer in another language
would implement the same shape (`Module`, `Dimensions`, `load_module`).

## Package readiness report

`runtime.package_report` is the catalog-level version of the consumer:
"can a build / release pipeline ingest the whole `examples/` folder as
a package?" It walks every `*.json` in a directory, loads each into a
typed `Module`, and reports the aggregate state plus structural-
integrity checks (duplicate ids, duplicate resolved asset paths).

```bash
python -m runtime.package_report examples/
```

Expected output:

```
Scanning: examples

Found 1 manifest file(s):
  examples/galley_1000.json

Modules loaded: 1
  [OK]   galley_1000_sink_left_oak → examples/assets/galley_1000.glb (present)

Summary:
  total modules:    1
  consumable:       1
  missing assets:   0
  manifest errors:  0

RESULT: PACKAGE READY
```

Exit codes:

| code | meaning |
|---|---|
| 0 | `PACKAGE READY` — every manifest loaded; every GLB present. |
| 1 | `PACKAGE NOT READY` — manifests loaded but at least one GLB is missing. |
| 2 | `ERROR` — at least one manifest is malformed, OR duplicate ids / resolved asset paths were detected, OR the directory contains no manifests. |

Like the single-module consumer, this is **not** a re-run of the
schema or GLB validators — those gates live under `tools/` and run
before commit. The package report answers the downstream question
"given that the gates passed, is the catalog ready to ship?" It is
the input a release / build / packaging script would consume — not a
UE5 / Fusion / CNC integration.

## Blender asset validation gate

This is the defence against the architecture doc's #1 fatal risk: visual
asset scale drift, **and** the closely related risks of origin drift,
missing material slots, and missing collision proxy. See
`tools/blender/README.md` for the full description; the short version is
below.

**Why it exists.** A GLB that looks correct in UE5 but whose bounding box
disagrees with `dimensions_mm`, whose declared anchor corner is not where
the contract requires it, or whose material/proxy names do not match the
manifest silently invalidates every cut list, clearance check, placement
rule, and importer assumption downstream. We refuse to commit any GLB
until it has passed this gate.

**Authoring coordinate contract.** Blender is the source of truth.
`+X` = width across the van, `+Y` = module depth (back is `+Y`),
`+Z` = floor → roof, units = metres. For `anchor = "floor_back_left"` the
mesh's bbox-min sits at `(0, 0, 0)` and bbox-max equals
`(width, depth, height)` converted from millimetres. UE5 / Fusion axis
conversion is downstream's job and must not mutate the source GLB.

**Two execution modes.**

* `tools/blender/validate_glb_against_manifest.py` — pure Python, no
  Blender. Reads the GLB's POSITION accessor `min`/`max` arrays. Runs in
  CI and locally.

  ```bash
  python tools/blender/validate_glb_against_manifest.py \
      --manifest examples/galley_1000.json \
      --glb path/to/galley_1000.glb
  ```

* `tools/blender/validate_in_blender.py` — runs inside Blender for the
  authoritative bbox (handles non-identity transforms).

  ```bash
  blender --background --python \
      tools/blender/validate_in_blender.py -- \
      --manifest examples/galley_1000.json \
      --glb path/to/galley_1000.glb
  ```

**Pass / fail.** Exit 0 = every axis within tolerance (`--tolerance-mm`,
default 1 mm), every manifest material slot exists in the GLB, and the
declared collision proxy node/mesh exists in the GLB. Exit 1 = contract
mismatch. Exit 2 = malformed manifest or unreadable GLB. The asset is not
committable until the exit code is 0.

## Real-asset export procedure

Real cabinet art is still deferred, but the procedure and guardrails for
introducing it now live in `tools/blender/`:

- `EXPORT_REAL_ASSET.md` documents the Blender setup, units, axes,
  `floor_back_left` origin rule, transform application, export settings,
  and validator sweep.
- `asset_export_checklist.md` is the per-asset sign-off sheet.
- `check_asset_ready.py` wraps the schema, path, dimension, anchor,
  material-slot, and collision-proxy checks into one pure-Python command:

  ```bash
  python tools/blender/check_asset_ready.py \
      --manifest examples/galley_1000.json \
      --glb /tmp/candidate.glb
  ```

The committed `examples/assets/galley_1000.glb` remains the current
manifest asset. Today it is still the generated box, with placeholder
geometry, placeholder material names, and a placeholder collision proxy
only to prove the contract. The permanent generated reference lives at
`tests/fixtures/galley_1000_contract_box.glb`; it stays forever as the
byte-for-byte regression target.

`examples/assets/galley_1000.asset_acceptance.json` records the current
asset state. It says the manifest asset is still a
`generated_contract_fixture`, that no human has accepted production art,
and that the full required gate list is schema, dimensions,
`floor_back_left` anchor, material slots, and collision proxy. Validate it
with:

```bash
python tools/assets/validate_asset_acceptance.py
```

Future real art must replace only `examples/assets/galley_1000.glb`,
update the acceptance metadata to a real-art sign-off state, and still pass
all existing validators before commit.

## Candidate export workflow

The first real-export candidate lives under:

```text
examples/assets/candidates/
```

`galley_1000_candidate.glb` is now a script-generated Blender cabinet blockout,
not polished cabinet art and not the manifest asset. It proves that a
reproducible Blender export can pass the same schema, dimension,
`floor_back_left` anchor, material-slot, and collision-proxy gates while leaving both
`examples/assets/galley_1000.glb` and
`tests/fixtures/galley_1000_contract_box.glb` untouched.

Regenerate the candidate with Blender:

```bash
blender --background --python tools/blender/create_galley_candidate.py -- \
    --manifest examples/galley_1000.json \
    --out examples/assets/candidates/galley_1000_candidate.glb
```

The blockout adds visible cabinet carcass massing, front panel seams, a plinth,
countertop separation, and a simple sink marker using the existing
`oak_body` and `sink_metal` material slots. It still omits UVs, real PBR
materials, topology cleanup, joinery detail, hardware, manufacturability
review, and visual sign-off. The generator treats the manifest as source of
truth: it requires positive integer `dimensions_mm.width`, `depth`, and
`height`, and rejects strings, floats, booleans, or missing dimension fields
instead of casting them.

Validate the candidate state with:

```bash
python tools/assets/validate_candidate_asset.py \
    examples/assets/candidates/galley_1000_candidate.asset_acceptance.json
```

Candidate validation is contract compliance only. It does not accept visual
quality, topology quality, UV/material quality, manufacturability, or runtime
performance. The candidate review metadata pins the exact candidate SHA and
keeps the review non-production:

```bash
python tools/assets/validate_candidate_review.py \
    examples/assets/candidates/galley_1000_candidate_review.json
```

The visual audit is a separate SHA-pinned record of visual findings. It is not
an acceptance of production quality, and the current audit explicitly says
`not_production_ready` and `do_not_promote`:

```bash
python tools/assets/validate_candidate_visual_audit.py \
    examples/assets/candidates/galley_1000_candidate_visual_audit.json
```

Render evidence is review support. The Blender script generates the six
standard PNG views, and the current blockout has a committed evidence set
under `examples/assets/candidates/render_evidence/galley_1000_candidate/`.
These images are not product screenshots, do not imply production art, and do
not promote the candidate:

```bash
blender --background --python tools/blender/render_candidate_views.py -- \
    --candidate examples/assets/candidates/galley_1000_candidate.glb \
    --out examples/assets/candidates/render_evidence/galley_1000_candidate/

python tools/assets/validate_render_evidence.py \
    examples/assets/candidates/galley_1000_candidate_render_evidence.json
```

The committed render evidence now has a human visual review record. That
review documents what is visible in each standard view and what remains missing,
but it is not production approval and still recommends `do_not_promote`:

```bash
python tools/assets/validate_human_visual_review.py \
    examples/assets/candidates/galley_1000_candidate_human_visual_review.json
```

Lifecycle:

1. **Golden fixture** — permanent byte-for-byte regression reference under
   `tests/fixtures/`.
2. **Candidate asset** — Blender-exported candidate under
   `examples/assets/candidates/`, never referenced by the manifest.
3. **Candidate review** — SHA-pinned report and metadata saying what the
   candidate proves and what remains missing.
4. **Visual audit** — SHA-pinned visual findings and repeatable local render
   procedure; still not production sign-off.
5. **Render evidence** — local Blender script and metadata for repeatable
   view generation; the current blockout has six committed review PNGs pinned
   by path, size, and SHA.
6. **Human visual review** — view-by-view observations from the committed PNGs;
   still not production approval and still do-not-promote.
7. **Accepted manifest asset** — future PR copies an accepted candidate to
   `examples/assets/galley_1000.glb` and updates acceptance metadata.
8. **Future real art** — later quality work can improve the accepted asset,
   still behind the same gates.

## Fusion parameter dry-run and skeleton

The first Fusion-side proof is pure Python and lives under `tools/fusion/`.
It proves that manufacturing-side parameter consumption can start from the same
manifest that drives validation and visual review, and that a future Fusion
script can consume the resulting payload without making CI depend on Fusion:

```bash
python tools/fusion/validate_fusion_parameter_map.py \
    tools/fusion/galley_v1_parameter_map.json

python tools/fusion/export_galley_v1_parameters.py \
    --manifest examples/galley_1000.json \
    --out build/fusion/galley_1000_fusion_parameters.json

python tools/fusion/check_fusion_payload.py \
    tests/fixtures/galley_1000_fusion_parameters.expected.json
```

The dry-run output contains `galley_v1` parameters (`Width`, `Depth`,
`Height`, `PlyThickness`), hardware, and the explicitly ignored/deferred fields.
`tools/fusion/fusion_galley_v1_skeleton.py` can be imported in normal Python
because Autodesk `adsk` imports are guarded inside Fusion-only functions. It
validates and summarizes the payload for a later Fusion run, but it does not
create geometry yet. It does not call Fusion 360 in CI, does not generate
drawings, does not emit DXF/CNC files, and does not claim manufacturing
readiness. `build/` output is ignored by Git.

## CI

`.github/workflows/ci.yml` runs the manifest validator, the pure-Python
test suites, the static handoff check, the asset-readiness CLI, the
asset-acceptance metadata CLI, the candidate-asset metadata CLI, the
candidate-review metadata CLI, and the candidate-visual-audit metadata CLI on
every push and pull request. CI also validates render-evidence metadata,
including the six committed PNG paths, sizes, SHA256 values, 1024 x 1024
resolution, Workbench render engine, and local lighting setup. CI also validates
the human visual review metadata. Blender itself is intentionally not installed
in CI; CI validates committed evidence metadata and files, not live Blender
rendering. CI also validates the pure-Python Fusion parameter map and skeleton
payload checker without installing Fusion 360 or Autodesk dependencies. Future
candidate changes require regenerating the PNGs and re-signing render-evidence
metadata to the new candidate SHA.

## What's next (not in this slice)

1. Promotion of a reviewed candidate into `examples/assets/galley_1000.glb`,
   accepted through the metadata gate without deleting the golden contract
   fixture. This requires a future explicit promotion PR with human visual
   and manufacturability sign-off.
2. Improve this visual candidate again, or create the next Fusion proof: a
   simple parametric box/carcass inside Fusion from the validated payload,
   still without CNC, drawings, cut lists, or manufacturing-ready claims.
3. UE5 Data Asset / importer that consumes the manifest at editor time.
4. Fusion 360 add-in that regenerates a parametric template from the same entry.
5. Anchor enforcement for the remaining schema-valid anchor values
   (currently only `floor_back_left` is enforced; the rest fail loudly).
