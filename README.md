# DraftMyVan - Foundation

DraftMyVan is a manufacturing-oriented 3D campervan configurator. This repository
holds the **data contract** — the single source of truth that future visualization,
asset-factory, and manufacturing tooling will read from.

Nothing else. No UE5, no Blender, no Fusion, no UI, no CNC post processors yet.

## Layout

```
manifest.schema.json       # JSON Schema (Draft 2020-12) for a module
examples/
  galley_1000.json         # First module: 1000 mm galley cabinet
  assets/                  # Current manifest asset GLB + acceptance metadata
runtime/                   # Reference manifest consumer + package report
tools/
  validate_manifest.py     # CLI validator
  assets/                  # Deterministic fixture generator + acceptance metadata validator
  blender/                 # GLB validators and export procedure
  handoff/                 # Extraction-readiness helper
tests/                     # Pure-Python suites; no Blender required
  fixtures/                # Permanent golden contract fixtures (regression reference)
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
python -m tests.test_galley_fixture               # golden fixture + manifest asset + generator determinism
python -m tests.test_runtime_consumer             # manifest read as typed runtime data
python -m tests.test_package_report               # catalog/package readiness
python -m tests.test_handoff_ready                # extraction-readiness helper
python -m tests.test_asset_acceptance             # acceptance metadata validator
```

Each suite prints `N/N passed` on success. None of them require Blender —
the fixture suite uses a pure-Python GLB generator
(`tools/assets/generate_galley_fixture_glb.py`) and pins the **golden
contract fixture** under `tests/fixtures/` to that generator's output
byte-for-byte. The **current manifest asset** at
`examples/assets/galley_1000.glb` is validated against the manifest
end-to-end; while no real cabinet art has landed it is also kept
byte-identical to the golden fixture (see the next section).

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

## Golden contract fixture vs. current manifest asset

Two GLBs participate in the contract today, each in a distinct role:

| file | role | bytes pinned? |
|---|---|---|
| `tests/fixtures/galley_1000_contract_box.glb` | **Golden contract fixture.** Permanent regression reference. Not referenced by any manifest. | Yes — pinned byte-for-byte to the generator's output by `tests/test_galley_fixture.py`. |
| `examples/assets/galley_1000.glb` | **Current manifest asset.** What `examples/galley_1000.json`'s `visual.glb_path` resolves to. Read by every downstream consumer. | Only while the acceptance metadata declares `generated_fixture_replaced: false`. After real art lands the byte-parity test short-circuits, but the asset still must validate end-to-end. |

The split exists so future real cabinet art can replace the manifest
asset without weakening the regression target. Real art changes
`examples/assets/galley_1000.glb` and flips the flag in
`examples/assets/galley_1000.asset_acceptance.json`; the golden fixture
under `tests/fixtures/` is never replaced.

The acceptance metadata for each manifest asset lives next to it:

```
examples/assets/galley_1000.glb                       # current manifest asset
examples/assets/galley_1000.asset_acceptance.json     # acceptance metadata
```

The metadata records the manifest id, asset path, asset kind, whether
the generated fixture has been replaced, the validator command, the
required-checks gate list, and a human sign-off block. It is validated
in CI by:

```bash
python tools/assets/validate_asset_acceptance.py --all
```

No real cabinet art is introduced in this PR — only the mechanism that
permits a future PR to swap it in safely. See
`tools/blender/EXPORT_REAL_ASSET.md` (step 9) and
`examples/assets/README.md` for the swap procedure.

## CI

`.github/workflows/ci.yml` runs the manifest validator, the pure-Python
test suites, the static handoff check, and the asset-readiness CLI on every
push and pull request. Blender itself is intentionally not installed in CI;
the Blender mode is a local-only authoritative gate.

## What's next (not in this slice)

1. UE5 Data Asset / importer that consumes the manifest at editor time.
2. Fusion 360 add-in that regenerates a parametric template from the same entry.
3. Anchor enforcement for the remaining schema-valid anchor values
   (currently only `floor_back_left` is enforced; the rest fail loudly).
