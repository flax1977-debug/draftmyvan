#!/usr/bin/env python3
"""Validate a galley_v1 Fusion payload without requiring Fusion 360."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import fusion_galley_v1_skeleton as skeleton


STATUS_VALID = "FUSION PAYLOAD VALID"
STATUS_INVALID = "FUSION PAYLOAD INVALID"


def validate_payload_file(path: Path) -> tuple[str, list[str]]:
    lines: list[str] = []
    try:
        payload = skeleton.load_parameter_payload(path)
        summary = skeleton.parameter_summary(payload)
        lines.append(f"[OK] payload readable: {path}")
        lines.append(summary)
        lines.append(f"RESULT: {STATUS_VALID}")
        return STATUS_VALID, lines
    except skeleton.FusionPayloadError as e:
        lines.append(f"[FAIL] {e}")
        lines.append(f"RESULT: {STATUS_INVALID}")
        return STATUS_INVALID, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a DraftMyVan galley_v1 Fusion parameter payload.",
    )
    parser.add_argument("payload", type=Path, help="Fusion parameter payload JSON.")
    args = parser.parse_args(argv)

    status, lines = validate_payload_file(args.payload)
    print(os.linesep.join(lines))
    return 0 if status == STATUS_VALID else 1


if __name__ == "__main__":
    sys.exit(main())
