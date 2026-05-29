# Fusion Panel Payload Contract

This document describes the JSON payload contract used by the
verification-only DraftMyVan Fusion galley panel import.

The current validated payload path is:

```text
/tmp/galley_1000_panels.json
```

The known dry-run result for that payload is:

```text
RESULT: FUSION GEOMETRY DRY RUN VALID
planned_panel_count: 5
Galley_LeftSide -> left_side_body
Galley_RightSide -> right_side_body
Galley_BottomPanel -> bottom_panel_body
Galley_TopPanel -> top_panel_body
Galley_BackPanel -> back_panel_body
```

## Purpose

The payload lets `tools/fusion/fusion_create_galley_v1.py` validate a
deterministic five-panel `galley_v1` carcass description and, when run manually
inside Fusion 360, create five rectangular panel bodies/components for
verification only.

## Scope

This contract covers the panel payload produced for the current `galley_v1`
verification path and the derived Fusion geometry plan created by
`fusion_create_galley_v1.py`.

It covers:

- Required raw panel payload shape.
- Required logical panel identities.
- Derived Fusion component/body naming.
- Validation expectations used by the dry-run and manual Fusion script.
- Failure behavior for invalid or missing payloads.

It does not define a general cabinet manufacturing schema.

## Verification-Only Status

The payload and Fusion script are for workflow and geometry verification only.
The current geometry is first-pass rectangular panel geometry. It is not a
manufacturing artifact and must not be treated as approved build output.

## Producer And Consumer

Identifiable from the repo:

- Producer: `tools/fusion/export_galley_v1_panels.py`.
- Panel math helper: `tools/fusion/compute_galley_panels.py`.
- Consumer/dry-run/manual Fusion script:
  `tools/fusion/fusion_create_galley_v1.py`.
- Geometry plan checker: `tools/fusion/check_fusion_geometry_plan.py`.
- Expected panel fixture:
  `tests/fixtures/galley_1000_panels.expected.json`.
- Expected derived geometry-plan fixture:
  `tests/fixtures/galley_1000_fusion_geometry_plan.expected.json`.

The manual Fusion script reads the payload path from `context` when supplied, or
from the environment variable:

```text
DRAFTMYVAN_FUSION_PANEL_PAYLOAD
```

For the current manual verification run, that variable should point to:

```text
/tmp/galley_1000_panels.json
```

## Required Top-Level Structure

Based on `fusion_create_galley_v1.py`,
`compute_galley_panels.py`, and the current fixtures, the raw panel payload is a
JSON object with these required top-level fields:

| Field | Required value or shape |
| --- | --- |
| `template` | Non-empty string; must be `galley_v1`. |
| `manifest_id` | Non-empty string. |
| `assumptions` | Non-empty list of non-empty strings. |
| `panels` | Non-empty list of panel objects. |
| `totals` | Object containing totals checked against `panels`. |

Minimal structural shape:

```json
{
  "template": "galley_v1",
  "manifest_id": "galley_1000_sink_left_oak",
  "assumptions": [],
  "panels": [],
  "totals": {}
}
```

The abbreviated example above is not a valid payload by itself. In a valid
payload, `assumptions` and `panels` must not be empty.

### Panel Object Fields

Every raw payload panel object must contain these fields:

| Field | Required value or shape |
| --- | --- |
| `name` | Non-empty string; must be unique. |
| `length_mm` | Positive integer. |
| `width_mm` | Positive integer. |
| `thickness_mm` | Positive integer. |
| `quantity` | Positive integer. |
| `material` | Non-empty string. |
| `orientation` | Non-empty string. |
| `notes` | Non-empty string. |

The `_mm` suffixes are the explicit unit marker for raw dimensions in the panel
payload. The derived geometry plan also carries top-level `units: "mm"`.

### Totals Object

The raw payload `totals` object must be present. The current validator checks:

- `totals.panel_count` equals the sum of panel `quantity` values.
- `totals.unique_panel_types` equals the number of unique panel `name` values.

The fixture also includes `totals.approximate_sheet_area_m2`, but the current
consumer validation does not require that field.

## Required Panel Identities

The current `galley_v1` validator requires exactly these five logical raw panel
names, in this order:

```text
left_side
right_side
bottom_panel
top_panel
back_panel
```

The derived Fusion geometry plan maps those logical panel names to these
required component identities:

```text
Galley_LeftSide
Galley_RightSide
Galley_BottomPanel
Galley_TopPanel
Galley_BackPanel
```

## Expected Fusion Output Mapping

The dry-run and derived geometry plan expect this exact component/body mapping:

```text
Galley_LeftSide -> left_side_body
Galley_RightSide -> right_side_body
Galley_BottomPanel -> bottom_panel_body
Galley_TopPanel -> top_panel_body
Galley_BackPanel -> back_panel_body
```

## Derived Geometry Plan Fields

The raw payload does not contain Fusion sketch/extrude placement fields. Those
fields are derived by `fusion_create_galley_v1.py` from the raw panel payload.

The derived geometry plan top-level object contains:

| Field | Required value or shape |
| --- | --- |
| `template` | Must be `galley_v1`. |
| `manifest_id` | Non-empty string. |
| `units` | Must be `mm`. |
| `source` | Must be `panel_payload`. |
| `geometry_status` | Must be `planned_not_executed`. |
| `panels` | Non-empty list of derived panel plan objects. |
| `deferred` | Non-empty list of non-empty strings. |

Every derived panel plan object must contain:

```text
name
component_name
body_name
length_mm
width_mm
thickness_mm
quantity
material
orientation
sketch_plane
extrude_axis
extrude_distance_mm
placement_origin_mm
placement_note
construction_method
status
notes
```

The current derived plan uses `status: "planned_not_executed"` for every panel.
`placement_origin_mm` must be a three-number list.

## Validation Expectations

The current validation path expects:

- Exactly five planned panels for this milestone.
- No duplicate raw logical panel names.
- No duplicate derived `component_name` values.
- No duplicate derived `body_name` values.
- Raw panel dimensions `length_mm`, `width_mm`, and `thickness_mm` are positive
  integers.
- Raw panel `quantity` is a positive integer.
- Derived `extrude_distance_mm` is a positive integer.
- Required raw panel fields exist.
- Required derived geometry fields exist before Fusion body creation.
- Units are explicit through raw `_mm` field suffixes and derived
  `units: "mm"`.
- The manual Fusion payload path is provided through
  `DRAFTMYVAN_FUSION_PANEL_PAYLOAD` unless a launcher supplies the path through
  script context.

The current five-panel carcass checks also require:

- `right_side` dimensions match `left_side` dimensions.
- `top_panel` dimensions match `bottom_panel` dimensions.
- Top/bottom panel depth matches side panel depth.
- Back panel length matches top/bottom panel length.
- Back panel width equals side panel height minus two times panel thickness.
- All panels share one `thickness_mm` value.

## Failure Behavior

Expected failure behavior for this verification milestone:

- Missing payload file fails clearly with a readable file error.
- Invalid JSON fails clearly with a readable JSON error.
- Invalid payload shape fails clearly with a readable validation error.
- Missing `DRAFTMYVAN_FUSION_PANEL_PAYLOAD` causes the Fusion script to report
  that no payload path was supplied and create no geometry.
- Dry-run failures print `RESULT: FUSION GEOMETRY DRY RUN INVALID`.
- A partial or mismatched Fusion result must not be accepted as success.

Treat any error, wrong count, wrong name, wrong unit scale, or extra geometry as
a failed manual verification run.

## Non-Goals

This contract does not define or authorize:

- CNC output.
- DXF files.
- Drawings.
- Cut lists.
- Joinery assumptions.
- Toolpaths.
- Fabrication instructions.
- Manufacturing readiness.

The payload and resulting Fusion geometry remain verification-only.
