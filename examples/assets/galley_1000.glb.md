# galley_1000.glb — current manifest asset

The committed `galley_1000.glb` in this directory is the **current
manifest asset** for `galley_1000_sink_left_oak`. It is the file every
downstream consumer reads via `examples/galley_1000.json`'s
`visual.glb_path`.

Today, this asset is **still the deterministic generated box**. The
day real cabinet art lands, this file is replaced — but the **golden
contract fixture** at `tests/fixtures/galley_1000_contract_box.glb`
stays exactly as it is forever, so the geometric contract still has a
regression reference. See `examples/assets/README.md` for the split.

## What it is today

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

While `galley_1000.asset_acceptance.json` declares
`generated_fixture_replaced: false`, the bytes here are kept identical
to the golden contract fixture by the generator and pinned by
`test_manifest_asset_equals_golden_while_fixture_not_replaced`.

## What it is *for*

To prove the pipeline can **reject** wrong size and wrong origin
**before** any polished cabinet art exists. Specifically:

1. It satisfies every gate today — manifest validator, dimension check,
   anchor/origin check, material-slot check, and collision-proxy check.
2. It is paired with a permanent golden contract fixture
   (`tests/fixtures/galley_1000_contract_box.glb`) that pins the
   generator's output byte-for-byte. The pair is the contract.
3. It gives every later GLB (real, polished art) a working comparison
   target: "did your polished asset match the same bounding box, corner,
   material-slot names, and collision-proxy name that this asset does?"

## What it is **not** for

- It is not the visual asset shipped to UE5 yet.
- It will not appear in any product screenshot.
- It does not represent the look, joinery, or interior detailing of a
  galley cabinet.
- Its material definitions and collision proxy are placeholders that exist
  only to prove the manifest contract.
- It must not be hand-edited. If you want to change its geometry, change
  the generator (or the manifest) and regenerate.

## Regenerate

```bash
cd /path/to/draftmyvan
python tools/assets/generate_galley_fixture_glb.py
```

This rewrites **both**:

- the golden contract fixture (`tests/fixtures/galley_1000_contract_box.glb`),
- the current manifest asset (`examples/assets/galley_1000.glb`),

so long as `galley_1000.asset_acceptance.json` still declares
`generated_fixture_replaced: false`. If real art has already landed in
the manifest asset slot, the generator refuses to overwrite this file
and only refreshes the golden fixture. See
`tools/assets/generate_galley_fixture_glb.py` for the exact rules.

If the regenerated golden fixture's bytes differ from the committed
file, the test suite (`tests/test_galley_fixture.py`) will fail with a
clear diff hint.

## Replacing this asset with real cabinet art (future)

See `tools/blender/EXPORT_REAL_ASSET.md` (step 9). The short version is
in `examples/assets/README.md`: build the GLB in Blender, run
`check_asset_ready.py` against it, swap it in over this file, flip the
flags in `galley_1000.asset_acceptance.json`, and tighten the
acceptance validator. The golden fixture at
`tests/fixtures/galley_1000_contract_box.glb` is untouched.
