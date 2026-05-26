# galley_1000.glb — fixture, not art

The committed `galley_1000.glb` in this directory is a **geometric contract
fixture**. It is not visual production art.

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
| materials | none |
| normals / UVs / textures | none |
| vertices / triangles | 8 / 12 |
| file size | ~800 bytes |

## What it is *for*

To prove the pipeline can **reject** wrong size and wrong origin **before**
any polished cabinet art exists. Specifically:

1. It satisfies every gate today — manifest validator, dimension check,
   anchor/origin check.
2. It pins the generator output via a byte-for-byte determinism test.
3. It gives every later GLB (real, polished art) a working comparison
   target: "did your polished asset match the same bounding box and
   corner that this fixture does?"

## What it is **not** for

- It is not the visual asset shipped to UE5.
- It will not appear in any product screenshot.
- It does not represent the look, joinery, or interior detailing of a
  galley cabinet.
- It must not be hand-edited. If you want to change its geometry, change
  the generator (or the manifest) and regenerate.

## Regenerate

```bash
cd draftmyvan
python tools/assets/generate_galley_fixture_glb.py
# (equivalent to: --manifest examples/galley_1000.json --out examples/assets/galley_1000.glb)
```

If the regenerated file's bytes differ from the committed file, the
test suite (`tests/test_galley_fixture.py`) will fail with a clear
diff hint.
