#!/usr/bin/env python3
"""Validate and summarize a planned galley_v1 Fusion geometry payload."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import fusion_create_galley_v1 as geometry


STATUS_VALID = "FUSION GEOMETRY PLAN VALID"
STATUS_INVALID = "FUSION GEOMETRY PLAN INVALID"


def check_geometry_plan(payload_path: Path, *, verbose: bool = False) -> tuple[str, list[str]]:
    lines: list[str] = []
    try:
        payload = geometry.load_panel_payload(payload_path)
        plan = geometry.fusion_geometry_plan(payload)
        lines.append(f"[OK] panel payload readable: {payload_path}")
        lines.append(geometry.geometry_plan_summary(plan))
        if verbose:
            for panel in plan["panels"]:
                lines.append(
                    f"{panel['name']}: sketch_plane={panel['sketch_plane']} "
                    f"extrude_axis={panel['extrude_axis']} "
                    f"extrude_distance_mm={panel['extrude_distance_mm']} "
                    f"placement_origin_mm={panel['placement_origin_mm']}"
                )
        lines.append(f"RESULT: {STATUS_VALID}")
        return STATUS_VALID, lines
    except geometry.FusionGeometryPlanError as e:
        lines.append(f"[FAIL] {e}")
        lines.append(f"RESULT: {STATUS_INVALID}")
        return STATUS_INVALID, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a galley_v1 panel payload and print its Fusion geometry plan.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print sketch plane, extrude axis, distance, and placement for every panel.",
    )
    parser.add_argument("payload", type=Path, help="Panel payload JSON from export_galley_v1_panels.py.")
    args = parser.parse_args(argv)

    status, lines = check_geometry_plan(args.payload, verbose=args.verbose)
    print(os.linesep.join(lines))
    return 0 if status == STATUS_VALID else 1


if __name__ == "__main__":
    sys.exit(main())
