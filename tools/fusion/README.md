# Fusion planning

This directory is the first manufacturing-side proof for DraftMyVan. It is
pure Python and planning-only: no Autodesk API, no Fusion 360 install, no CNC
post processors, and no DXF output.

## Purpose

The Fusion stage will eventually turn the same manifest truth used by visual
assets and runtime consumers into manufacturing artifacts. The first template is
`galley_v1`, a future parametric cabinet template for the `galley_1000`
manifest family.

## Fusion Owns Later

- Parametric cabinet template definitions.
- Cut lists derived from manifest dimensions and manufacturing metadata.
- Drawings derived from accepted manufacturing geometry.
- DXF/CNC exports after a later explicit manufacturing PR.

## Fusion Must Not Own

- Visual GLB truth. GLB assets remain under the visual pipeline and its gates.
- UE5 placement rules. Runtime placement comes from the manifest contract.
- Manifest schema truth. Fusion consumes validated manifests; it does not define
  the schema.

## Current Slice

This PR is a mapping/dry-run only. `galley_v1_parameter_map.json` declares how
manifest fields map to Fusion-style parameters, and
`export_galley_v1_parameters.py` writes a deterministic JSON dry-run payload.

The generated dry-run output is for review only and lives under `build/` by
default, which is ignored by Git.
