# galley_1000 candidate review

This review records what the current script-generated Blender candidate is and
what it does not prove. The candidate remains outside the manifest and is not
production art.

| Field | Value |
|---|---|
| Candidate path | `examples/assets/candidates/galley_1000_candidate.glb` |
| Manifest id | `galley_1000_sink_left_oak` |
| Validator command used | `python tools/assets/validate_candidate_asset.py examples/assets/candidates/galley_1000_candidate.asset_acceptance.json` |
| Validation result | `ready` (`RESULT: CANDIDATE READY`) |
| Candidate SHA256 | `0821e06ce68396f413447ec46e16ea5cf179c4d1c5458c59681c77f27e115ee8` |
| Golden fixture SHA256 | `db31a7317f683735ba9e487607dc53636b662077aff45e19456e6909007c5e76` |
| Comparison to golden fixture SHA | Different SHA. The candidate is distinct from the deterministic generated fixture. |
| production_art | `false` |
| promotion_ready | `false` |

## What It Proves

- A script-generated Blender GLB can live under
  `examples/assets/candidates/`.
- Candidate metadata can point at the candidate without changing the manifest.
- The candidate passes the contract gate for schema, dimensions,
  `floor_back_left` anchor, material-slot names, and collision proxy name.
- The candidate is no longer a plain cuboid: it has a blockout carcass,
  countertop distinction, front door/drawer seams, plinth, and sink marker.
- The current manifest asset and golden contract fixture remain untouched.

## What It Does Not Prove

- It does not prove production visual quality.
- It does not prove the asset is polished cabinet art.
- It does not prove UVs, real PBR materials, or texture policy.
- It does not prove topology cleanup, mesh hygiene, or real-time performance
  quality.
- It does not prove joinery detail or hardware treatment.
- It does not prove manufacturability or installation relevance.
- It does not provide human visual or manufacturing sign-off.

## Required Improvements Before Promotion

- Proper UV unwrapping.
- Real PBR materials.
- Topology cleanup.
- Joinery detail.
- Hardware.
- Manufacturability review.
- Visual sign-off.

Promotion must happen in a future explicit PR. This review does not promote
the candidate and does not replace `examples/assets/galley_1000.glb`.
