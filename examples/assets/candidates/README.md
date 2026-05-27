# Candidate assets

This directory holds candidate GLBs, candidate acceptance metadata, candidate
review metadata, visual audit metadata, and render-evidence metadata. These
files are not production assets and are not referenced by any manifest.

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
- Render evidence is review support. The current blockout has six committed
  PNG views under `render_evidence/galley_1000_candidate/`, pinned by metadata
  path, size, and SHA256. These images are not product screenshots, do not
  claim production art, and do not promote the candidate. Other generated PNG
  output remains ignored until a future PR explicitly approves it.

## Lifecycle

```text
golden contract fixture
-> generated manifest asset
-> candidate asset
-> candidate review
-> visual audit
-> render evidence
-> accepted production asset
-> future UE5/Fusion consumers
```

The current state reaches the render-evidence workflow stage. It records what
the current candidate proves, what can be seen from local renders, and what is
still missing before any production claim. Render evidence now includes a
committed six-view PNG set for the current blockout only; future candidate
changes must regenerate the images and update the SHA-pinned metadata.

## Current candidate

`galley_1000_candidate.glb` is a script-generated Blender 5.1.2 cabinet
blockout. It is a process test, not polished cabinet art: a full-size carcass,
front door/drawer seam markers, plinth, countertop separation, an unpolished
metal sink marker, and a `UCX_galley_1000` collision proxy, all authored inside
the manifest bounding box.

Regenerate it with:

```bash
blender --background --python tools/blender/create_galley_candidate.py -- \
    --manifest examples/galley_1000.json \
    --out examples/assets/candidates/galley_1000_candidate.glb
```

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

Validate the local render-evidence procedure metadata with:

```bash
python tools/assets/validate_render_evidence.py \
    examples/assets/candidates/galley_1000_candidate_render_evidence.json
```

Generate local render evidence when Blender is available:

```bash
blender --background --python tools/blender/render_candidate_views.py -- \
    --candidate examples/assets/candidates/galley_1000_candidate.glb \
    --out examples/assets/candidates/render_evidence/galley_1000_candidate/
```

The current review report is
`examples/assets/candidates/galley_1000_candidate_review.md`. It says the
candidate is a contract-valid blockout but not production art and not
promotion-ready.
The current visual audit is
`examples/assets/candidates/galley_1000_candidate_visual_audit.md`; it says
the candidate is not production-ready and should not be promoted.

Use `candidate_review_checklist.md`, `PROMOTION_CRITERIA.md`, and
`tools/blender/RENDER_CANDIDATE_AUDIT.md` before any future promotion work.
The six committed render images are review evidence for this exact candidate
SHA only. They are not product screenshots and do not imply visual sign-off or
production readiness. Generated PNGs outside the approved
`render_evidence/galley_1000_candidate/` set remain ignored.
