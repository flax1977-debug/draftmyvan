# Candidate Promotion Criteria

Validation passing does not equal production readiness. The GLB gate proves
contract compliance only: schema, dimensions, anchor, material-slot names, and
collision proxy. It does not prove visual quality, manufacturability, topology
quality, UV quality, material quality, or runtime performance.

Visual audit passing is also not promotion. It records repeatable findings and
keeps the candidate SHA-synced, but the current audit state is
`not_production_ready` with `do_not_promote`.

Render evidence supports human review, but it is not promotion either. The
current render-evidence state is `procedure_ready`; generated PNGs are ignored
and not committed yet.

## Required State Before Promotion

- Candidate review metadata must be current with the exact candidate SHA.
- Candidate visual audit metadata must be current with the exact candidate SHA.
- Candidate render-evidence metadata must be current with the exact candidate
  SHA and point to the local render script/output directory.
- `production_art` must stay `false` until a future explicit promotion PR.
- `promotion_ready` must stay `false` until a future explicit promotion PR.
- The current manifest asset at `examples/assets/galley_1000.glb` must not be
  replaced by candidate-review work.
- The golden contract fixture at
  `tests/fixtures/galley_1000_contract_box.glb` must remain unchanged.

## Future Promotion PR

A future promotion PR may replace `examples/assets/galley_1000.glb` only after
all of the following are true:

- The candidate passes the full existing gates.
- Candidate review metadata matches the candidate SHA.
- Candidate visual audit metadata matches the candidate SHA and includes
  current visual findings.
- Render evidence is generated, reviewed, or explicitly deferred according to
  the current render-evidence metadata.
- Human visual sign-off is recorded.
- Human manufacturing or buildability sign-off is recorded.
- Current-asset acceptance metadata is updated to a real production-art state.
- The golden contract fixture remains as the regression reference.

Until then, the candidate remains a candidate and is not product-facing.
