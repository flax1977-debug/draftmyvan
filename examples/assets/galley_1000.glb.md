# galley_1000.glb — current manifest asset, generated for now

The committed `galley_1000.glb` in this directory is the asset referenced by
`examples/galley_1000.json` via `visual.glb_path`. Today it is still the
generated contract box. It is not visual production art.

The permanent byte-for-byte golden fixture is now separate:

```
tests/fixtures/galley_1000_contract_box.glb
```

That test fixture stays forever as the regression reference. This file may
be replaced by real cabinet art in a future PR only after the candidate
passes every existing gate and the acceptance metadata is updated.

## What it is

A closed axis-aligned box, generated deterministically from
`examples/galley_1000.json` by `tools/assets/generate_galley_fixture_glb.py`:

| dimension | value |
|---|---|
| manifest id | `galley_1000_sink_left_oak` |
| width  | 1000 mm |
| depth  | 520 mm |
| height | 900 mm |
| anchor | `floor_back_left` (bbox-min at world origin) |
| materials | placeholder slots: `oak_body`, `sink_metal` |
| collision proxy | placeholder node/mesh: `UCX_galley_1000` |
| normals / UVs / textures | none |
| vertices / triangles | 8 / 12 |
| file size | ~1.1 KB |
| acceptance metadata | `galley_1000.asset_acceptance.json` |

## What it is *for*

To prove the pipeline can **reject** wrong size and wrong origin **before**
any polished cabinet art exists. Specifically:

1. It satisfies every gate today — manifest validator, dimension check,
   anchor/origin check, material-slot check, and collision-proxy check.
2. It validates the current manifest asset path end-to-end.
3. It is byte-identical to the permanent golden fixture while
   `generated_fixture_replaced` is `false`.
4. It gives every later GLB (real, polished art) a working comparison
   target: "did your polished asset match the same bounding box, corner,
   material-slot names, and collision-proxy name that this fixture does?"

## What it is **not** for

- It is not the visual asset shipped to UE5.
- It will not appear in any product screenshot.
- It does not represent the look, joinery, or interior detailing of a
  galley cabinet.
- Its material definitions and collision proxy are placeholders that exist
  only to prove the manifest contract.
- It must not be hand-edited. While it remains generated, change the
  generator (or the manifest) and regenerate. After real art replaces it,
  go back to the source art and re-export.

## Regenerate

```bash
cd /path/to/draftmyvan
python tools/assets/generate_galley_fixture_glb.py
# writes tests/fixtures/galley_1000_contract_box.glb

# While the manifest asset is still generated, this also refreshes it:
python tools/assets/generate_galley_fixture_glb.py \
    --out examples/assets/galley_1000.glb
```

If the regenerated golden fixture's bytes differ from the committed golden fixture,
`tests/test_galley_fixture.py` fails with a clear diff hint. If
`galley_1000.asset_acceptance.json` still says
`generated_fixture_replaced: false`, the current manifest asset must also
match the golden fixture byte-for-byte.

## Future replacement

Real art must replace only this manifest asset path:

```
examples/assets/galley_1000.glb
```

The future replacement PR must leave
`tests/fixtures/galley_1000_contract_box.glb` unchanged, run the full
readiness gate, and update `galley_1000.asset_acceptance.json` from the
current generated-fixture state to production-art sign-off. No real cabinet
art is being added in this PR.
