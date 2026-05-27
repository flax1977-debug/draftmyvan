#!/usr/bin/env python3
"""Export deterministic galley_v1 panel math from a Fusion payload."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import compute_galley_panels as panel_math


STATUS_EXPORTED = "GALLEY PANELS EXPORTED"
STATUS_INVALID = "GALLEY PANELS INVALID"


def export_panels(payload_path: Path, out_path: Path) -> tuple[str, list[str]]:
    lines: list[str] = []
    try:
        payload = panel_math.load_payload(payload_path)
        breakdown = panel_math.build_panel_breakdown(payload)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(breakdown, indent=2) + "\n", encoding="utf-8")
        lines.append(f"[OK] payload readable: {payload_path}")
        lines.append(f"[OK] wrote panel breakdown: {out_path}")
        lines.append(panel_math.panel_summary(breakdown["panels"]))
        lines.append(f"RESULT: {STATUS_EXPORTED}")
        return STATUS_EXPORTED, lines
    except (OSError, panel_math.GalleyPanelError) as e:
        lines.append(f"[FAIL] {e}")
        lines.append(f"RESULT: {STATUS_INVALID}")
        return STATUS_INVALID, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export galley_v1 panel math from a Fusion parameter payload.",
    )
    parser.add_argument("--payload", required=True, type=Path, help="Fusion parameter payload JSON.")
    parser.add_argument("--out", required=True, type=Path, help="Output panel breakdown JSON.")
    args = parser.parse_args(argv)

    status, lines = export_panels(args.payload, args.out)
    print(os.linesep.join(lines))
    return 0 if status == STATUS_EXPORTED else 1


if __name__ == "__main__":
    sys.exit(main())
