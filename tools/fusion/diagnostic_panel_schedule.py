#!/usr/bin/env python3
"""Emit a diagnostic galley_v1 panel schedule from a validated panel payload.

This is a text verification aid only. It does not run Fusion 360 and does not
create fabrication output.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import fusion_create_galley_v1 as geometry


STATUS_VALID = "DIAGNOSTIC PANEL SCHEDULE VALID"
STATUS_INVALID = "DIAGNOSTIC PANEL SCHEDULE INVALID"
WARNING = (
    "Diagnostic verification schedule only. Not CNC, DXF, drawing, cut-list, "
    "joinery, toolpath, or manufacturing-ready output."
)


def _dimension_text(panel: dict, units: str) -> str:
    return (
        f"{panel['length_mm']} x {panel['width_mm']} x "
        f"{panel['thickness_mm']} {units}"
    )


def diagnostic_schedule_lines(payload_path: str | Path) -> list[str]:
    """Return deterministic Markdown schedule lines for a panel payload."""
    payload = geometry.load_panel_payload(payload_path)
    plan = geometry.fusion_geometry_plan(payload)
    panels = plan["panels"]
    units = plan["units"]

    lines = [
        "# Diagnostic Fusion Panel Schedule",
        "",
        WARNING,
        "",
        f"template: {plan['template']}",
        f"manifest_id: {plan['manifest_id']}",
        f"units: {units}",
        f"panel_count: {len(panels)}",
        "",
        "Expected Fusion output mapping:",
        "",
        "```text",
    ]
    for panel in panels:
        lines.append(f"{panel['component_name']} -> {panel['body_name']}")
    lines.extend(
        [
            "```",
            "",
            "Panel details:",
            "",
            "| Logical panel | Expected Fusion component | Expected Fusion body | "
            "Quantity | Dimensions |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    for panel in panels:
        lines.append(
            f"| `{panel['name']}` | `{panel['component_name']}` | "
            f"`{panel['body_name']}` | {panel['quantity']} | "
            f"`{_dimension_text(panel, units)}` |"
        )
    lines.extend(
        [
            "",
            WARNING,
        ]
    )
    return lines


def generate_schedule(payload_path: str | Path) -> tuple[str, list[str]]:
    """Validate a payload and return a diagnostic schedule or clear failure."""
    lines: list[str] = []
    try:
        lines.extend(diagnostic_schedule_lines(payload_path))
        lines.append("")
        lines.append(f"RESULT: {STATUS_VALID}")
        return STATUS_VALID, lines
    except geometry.FusionGeometryPlanError as e:
        lines.append(f"[FAIL] {e}")
        lines.append(f"RESULT: {STATUS_INVALID}")
        return STATUS_INVALID, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit a diagnostic galley_v1 panel schedule from a panel payload.",
    )
    parser.add_argument(
        "payload",
        type=Path,
        help="Panel payload JSON from export_galley_v1_panels.py.",
    )
    args = parser.parse_args(argv)

    status, lines = generate_schedule(args.payload)
    print(os.linesep.join(lines))
    return 0 if status == STATUS_VALID else 1


if __name__ == "__main__":
    sys.exit(main())
