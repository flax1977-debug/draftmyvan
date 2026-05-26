#!/usr/bin/env python3
"""Generate the deterministic galley_1000 GLB test fixture.

This is a **test-fixture generator**, not an art tool. Its job is to
produce a geometrically-correct stand-in so the manifest → validator →
asset pipeline can be exercised end-to-end before any polished cabinet
art exists.

Default invocation (no flags) regenerates the canonical fixture in place:

    cd draftmyvan
    python tools/assets/generate_galley_fixture_glb.py
    # reads  examples/galley_1000.json
    # writes examples/assets/galley_1000.glb

Both inputs can be overridden:
    --manifest <path>   Override the manifest source.
    --out <path>        Override the GLB output path.

The generated GLB:
    * Has exactly the bounding box implied by the manifest's
      `dimensions_mm` and `anchor`.
    * Uses metres in object data (glTF convention).
    * Is deterministic — `sort_keys=True` JSON, fixed vertex order,
      fixed index layout — so the committed fixture can be regenerated
      byte-for-byte and a test pins this.
    * Uses only the Python standard library (no Blender, no third-party
      glTF lib).

Limits (V1, deliberate):
    * Only `anchor = "floor_back_left"` is supported. Other anchors
      raise — silent acceptance is not an option here either.
    * Geometry is a closed axis-aligned box (8 vertices, 12 triangles).
      No materials, no normals, no UVs, no PBR. Adding those is art
      work, not contract work.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

# glTF 2.0 binary constants
GLB_MAGIC = b"glTF"
GLB_VERSION = 2
CHUNK_TYPE_JSON = 0x4E4F534A
CHUNK_TYPE_BIN = 0x004E4942

# glTF accessor componentType codes
COMP_FLOAT = 5126
COMP_UNSIGNED_SHORT = 5123

# bufferView targets
TARGET_ARRAY_BUFFER = 34962          # vertex attrs
TARGET_ELEMENT_ARRAY_BUFFER = 34963  # indices

GENERATOR_TAG = "DraftMyVan box generator v1"

# 12 triangles, outward-facing.
# Vertex layout matches `_vertices_floor_back_left` below.
BOX_INDICES: tuple[int, ...] = (
    # bottom (z=0), normal -Z
    0, 2, 1,  0, 3, 2,
    # top    (z=H), normal +Z
    4, 5, 6,  4, 6, 7,
    # front  (y=0), normal -Y
    0, 1, 5,  0, 5, 4,
    # back   (y=D), normal +Y
    3, 7, 6,  3, 6, 2,
    # left   (x=0), normal -X
    0, 4, 7,  0, 7, 3,
    # right  (x=W), normal +X
    1, 2, 6,  1, 6, 5,
)


def _vertices_floor_back_left(W: float, D: float, H: float) -> list[tuple[float, float, float]]:
    """8 box corners with bbox_min = (0,0,0), bbox_max = (W,D,H)."""
    return [
        (0.0, 0.0, 0.0),  # 0: back-left-bottom
        (W,   0.0, 0.0),  # 1: back-right-bottom
        (W,   D,   0.0),  # 2: front-right-bottom (if back is +Y, "front" is +Y direction… see contract)
        (0.0, D,   0.0),  # 3
        (0.0, 0.0, H),    # 4: back-left-top
        (W,   0.0, H),    # 5
        (W,   D,   H),    # 6
        (0.0, D,   H),    # 7
    ]


def _pack_positions(verts: list[tuple[float, float, float]]) -> bytes:
    return b"".join(struct.pack("<fff", x, y, z) for (x, y, z) in verts)


def _pack_indices(indices: tuple[int, ...]) -> bytes:
    return b"".join(struct.pack("<H", i) for i in indices)


def _pad4(blob: bytes, pad_byte: bytes) -> bytes:
    rem = (4 - len(blob) % 4) % 4
    return blob + pad_byte * rem


def make_box_glb_from_manifest(manifest: dict) -> bytes:
    """Return GLB bytes for the box implied by `manifest`. Deterministic."""
    dims = manifest.get("dimensions_mm") or {}
    try:
        width_mm = int(dims["width"])
        depth_mm = int(dims["depth"])
        height_mm = int(dims["height"])
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(
            "manifest.dimensions_mm must have integer width/depth/height"
        ) from e
    anchor = manifest.get("anchor")
    if anchor != "floor_back_left":
        raise ValueError(
            f"generator supports only anchor 'floor_back_left'; got {anchor!r}"
        )

    W, D, H = width_mm / 1000.0, depth_mm / 1000.0, height_mm / 1000.0
    verts = _vertices_floor_back_left(W, D, H)

    pos_bytes = _pad4(_pack_positions(verts), b"\x00")           # 8*12 = 96 bytes, already aligned
    idx_bytes = _pad4(_pack_indices(BOX_INDICES), b"\x00")        # 36*2 = 72 bytes, already aligned
    bin_payload = pos_bytes + idx_bytes

    gltf: dict = {
        "accessors": [
            {
                "bufferView": 0,
                "byteOffset": 0,
                "componentType": COMP_FLOAT,
                "count": len(verts),
                "max": [W, D, H],
                "min": [0.0, 0.0, 0.0],
                "type": "VEC3",
            },
            {
                "bufferView": 1,
                "byteOffset": 0,
                "componentType": COMP_UNSIGNED_SHORT,
                "count": len(BOX_INDICES),
                "type": "SCALAR",
            },
        ],
        "asset": {"generator": GENERATOR_TAG, "version": "2.0"},
        "bufferViews": [
            {
                "buffer": 0,
                "byteLength": len(pos_bytes),
                "byteOffset": 0,
                "target": TARGET_ARRAY_BUFFER,
            },
            {
                "buffer": 0,
                "byteLength": len(idx_bytes),
                "byteOffset": len(pos_bytes),
                "target": TARGET_ELEMENT_ARRAY_BUFFER,
            },
        ],
        "buffers": [{"byteLength": len(bin_payload)}],
        "meshes": [
            {"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}
        ],
        "nodes": [{"mesh": 0, "name": manifest.get("id", "module")}],
        "scene": 0,
        "scenes": [{"nodes": [0]}],
    }

    json_bytes = _pad4(
        json.dumps(gltf, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        b" ",
    )

    json_chunk = struct.pack("<II", len(json_bytes), CHUNK_TYPE_JSON) + json_bytes
    bin_chunk = struct.pack("<II", len(bin_payload), CHUNK_TYPE_BIN) + bin_payload

    total_length = 12 + len(json_chunk) + len(bin_chunk)
    header = struct.pack("<4sII", GLB_MAGIC, GLB_VERSION, total_length)
    return header + json_chunk + bin_chunk


REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # draftmyvan/
DEFAULT_MANIFEST = REPO_ROOT / "examples" / "galley_1000.json"
DEFAULT_OUT = REPO_ROOT / "examples" / "assets" / "galley_1000.glb"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the deterministic galley_1000 GLB test fixture.",
    )
    parser.add_argument(
        "--manifest", type=Path, default=DEFAULT_MANIFEST,
        help=f"Manifest JSON (default: examples/galley_1000.json).",
    )
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT,
        help=f"Output GLB path (default: examples/assets/galley_1000.glb).",
    )
    args = parser.parse_args(argv)

    if not args.manifest.exists():
        print(f"ERROR: manifest not found: {args.manifest}", file=sys.stderr)
        return 2
    with args.manifest.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    try:
        blob = make_box_glb_from_manifest(manifest)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(blob)
    print(f"wrote {args.out} ({len(blob)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
