"""Load a DraftMyVan manifest as a typed `Module`.

CLI:
    cd draftmyvan
    python -m runtime.load_module examples/galley_1000.json

CLI output is intentionally boring: id, type, dimensions, anchor,
placement, glb_path, resolved on-disk path, asset-present yes/no, and
either `RESULT: CONSUMABLE` or `RESULT: NOT CONSUMABLE`.

Exit codes:
    0  CONSUMABLE     — manifest loaded; GLB exists on disk.
    1  NOT CONSUMABLE — manifest loaded, but GLB is missing. Caller
                       should export and validate before runtime use.
    2  ERROR          — manifest unreadable or malformed (clear message).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .module import ConsumerError, Dimensions, Module


def _require(obj: Any, key: str, where: str) -> Any:
    if not isinstance(obj, dict) or key not in obj:
        raise ConsumerError(f"manifest missing required field {where!r}")
    return obj[key]


def _resolve_asset_path(manifest_path: Path, glb_path: str) -> Path:
    """Repo-relative `assets/foo.glb` → `<manifest_dir>/assets/foo.glb`.

    The manifest writes its visual paths as `assets/<file>` (per the
    schema's `^assets/.+\\.glb$` pattern); the on-disk location is
    `examples/assets/<file>` because the manifest itself lives in
    `examples/`. We use the manifest's parent directory rather than a
    hard-coded `examples/` so the same logic survives if manifests
    move later.
    """
    basename = os.path.basename(glb_path) or "?.glb"
    return manifest_path.parent / "assets" / basename


def load_module(manifest_path: Path) -> Module:
    """Read a manifest JSON file and return a typed `Module`.

    Does **not** run schema validation — that is the responsibility of
    `tools/validate_manifest.py`, run upstream. This function trusts the
    manifest's structure but still raises `ConsumerError` for missing
    required fields, so a malformed manifest produces a clear error
    rather than an `AttributeError` deep in caller code.
    """
    if not manifest_path.exists():
        raise ConsumerError(f"manifest not found: {manifest_path}")
    try:
        with manifest_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        raise ConsumerError(f"manifest {manifest_path} is not valid JSON: {e}") from e
    if not isinstance(raw, dict):
        raise ConsumerError(f"manifest {manifest_path} is not a JSON object")

    module_id = _require(raw, "id", "id")
    type_ = _require(raw, "type", "type")
    anchor = _require(raw, "anchor", "anchor")
    placement = _require(raw, "placement", "placement")

    dims_raw = _require(raw, "dimensions_mm", "dimensions_mm")
    width = _require(dims_raw, "width", "dimensions_mm.width")
    depth = _require(dims_raw, "depth", "dimensions_mm.depth")
    height = _require(dims_raw, "height", "dimensions_mm.height")
    # JSON-decoded ints come back as int; floats (e.g. 1000.5) come back
    # as float. We require strict ints because the manifest's truth is
    # millimetres-as-integers (schema enforces this upstream); `int(1.5)`
    # would silently truncate and is therefore dangerous.
    for name, value in (("width", width), ("depth", depth), ("height", height)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ConsumerError(
                f"manifest dimensions_mm.{name} must be an integer; "
                f"got {type(value).__name__} {value!r}"
            )
    dimensions = Dimensions(width_mm=width, depth_mm=depth, height_mm=height)

    visual = _require(raw, "visual", "visual")
    glb_path = _require(visual, "glb_path", "visual.glb_path")
    if not isinstance(glb_path, str) or not glb_path.endswith(".glb"):
        raise ConsumerError(
            f"manifest visual.glb_path must end in .glb (got {glb_path!r})"
        )

    resolved = _resolve_asset_path(manifest_path, glb_path)
    asset_exists = resolved.exists()

    return Module(
        id=str(module_id),
        type=str(type_),
        dimensions=dimensions,
        anchor=str(anchor),
        placement=str(placement),
        glb_path=str(glb_path),
        resolved_asset_path=resolved,
        asset_exists=bool(asset_exists),
    )


def _format_report(module: Module) -> list[str]:
    yes_no = "yes" if module.asset_exists else "no"
    lines = [
        f"module id:        {module.id}",
        f"type:             {module.type}",
        f"dimensions:       width={module.dimensions.width_mm} "
        f"depth={module.dimensions.depth_mm} "
        f"height={module.dimensions.height_mm} (mm)",
        f"anchor:           {module.anchor}",
        f"placement:        {module.placement}",
        f"glb_path:         {module.glb_path}",
        f"resolved path:    {module.resolved_asset_path}",
        f"asset present:    {yes_no}",
    ]
    if module.asset_exists:
        lines.append("RESULT: CONSUMABLE")
    else:
        lines.append(
            "RESULT: NOT CONSUMABLE — asset file missing at "
            f"{module.resolved_asset_path}; export and validate before runtime use."
        )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read a DraftMyVan manifest as typed runtime data.",
    )
    parser.add_argument("manifest", type=Path,
                        help="Path to the manifest JSON file.")
    args = parser.parse_args(argv)

    try:
        module = load_module(args.manifest)
    except ConsumerError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    for line in _format_report(module):
        print(line)
    return 0 if module.asset_exists else 1


if __name__ == "__main__":
    sys.exit(main())
