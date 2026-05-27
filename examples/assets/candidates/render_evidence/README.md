# Render Evidence

This directory is the local output area for candidate render evidence.

PNG renders are not committed yet. Generate them locally with:

```bash
blender --background --python tools/blender/render_candidate_views.py -- \
  --candidate examples/assets/candidates/galley_1000_candidate.glb \
  --out examples/assets/candidates/render_evidence/galley_1000_candidate/
```

The generated PNGs are ignored by Git. Future PRs can decide whether a small,
stable image set should be committed after naming, size, and retention rules
are settled.
