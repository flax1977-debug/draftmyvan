# Candidate assets

This directory holds candidate GLBs, candidate acceptance metadata, and
candidate review metadata. These files are not production assets and are not
referenced by any manifest.

Candidates exist to test the real Blender export workflow before replacing
the manifest-selected asset at `examples/assets/galley_1000.glb`.

## Rules

- A candidate does not replace `examples/assets/galley_1000.glb` until a
  future promotion PR explicitly accepts it.
- The golden regression fixture at
  `tests/fixtures/galley_1000_contract_box.glb` must not be changed by
  candidate work.
- Every candidate GLB must pass `tools/assets/validate_candidate_asset.py`
  or an equivalent validator that runs the same schema, dimension, anchor,
  material-slot, and collision-proxy gates.
- Every candidate must have candidate acceptance metadata before promotion.
- Candidate metadata must keep `candidate_only: true`,
  `production_art: false`, and `promotion_allowed: false` until a separate
  promotion PR changes those fields.
- Candidate review metadata is mandatory. It must stay current with the exact
  candidate file SHA and must keep `production_art: false` and
  `promotion_ready: false` until a future explicit promotion PR.

## Lifecycle

```text
golden contract fixture
-> generated manifest asset
-> candidate asset
-> candidate review
-> accepted production asset
-> future UE5/Fusion consumers
```

This PR only reaches the candidate review stage. It records what the current
candidate proves and what is still missing before any production claim.

## Current candidate

`galley_1000_candidate.glb` is a simple Blender 5.1.2 export. It is a process
test, not polished cabinet art: a full-size body box, an unpolished metal sink
marker, and a `UCX_galley_1000` collision proxy, all authored inside the
manifest bounding box.

Validate it with:

```bash
python tools/assets/validate_candidate_asset.py \
    examples/assets/candidates/galley_1000_candidate.asset_acceptance.json
```

Review it with:

```bash
python tools/assets/validate_candidate_review.py \
    examples/assets/candidates/galley_1000_candidate_review.json
```

The current review report is
`examples/assets/candidates/galley_1000_candidate_review.md`. It says the
candidate is contract-valid but not production art and not promotion-ready.
Use `candidate_review_checklist.md` and `PROMOTION_CRITERIA.md` before any
future promotion work.
