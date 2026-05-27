# Candidate Promotion Criteria

Validation passing does not equal production readiness. The GLB gate proves
contract compliance only: schema, dimensions, anchor, material-slot names, and
collision proxy. It does not prove visual quality, manufacturability, topology
quality, UV quality, material quality, or runtime performance.

## Required State Before Promotion

- Candidate review metadata must be current with the exact candidate SHA.
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
- Human visual sign-off is recorded.
- Human manufacturing or buildability sign-off is recorded.
- Current-asset acceptance metadata is updated to a real production-art state.
- The golden contract fixture remains as the regression reference.

Until then, the candidate remains a candidate and is not product-facing.
