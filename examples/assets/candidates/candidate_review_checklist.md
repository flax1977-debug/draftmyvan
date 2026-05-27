# Candidate Review Checklist

Use this checklist when reviewing a candidate GLB before any promotion PR.
Passing validation is required, but validation alone does not prove production
readiness.

## Geometry Correctness

- [ ] Cabinet volume and major feature positions match the manifest intent.
- [ ] No obvious gaps, inverted faces, stray geometry, or unintended overlaps.
- [ ] Door, carcass, sink, and visible feature proportions are plausible.

## Scale / Units

- [ ] Blender scene units are metric metres.
- [ ] Exported bounding box matches manifest dimensions in millimetres.
- [ ] No downstream import scale compensation is required.

## Origin / Anchor / Pivot

- [ ] Rear-left-bottom corner is at world `(0, 0, 0)`.
- [ ] Geometry extends into positive X, Y, and Z only.
- [ ] Object transforms are applied before export.
- [ ] Pivot behavior is suitable for placement and editing.

## Material-Slot Names

- [ ] Every manifest material slot exists in the GLB.
- [ ] Slot names match exactly, including case and punctuation.
- [ ] Temporary or duplicate material names have been removed.

## Collision Proxy Name

- [ ] Required collision proxy object exists.
- [ ] Proxy name matches the manifest exactly.
- [ ] Proxy bounds are intentional and not visual geometry by accident.

## Visual Quality

- [ ] Surfaces, seams, bevels, and proportions are acceptable for review.
- [ ] Placeholder blocks have been replaced before any production claim.
- [ ] The asset has been inspected from all normal viewing angles.

## Topology / Mesh Hygiene

- [ ] Meshes have reasonable polygon density for real-time use.
- [ ] Normals are correct.
- [ ] Non-manifold, duplicate, or hidden junk geometry has been removed.
- [ ] Modifier stack state is intentional before export.

## UVs / Materials / Textures

- [ ] UVs are unwrapped where textured materials require them.
- [ ] PBR material channels are authored and named consistently.
- [ ] Textures are correctly referenced or embedded by the chosen export policy.
- [ ] No missing texture placeholders remain.

## File Size / Real-Time Performance

- [ ] GLB size is reasonable for the target runtime.
- [ ] Mesh complexity is appropriate for repeated use in a configurator.
- [ ] No unnecessary high-density source meshes are exported.

## Export Hygiene

- [ ] No temporary objects are exported.
- [ ] No hidden layers or collections affect the exported result.
- [ ] Outliner contains only intentional export objects.
- [ ] Export settings match `tools/blender/EXPORT_REAL_ASSET.md`.

## Manufacturability Relevance

- [ ] Visible details do not contradict plausible cabinet construction.
- [ ] Sink, carcass, and panel representation are suitable for downstream review.
- [ ] Known non-manufacturable placeholders are documented.

## Sign-Off

- [ ] Visual reviewer recorded.
- [ ] Manufacturing reviewer recorded when relevant.
- [ ] Candidate review JSON updated with the current candidate SHA.
- [ ] Promotion decision happens in a future explicit promotion PR.
