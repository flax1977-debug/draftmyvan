# DraftMyVan — Foundation

> **This folder is not part of the PaperAI Flutter app.** It shares the repository for
> persistence convenience only. The Flutter project lives under `lib/`; DraftMyVan
> lives entirely under `draftmyvan/` and has no build coupling to it.

DraftMyVan is a manufacturing-oriented 3D campervan configurator. This directory
holds the **data contract** — the single source of truth that UE5 (visualisation),
Blender (asset factory), and Fusion 360 (manufacturing brain) will all read from.

Nothing else. No UE5, no Blender, no Fusion, no UI, no CNC post processors yet.

## Layout

```
draftmyvan/
  manifest.schema.json     # JSON Schema (Draft 2020-12) for a module
  examples/
    galley_1000.json       # First module: 1000 mm galley cabinet
  tools/
    validate_manifest.py   # CLI validator
  tests/
    test_validator.py      # Schema + sample + negative tests
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
cd draftmyvan
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
cd draftmyvan
python -m tests.test_validator                    # schema + manifest
python -m tests.test_blender_manifest_contract    # Blender gate, anchor enforcement
python -m tests.test_galley_fixture               # committed fixture + generator determinism
python -m tests.test_runtime_consumer             # manifest read as typed runtime data
python -m tests.test_package_report               # catalog/package readiness
```

Each suite prints `N/N passed` on success. None of them require Blender —
the fixture suite uses a pure-Python GLB generator
(`tools/assets/generate_galley_fixture_glb.py`) and pins the committed
`examples/assets/galley_1000.glb` to that generator's output byte-for-byte.

## Runtime consumer (reference implementation)

`draftmyvan/runtime/` is the **reference consumer** of a module manifest.
It is deliberately distinct from `tools/`: the tools directory holds
**gates** (schema validator, GLB validator) that run before code is
committed; `runtime/` is what something downstream — an editor
importer, a build script, an actual app — calls to **read** an
already-validated manifest into typed in-memory data.

```bash
cd draftmyvan
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
**other than a validator** — a Unity / UE5 / Flutter importer in a
different language would implement the same shape (`Module`,
`Dimensions`, `load_module`).

## Package readiness report

`runtime.package_report` is the catalog-level version of the consumer:
"can a build / release pipeline ingest the whole `examples/` folder as
a package?" It walks every `*.json` in a directory, loads each into a
typed `Module`, and reports the aggregate state plus structural-
integrity checks (duplicate ids, duplicate resolved asset paths).

```bash
cd draftmyvan
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
asset scale drift, **and** the closely related risk of origin drift (right
size, wrong position). See `tools/blender/README.md` for the full
description; the short version is below.

**Why it exists.** A GLB that looks correct in UE5 but whose bounding box
disagrees with `dimensions_mm` — or whose declared anchor corner is not
where the contract requires it — silently invalidates every cut list,
clearance check, and placement rule downstream. We refuse to commit any
GLB until it has passed this gate.

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
      draftmyvan/tools/blender/validate_in_blender.py -- \
      --manifest draftmyvan/examples/galley_1000.json \
      --glb path/to/galley_1000.glb
  ```

**Pass / fail.** Exit 0 = every axis within tolerance (`--tolerance-mm`,
default 1 mm). Exit 1 = drift. Exit 2 = malformed manifest or unreadable
GLB. The asset is not committable until the exit code is 0.

## CI

`.github/workflows/draftmyvan.yml` runs the manifest validator (`--all`) and
both test suites — `tests.test_validator` and
`tests.test_blender_manifest_contract` — on every push and pull request
that touches `draftmyvan/**` or the workflow file itself. It does **not**
run for changes that only touch the PaperAI Flutter app. Blender itself is
intentionally not installed in CI; the Blender mode is a local-only gate.

## What's next (not in this slice)

1. UE5 Data Asset / importer that consumes the manifest at editor time.
2. Fusion 360 add-in that regenerates a parametric template from the same entry.
3. Collision-proxy and material-slot enforcement in the GLB validator.
4. Anchor enforcement for the remaining schema-valid anchor values
   (currently only `floor_back_left` is enforced; the rest fail loudly).
