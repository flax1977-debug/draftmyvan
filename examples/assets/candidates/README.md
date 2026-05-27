# Candidate assets

This directory holds candidate GLBs, candidate acceptance metadata, candidate
review metadata, and visual audit metadata. These files are not production
assets and are not referenced by any manifest.

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
- Visual audit metadata is separate from contract validation. It records
  observed visual findings, must stay current with the exact candidate file
  SHA, and must keep `visual_status: not_production_ready` and
  `promotion_recommendation: do_not_promote` until a future explicit
  promotion PR.

## Lifecycle

```text
golden contract fixture
-> generated manifest asset
-> candidate asset
-> candidate review
-> visual audit
-> accepted production asset
-> future UE5/Fusion consumers
```

The current state reaches the visual audit stage. It records what the current
candidate proves, what can be seen from the current candidate, and what is
still missing before any production claim.

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

Audit its current visual state with:

```bash
python tools/assets/validate_candidate_visual_audit.py \
    examples/assets/candidates/galley_1000_candidate_visual_audit.json
```

The current review report is
`examples/assets/candidates/galley_1000_candidate_review.md`. It says the
candidate is contract-valid but not production art and not promotion-ready.
The current visual audit is
`examples/assets/candidates/galley_1000_candidate_visual_audit.md`; it says
the candidate is not production-ready and should not be promoted.

Use `candidate_review_checklist.md`, `PROMOTION_CRITERIA.md`, and
`tools/blender/RENDER_CANDIDATE_AUDIT.md` before any future promotion work.
No render images are committed yet.
