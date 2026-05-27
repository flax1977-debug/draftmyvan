# Test fixtures

This directory holds permanent regression fixtures for tests. These files
are not package assets and are not shipped as the manifest-selected GLBs.

`galley_1000_contract_box.glb` is the golden generated box for
`examples/galley_1000.json`. It stays here even after
`examples/assets/galley_1000.glb` is replaced by future real art, so the
validator suite always has a byte-for-byte deterministic reference.
