# Test fixtures

Permanent regression fixtures for the test suites. **Not** shipping
assets — these files exist only so the test suites have an immutable
reference to diff every other artifact against.

## Why this directory exists (not `examples/assets/`)

`examples/assets/` is the **manifest asset directory**: the GLB at
`examples/assets/galley_1000.glb` is what `examples/galley_1000.json`'s
`visual.glb_path` resolves to, and what every downstream consumer
(UE5 importer, package report, etc.) reads.

Today the manifest asset happens to be the deterministic generated box —
because no real cabinet art exists yet. The moment a real GLB lands, the
manifest asset stops being a generated fixture but the deterministic box
**must still exist somewhere as a regression reference** so that:

- the generator's determinism can still be tested byte-for-byte;
- the bounding-box / anchor / material-slot / collision-proxy contract
  has a known-good comparison target forever;
- a real-art regression that silently drifts dimensions is caught by a
  diff against the box, not just by validators that are themselves
  under change.

That regression reference lives **here**, deliberately outside
`examples/assets/`, so that future real art swapping into the manifest
asset path can never silently erase it.

## What lives here

| file | what it is | how it is made |
|---|---|---|
| `galley_1000_contract_box.glb` | Golden contract fixture for `examples/galley_1000.json`: the 1000×520×900 mm anchored box with the placeholder material slots and collision proxy declared by the manifest. | Generated deterministically by `tools/assets/generate_galley_fixture_glb.py`. Pinned to that output byte-for-byte by `tests/test_galley_fixture.py`. |

## Rules

- These files are **permanent**. Removing one is a contract change and
  must come with an explicit reason in the PR description.
- The bytes are pinned to the generator's output. To change the bytes,
  change the generator (or the source manifest). Hand-editing is
  forbidden — `test_committed_fixture_matches_generator_byte_for_byte`
  will fail immediately.
- They must not be referenced by any manifest as `visual.glb_path`.
  The manifest asset lives under `examples/assets/`.
