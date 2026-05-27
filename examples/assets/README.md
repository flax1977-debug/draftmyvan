# Asset directory

This directory holds manifest asset files and their acceptance metadata.
It does not hold the permanent golden contract fixtures.

Today's contents:

| file | what it is | how it is made |
|---|---|---|
| `galley_1000.glb` | Current manifest asset for `galley_1000_sink_left_oak`: still the generated 1000x520x900 mm contract box, with placeholder material slots and a placeholder collision proxy. See `galley_1000.glb.md`. | Currently byte-identical to `tests/fixtures/galley_1000_contract_box.glb`. It must pass `tools/blender/check_asset_ready.py` as the manifest asset. |
| `galley_1000.asset_acceptance.json` | Acceptance metadata for the current manifest asset. | Validated by `tools/assets/validate_asset_acceptance.py --all` and `tests/test_asset_acceptance.py`. |

## Golden contract fixture

The permanent generated regression fixture lives at:

```
tests/fixtures/galley_1000_contract_box.glb
```

That path was chosen because the file is now a test contract, not the
runtime manifest asset. The generator default writes to `tests/fixtures/`
so future real art can replace `examples/assets/galley_1000.glb` without
removing or weakening the deterministic byte-for-byte fixture.

## Why production art is not here yet

Real, polished GLBs cannot replace the current manifest asset until:

1. The manifest validator passes (PR #3 ✔).
2. The Blender/pure-Python scale-drift gate passes (PR #4 ✔).
3. The origin/anchor gate passes (PR #5 ✔).
4. A passing fixture exists so any later real asset can be diffed
   against a known-good geometric contract (PR #6).
5. Material-slot and collision-proxy names are enforced by the GLB
   validator (PR #3).
6. Acceptance metadata records whether the manifest asset is still the
   generated fixture or has been replaced by signed-off production art.

## Adding a new fixture

1. Add the manifest entry under `examples/`.
2. Either extend `tools/assets/generate_galley_fixture_glb.py` (e.g. add a
   default-target argument) or write a sibling script. Each generator must
   stay stdlib-only and deterministic.
3. Commit the manifest and generated GLB together.
4. Add a regression test analogous to
   `test_contract_fixture_matches_generator_byte_for_byte`.

## Replacing the manifest asset with real art (future)

Real art replaces `examples/assets/galley_1000.glb`, not the golden fixture.
The replacement PR must:

- Leave `tests/fixtures/galley_1000_contract_box.glb` unchanged.
- Run `python tools/blender/check_asset_ready.py --manifest examples/galley_1000.json --glb <candidate>`.
- Copy the passing candidate to `examples/assets/galley_1000.glb`.
- Update `galley_1000.asset_acceptance.json` for production art and human
  sign-off.
- Keep the required check list complete: schema, dimensions,
  floor_back_left_anchor, material_slots, and collision_proxy.

No real cabinet art is being added in this PR.
