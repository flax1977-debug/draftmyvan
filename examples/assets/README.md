# Asset directory

This directory holds **manifest-selected assets** and per-asset acceptance
metadata. It does not hold the permanent golden test fixture anymore.

Today's contents:

| file | what it is | how it is made |
|---|---|---|
| `galley_1000.glb` | Current manifest asset for `galley_1000_sink_left_oak`: still a plain 1000x520x900 mm generated box today, anchored at the floor back-left corner, with placeholder material slots and a placeholder collision proxy. See `galley_1000.glb.md`. | Currently byte-identical to `tests/fixtures/galley_1000_contract_box.glb`. It validates as the manifest asset, but is no longer the byte-pinned golden fixture. |
| `galley_1000.asset_acceptance.json` | Acceptance metadata for the current manifest asset. | Validated by `tools/assets/validate_asset_acceptance.py`. |
| `candidates/` | Candidate-only Blender exports and candidate metadata. These files are not referenced by the manifest. | Validated by `tools/assets/validate_candidate_asset.py`. |

## Where the golden fixture lives

The permanent generated regression fixture is:

```text
tests/fixtures/galley_1000_contract_box.glb
```

That file is generated deterministically by
`tools/assets/generate_galley_fixture_glb.py` from
`examples/galley_1000.json` and pinned byte-for-byte by
`tests/test_galley_fixture.py`. It stays in `tests/fixtures/` after real
art replaces `galley_1000.glb`.

This split is deliberate:

- `tests/fixtures/galley_1000_contract_box.glb` is the forever regression
  reference.
- `examples/assets/galley_1000.glb` is the asset referenced by the
  manifest and may become real art later.
- `examples/assets/candidates/galley_1000_candidate.glb` is a candidate
  export used to test the Blender workflow before any manifest asset is
  replaced.

## Candidate lifecycle

The asset lifecycle is:

```text
golden fixture -> candidate asset -> accepted manifest asset -> future real art
```

Candidates live under `examples/assets/candidates/` and must keep
`candidate_only: true`, `production_art: false`, and
`promotion_allowed: false` until a later promotion PR accepts them. A
candidate can prove the Blender export workflow and pass the full GLB gate,
but it still does not replace `examples/assets/galley_1000.glb`.

Validate the current candidate with:

```bash
python tools/assets/validate_candidate_asset.py \
    examples/assets/candidates/galley_1000_candidate.asset_acceptance.json
```

## Why real art cannot land casually

Real, polished GLBs cannot land before:

1. The manifest validator passes (PR #3 ✔).
2. The Blender/pure-Python scale-drift gate passes (PR #4 ✔).
3. The origin/anchor gate passes (PR #5 ✔).
4. A passing fixture exists so any later real asset can be diffed
   against a known-good geometric contract (PR #6).
5. Material-slot and collision-proxy names are enforced by the GLB
   validator (PR #3).
6. Acceptance metadata records whether the manifest asset is still the
   generated fixture or has become signed-off production art (PR #4).

## Adding a new fixture

1. Add the manifest entry under `examples/`.
2. Either extend `tools/assets/generate_galley_fixture_glb.py` (e.g. add a
   default-target argument) or write a sibling script. Each generator must
   stay stdlib-only and deterministic.
3. Commit the manifest and generated GLB together.
4. Add a regression test analogous to
   `test_golden_contract_fixture_matches_generator_byte_for_byte`.

## Replacing the manifest asset with real art (future)

Real art is not present in this PR. A future real-art swap must:

- Keep `tests/fixtures/galley_1000_contract_box.glb`.
- Promote a reviewed candidate by replacing only
  `examples/assets/galley_1000.glb`.
- Pass `python tools/blender/check_asset_ready.py --manifest examples/galley_1000.json`.
- Update `galley_1000.asset_acceptance.json` from
  `generated_contract_fixture` to a real-art sign-off state.
- Pass `python tools/assets/validate_asset_acceptance.py`.
