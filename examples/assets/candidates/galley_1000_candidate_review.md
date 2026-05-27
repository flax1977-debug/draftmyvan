# galley_1000 candidate review

This review records what the first Blender-authored candidate is and what it
does not prove. The candidate remains outside the manifest and is not
production art.

| Field | Value |
|---|---|
| Candidate path | `examples/assets/candidates/galley_1000_candidate.glb` |
| Manifest id | `galley_1000_sink_left_oak` |
| Validator command used | `python tools/assets/validate_candidate_asset.py examples/assets/candidates/galley_1000_candidate.asset_acceptance.json` |
| Validation result | `ready` (`RESULT: CANDIDATE READY`) |
| Candidate SHA256 | `157432f4e94f52e4975570761222ace84b804c99e2eca8b28eacca90c67984c6` |
| Golden fixture SHA256 | `db31a7317f683735ba9e487607dc53636b662077aff45e19456e6909007c5e76` |
| Comparison to golden fixture SHA | Different SHA. The candidate is distinct from the deterministic generated fixture. |
| production_art | `false` |
| promotion_ready | `false` |

## What It Proves

- A Blender-authored GLB can live under `examples/assets/candidates/`.
- Candidate metadata can point at the candidate without changing the manifest.
- The candidate passes the contract gate for schema, dimensions,
  `floor_back_left` anchor, material-slot names, and collision proxy name.
- The current manifest asset and golden contract fixture remain untouched.

## What It Does Not Prove

- It does not prove visual quality.
- It does not prove the asset is polished cabinet art.
- It does not prove UVs, textures, or PBR materials are production-ready.
- It does not prove topology, mesh hygiene, or real-time performance quality.
- It does not prove manufacturability or installation relevance.
- It does not provide human visual or manufacturing sign-off.

## Required Improvements Before Promotion

- High-quality PBR materials.
- Proper UV unwrapping.
- Optimized topology.
- Visual sign-off.
- Manufacturability review.

Promotion must happen in a future explicit PR. This review does not promote
the candidate and does not replace `examples/assets/galley_1000.glb`.
