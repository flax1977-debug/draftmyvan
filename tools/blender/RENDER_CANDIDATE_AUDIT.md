# Rendering a Candidate Visual Audit

This local procedure explains how to inspect or render
`examples/assets/candidates/galley_1000_candidate.glb` in Blender. It records a
repeatable audit path only; this PR does not commit production renders and does
not promote the candidate.

## Open the Candidate

1. Open Blender locally.
2. Start with an empty scene.
3. Import the candidate:

   ```text
   File -> Import -> glTF 2.0 (.glb/.gltf)
   examples/assets/candidates/galley_1000_candidate.glb
   ```

4. Confirm scene units are metric metres.
5. Confirm the imported candidate remains at the origin and inside the
   manifest-sized bounds.
6. Use material preview or rendered preview for visual inspection.

## Suggested Views

Capture the same views each time so candidate comparisons are repeatable:

- `front`
- `rear`
- `left`
- `right`
- `top`
- `three_quarter`

For the `three_quarter` view, use a camera above the object looking toward the
front-left-top region so the body, sink marker, and overall proportions are
visible in one frame.

## Capturing Evidence Locally

Screenshots are acceptable for early audit passes. Blender still renders are
preferred once material and lighting quality matter.

Suggested local-only evidence path for future work:

```text
examples/assets/candidates/audit_evidence/galley_1000_candidate/<candidate_sha>/
```

Use filenames that include the view name, for example:

```text
front.png
rear.png
left.png
right.png
top.png
three_quarter.png
```

## CI Policy

Evidence images are optional in CI and should not be required yet. The CI gate
checks only the JSON visual-audit metadata and SHA synchronization. Images can
be added in a future PR once the evidence naming, size limits, and retention
policy are settled.

## Current Scope

This PR records the visual audit procedure and current findings. It does not
add production renders, does not claim visual sign-off, and does not replace
`examples/assets/galley_1000.glb`.
