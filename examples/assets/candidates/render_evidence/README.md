# Render Evidence

This directory is the render evidence area for candidate review.

The approved `galley_1000_candidate/` folder contains six committed PNG
views for the current blockout candidate. They are review evidence only: not
product screenshots, not production art, and not candidate promotion.

Regenerate them locally with:

```bash
blender --background --python tools/blender/render_candidate_views.py -- \
  --candidate examples/assets/candidates/galley_1000_candidate.glb \
  --out examples/assets/candidates/render_evidence/galley_1000_candidate/
```

The committed files are pinned in
`examples/assets/candidates/galley_1000_candidate_render_evidence.json` by
view, path, file size, and SHA256. If the candidate GLB changes, regenerate all
six views and update that metadata.

Other generated PNGs under `render_evidence/` remain ignored by Git until a
future PR explicitly approves them.
