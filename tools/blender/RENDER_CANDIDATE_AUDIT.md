# Rendering a Candidate Visual Audit

This local procedure explains how to inspect or render
`examples/assets/candidates/galley_1000_candidate.glb` in Blender. It records a
repeatable audit path only; it does not commit production renders and does not
promote the candidate.

The scripted local renderer is:

```bash
blender --background --python tools/blender/render_candidate_views.py -- \
  --candidate examples/assets/candidates/galley_1000_candidate.glb \
  --out examples/assets/candidates/render_evidence/galley_1000_candidate/
```

The renderer is visual-review tooling only. It orients the GLB contract axes
for Blender's Z-up camera views and hides `UCX_` collision proxy meshes from
the rendered PNGs. The collision proxy remains in the GLB and is still checked
by the validators.

Validate the metadata/procedure without Blender:

```bash
python tools/assets/validate_render_evidence.py \
  examples/assets/candidates/galley_1000_candidate_render_evidence.json
```

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

The script writes one PNG per standard view. Manual screenshots are acceptable
for exploratory audit passes, but script output is preferred for repeatable
evidence.

Repository-local output path when evidence is intentionally retained:

```text
examples/assets/candidates/render_evidence/galley_1000_candidate/
```

For throwaway inspection runs, write to `/tmp`, for example:

```bash
blender --background --python tools/blender/render_candidate_views.py -- \
  --candidate examples/assets/candidates/galley_1000_candidate.glb \
  --out /tmp/draftmyvan_candidate_renders_v2
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
checks only the JSON visual-audit metadata, render-evidence metadata, and
script path. Generated PNGs are ignored by Git. Images can be added in a future
PR once the evidence naming, size limits, determinism, and retention policy are
settled.

## Current Scope

The current workflow records the visual audit procedure, current findings, and
a local render-generation script. It does not add production renders, does not
claim visual sign-off, and does not replace `examples/assets/galley_1000.glb`.
