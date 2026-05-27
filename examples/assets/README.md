# Asset directory

This directory holds **test-fixture GLBs**, not production art.

Today's contents:

| file | what it is | how it is made |
|---|---|---|
| `galley_1000.glb` | Contract fixture for `galley_1000_sink_left_oak`: a plain 1000×520×900 mm box anchored at the floor back-left corner, with placeholder material slots and a placeholder collision proxy. See `galley_1000.glb.md`. | Generated deterministically by `tools/assets/generate_galley_fixture_glb.py` from `examples/galley_1000.json`. Pinned to that output by `tests/test_galley_fixture.py`. |

## Why fixtures live here

Real, polished GLBs cannot land before:

1. The manifest validator passes (PR #3 ✔).
2. The Blender/pure-Python scale-drift gate passes (PR #4 ✔).
3. The origin/anchor gate passes (PR #5 ✔).
4. A passing fixture exists so any later real asset can be diffed
   against a known-good geometric contract (PR #6).
5. Material-slot and collision-proxy names are enforced by the GLB
   validator (PR #3).

## Adding a new fixture

1. Add the manifest entry under `examples/`.
2. Either extend `tools/assets/generate_galley_fixture_glb.py` (e.g. add a
   default-target argument) or write a sibling script. Each generator must
   stay stdlib-only and deterministic.
3. Commit the manifest and generated GLB together.
4. Add a regression test analogous to
   `test_committed_fixture_matches_generator_byte_for_byte`.

## Replacing a fixture with real art (future)

Not yet supported. Real art requires:

- A documented Blender export procedure.
- Per-PR sign-off that the polished GLB still passes every gate.
- Fixture-swap metadata that records the committed binary is real art,
  signed off by a human, and no longer the deterministic placeholder box.
