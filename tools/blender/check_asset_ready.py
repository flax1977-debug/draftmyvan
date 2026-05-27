#!/usr/bin/env python3
"""One command: is this candidate GLB ready to commit?

A pure-Python wrapper around the existing validators that gives a single
PASS/FAIL verdict and a checklist-style report. Saves a human (or
future CI step) from running three commands and stitching the output
together.

What it runs:

  1. Manifest schema validation (via the manifest validator).
  2. Path existence + basename match against `visual.glb_path`.
  3. Dimension + origin/anchor + material-slot + collision-proxy validation
     (via the Blender-side pure-Python validator).

Usage from the repository root (default GLB resolved from the manifest):

    cd /path/to/draftmyvan
    python tools/blender/check_asset_ready.py \\
        --manifest examples/galley_1000.json

Override the GLB explicitly (e.g. a candidate in /tmp before commit):

    python tools/blender/check_asset_ready.py \\
        --manifest examples/galley_1000.json \\
        --glb /tmp/galley_v2.glb

Exit codes:
    0  READY     — all checks pass; safe to commit (subject to the
                  procedure in EXPORT_REAL_ASSET.md).
    1  NOT READY — at least one validator gate failed.
    2  ERROR     — manifest unreadable, GLB unreadable, or arguments bad.

This script does **not** touch Blender. It is safe in CI.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Make the sibling validators importable.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))                              # tools/blender/
sys.path.insert(0, str(_HERE.parent))                       # tools/ (for validate_manifest)

import validate_glb_against_manifest as v  # noqa: E402

try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None  # type: ignore[assignment]


def _repo_root() -> Path:
    """Repository root."""
    return _HERE.parent.parent


def _schema_path() -> Path:
    return _repo_root() / "manifest.schema.json"


def _default_glb_for(manifest_path: Path, manifest: dict) -> Path:
    """Resolve the expected on-disk GLB path from `manifest.visual.glb_path`.

    Convention: a manifest at `examples/<id>.json` whose `visual.glb_path`
    is `assets/<id>.glb` resolves to `examples/assets/<id>.glb`.
    """
    rel = (manifest.get("visual") or {}).get("glb_path", "")
    basename = os.path.basename(rel) or "?.glb"
    return manifest_path.parent / "assets" / basename


def check(
    manifest_path: Path,
    glb_path: Path | None = None,
    tolerance_mm: float = 1.0,
    glb_units: str = "meters",
) -> tuple[int, list[str]]:
    """Run every gate. Returns (exit_code, report_lines)."""
    lines: list[str] = []

    # --- 1. Manifest readable ---
    try:
        manifest = v.load_manifest(manifest_path)
    except v.ManifestError as e:
        return 2, [f"[ERROR] manifest: {e}"]
    lines.append(f"[OK]   Manifest readable: {manifest_path}")

    # --- 2. Manifest schema ---
    if Draft202012Validator is None:
        return 2, lines + [
            "[ERROR] jsonschema not installed; cannot run manifest schema validation. "
            "Run `pip install jsonschema` and re-run."
        ]
    else:
        try:
            schema = json.loads(_schema_path().read_text(encoding="utf-8"))
            errors = list(Draft202012Validator(schema).iter_errors(manifest))
        except Exception as e:
            return 2, lines + [f"[ERROR] could not load schema: {e}"]
        if errors:
            lines.append("[FAIL] Manifest schema validation:")
            for err in errors:
                path = "/".join(str(p) for p in err.absolute_path) or "<root>"
                lines.append(f"       - {path}: {err.message}")
            lines.append("RESULT: NOT READY — fix the manifest and re-run")
            return 1, lines
        lines.append("[OK]   Manifest schema validates")

    # --- 3. Resolve and check the GLB path ---
    if glb_path is None:
        glb_path = _default_glb_for(manifest_path, manifest)
        lines.append(f"[INFO] GLB path defaulted to: {glb_path}")
    if not glb_path.exists():
        lines.append(f"[FAIL] GLB file not found: {glb_path}")
        lines.append("RESULT: NOT READY — export the GLB first (see EXPORT_REAL_ASSET.md)")
        return 1, lines
    lines.append(f"[OK]   GLB file exists: {glb_path}")

    # --- 4. Full dimension + anchor/origin validation ---
    try:
        report = v.validate(
            manifest_path=manifest_path,
            glb_path=glb_path,
            tolerance_mm=tolerance_mm,
            glb_units=glb_units,
        )
    except (v.ManifestError, v.GlbParseError) as e:
        return 2, lines + [f"[ERROR] validator: {e}"]

    # Indent the validator's own report so it reads as a sub-section.
    lines.append("[..]   Validator report:")
    for msg in report.messages:
        lines.append(f"       {msg}")

    if report.ok:
        lines.append("RESULT: READY — every gate passed within tolerance")
        return 0, lines
    lines.append("RESULT: NOT READY — see validator report above; "
                 "follow EXPORT_REAL_ASSET.md to fix and re-run")
    return 1, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="One-shot readiness check for a DraftMyVan candidate GLB.",
    )
    parser.add_argument("--manifest", required=True, type=Path,
                        help="Path to the manifest JSON.")
    parser.add_argument("--glb", type=Path, default=None,
                        help="Path to the candidate GLB (default: derived "
                             "from manifest.visual.glb_path).")
    parser.add_argument("--tolerance-mm", type=float, default=1.0,
                        help="Per-axis tolerance in mm (default: 1.0).")
    parser.add_argument("--glb-units", choices=("meters", "millimeters"),
                        default="meters",
                        help="Unit interpretation of GLB positions (default: meters).")
    args = parser.parse_args(argv)

    code, report_lines = check(
        manifest_path=args.manifest,
        glb_path=args.glb,
        tolerance_mm=args.tolerance_mm,
        glb_units=args.glb_units,
    )
    print("\n".join(report_lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
