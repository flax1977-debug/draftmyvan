# galley_v1 parametric plan

`galley_v1` is the first planned manufacturing template for the DraftMyVan
galley family. It starts from `examples/galley_1000.json` and consumes only the
manifest fields needed for a cabinet parameter dry-run.

## Source Of Truth

The manifest remains the source of truth:

- `id` identifies the module.
- `dimensions_mm.width`, `dimensions_mm.depth`, and `dimensions_mm.height`
  provide external bounds in integer millimetres.
- `manufacturing.plywood_thickness_mm` provides the cabinet material thickness.
- `manufacturing.fusion_template` selects `galley_v1`.
- `manufacturing.hardware` provides hardware line items for later assembly
  planning.

## Planned Template Responsibilities

Later Fusion work may use these parameters to drive:

- A parametric cabinet carcass.
- Door/drawer panel layouts.
- Countertop and sink opening references.
- Cut-list derivation.
- Drawing output.
- DXF/CNC output after explicit CNC guardrails exist.

## Explicitly Out Of Scope

This plan does not:

- Automate Fusion 360.
- Require Autodesk libraries in CI.
- Generate DXF, CNC, drawings, or manufacturing-ready output.
- Replace, promote, or inspect visual GLB assets.
- Add UE5, UI, dashboard, or catalog entries.

## Deferred Manifest Fields

The following fields are intentionally not Fusion parameters in this first
mapping:

- `visual.glb_path`
- `visual.material_slots`
- `visual.collision_proxy`
- `anchor`
- `placement`
- `clearances`
- `rules.service_access`

They remain part of the broader manifest contract, but this mapping keeps the
manufacturing proof focused on dry-run parameter consumption.

## Script Skeleton

`fusion_galley_v1_skeleton.py` is the first Fusion-side script skeleton. Normal
Python can import it without Fusion installed because Autodesk `adsk` imports
remain inside guarded Fusion-only functions. The skeleton currently:

- Loads a `galley_v1` parameter payload JSON.
- Validates `template`, `manifest_id`, `Width`, `Depth`, `Height`, and
  `PlyThickness`.
- Rejects float, string, boolean, missing, or non-positive parameter values.
- Produces a text summary for CLI output or future Fusion UI logging.
- Provides a `run(context)` entry point for a later Fusion script/add-in.

It does not create geometry, drawings, cut lists, DXF, CNC, or
manufacturing-ready output. The next future step is a simple parametric
box/carcass proof inside Fusion from the validated payload.
