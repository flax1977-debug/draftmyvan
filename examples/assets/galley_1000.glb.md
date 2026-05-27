# galley_1000.glb — current manifest asset, not art yet

The committed `galley_1000.glb` in this directory is the asset referenced
by `examples/galley_1000.json`. Today it is still the generated contract
box. It is not visual production art.

The permanent golden fixture now lives separately at:

```text
tests/fixtures/galley_1000_contract_box.glb
```

That golden fixture stays forever as the byte-for-byte deterministic
regression reference. Future real art may replace only this manifest asset
file after acceptance metadata is updated and every validator still passes.

## What it is

A closed axis-aligned box, currently byte-identical to the golden fixture
generated from `examples/galley_1000.json` by
`tools/assets/generate_galley_fixture_glb.py`:

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

## What it is *for*

To prove the pipeline can **reject** wrong size and wrong origin **before**
any polished cabinet art exists. Specifically:

1. It satisfies every gate today — manifest validator, dimension check,
   anchor/origin check, material-slot check, and collision-proxy check.
2. It proves the manifest asset path is currently consumable.
3. It gives every later GLB (real, polished art) a working comparison
   target: "did your polished asset match the same bounding box, corner,
   material-slot names, and collision-proxy name that this fixture does?"

## What it is **not** for

- It is not the visual asset shipped to UE5.
- It will not appear in any product screenshot.
- It does not represent the look, joinery, or interior detailing of a
  galley cabinet.
- Its material definitions and collision proxy are placeholders that exist
  only to prove the manifest contract.
- It must not be hand-edited. If the asset is still accepted as a generated
  fixture, its bytes must match `tests/fixtures/galley_1000_contract_box.glb`.

## Regenerate

```bash
cd /path/to/draftmyvan
python tools/assets/generate_galley_fixture_glb.py
# writes tests/fixtures/galley_1000_contract_box.glb

# To intentionally refresh this current manifest asset while it is still generated:
python tools/assets/generate_galley_fixture_glb.py --out examples/assets/galley_1000.glb
```

If the regenerated golden fixture's bytes differ from the committed golden
fixture, `tests/test_galley_fixture.py` fails with a clear diff hint. If
`galley_1000.asset_acceptance.json` still says this manifest asset is a
generated fixture, `tests/test_asset_acceptance.py` also requires this file
to match the golden fixture bytes.
