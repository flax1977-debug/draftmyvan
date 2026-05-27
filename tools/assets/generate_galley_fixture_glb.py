#!/usr/bin/env python3
"""Generate the deterministic galley_1000 GLB test fixture.

This is a **test-fixture generator**, not an art tool. Its job is to
produce a geometrically-correct stand-in so the manifest → validator →
asset pipeline can be exercised end-to-end before any polished cabinet
art exists.

Two outputs, two roles
----------------------

The generator targets two distinct files by default:

1. The **golden contract fixture** at
   ``tests/fixtures/galley_1000_contract_box.glb``.

   This is the permanent regression reference. Its bytes are pinned to
   this generator's output via
   ``test_committed_fixture_matches_generator_byte_for_byte``. It does
   **not** participate in any manifest's ``visual.glb_path`` — it lives
   under ``tests/fixtures/`` precisely so future real cabinet art landing
   under ``examples/assets/`` cannot silently erase it.

2. The **current manifest asset** at
   ``examples/assets/galley_1000.glb``.

   This is the file that ``examples/galley_1000.json`` actually points
   at. Today it is bit-identical to the golden fixture (because no real
   art exists). The day real cabinet art lands, its bytes will diverge —
   at which point the acceptance metadata at
   ``examples/assets/galley_1000.asset_acceptance.json`` flips
   ``generated_fixture_replaced`` to ``true`` and this generator refuses
   to overwrite the manifest asset.

Default invocation (no flags) regenerates the canonical fixture in place::

    cd /path/to/draftmyvan
    python tools/assets/generate_galley_fixture_glb.py

This:

  * Always writes the golden contract fixture
    (``tests/fixtures/galley_1000_contract_box.glb``).
  * Also writes the manifest asset (``examples/assets/galley_1000.glb``)
    **only** if the acceptance metadata for that asset declares
    ``generated_fixture_replaced: false`` (or the metadata file is
    absent). When the metadata says the manifest asset is real art,
    the generator prints a notice and skips that write.

Overrides::

    --manifest <path>           Override the manifest source.
    --out <path>                Write only to <path>; never touches
                                either of the canonical defaults.
    --skip-manifest-asset       Always skip the manifest asset write,
                                even if metadata permits it.

The generated GLB:
    * Has exactly the bounding box implied by the manifest's
      ``dimensions_mm`` and ``anchor``.
    * Declares every ``visual.material_slots[]`` name as a placeholder
      material.
    * Contains a placeholder collision proxy node/mesh named exactly
      ``visual.collision_proxy``; it reuses the box geometry because this
      fixture proves contract wiring, not production collision art.
    * Uses metres in object data (glTF convention).
    * Is deterministic — ``sort_keys=True`` JSON, fixed vertex order,
      fixed index layout — so the committed fixture can be regenerated
      byte-for-byte and a test pins this.
    * Uses only the Python standard library (no Blender, no third-party
      glTF lib).

Limits (V1, deliberate):
    * Only ``anchor = "floor_back_left"`` is supported. Other anchors
      raise — silent acceptance is not an option here either.
    * Geometry is a closed axis-aligned box (8 vertices, 12 triangles).
      Materials and collision proxy are placeholder contract markers only:
      no normals, no UVs, no PBR, no production collision hull.
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

GENERATOR_TAG = "DraftMyVan box generator v2"

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


def _manifest_material_slots(manifest: dict) -> tuple[str, ...]:
    visual = manifest.get("visual") or {}
    slots = visual.get("material_slots")
    if not isinstance(slots, list) or not slots:
        raise ValueError("manifest.visual.material_slots must be a non-empty list")
    bad = [slot for slot in slots if not isinstance(slot, str) or not slot]
    if bad:
        raise ValueError("manifest.visual.material_slots entries must be non-empty strings")
    return tuple(slots)


def _manifest_collision_proxy(manifest: dict) -> str:
    visual = manifest.get("visual") or {}
    proxy = visual.get("collision_proxy")
    if not isinstance(proxy, str) or not proxy:
        raise ValueError("manifest.visual.collision_proxy must be a non-empty string")
    return proxy


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
    material_slots = _manifest_material_slots(manifest)
    collision_proxy = _manifest_collision_proxy(manifest)

    W, D, H = width_mm / 1000.0, depth_mm / 1000.0, height_mm / 1000.0
    verts = _vertices_floor_back_left(W, D, H)

    pos_bytes = _pad4(_pack_positions(verts), b"\x00")           # 8*12 = 96 bytes, already aligned
    idx_bytes = _pad4(_pack_indices(BOX_INDICES), b"\x00")        # 36*2 = 72 bytes, already aligned
    bin_payload = pos_bytes + idx_bytes

    module_primitives = [
        {"attributes": {"POSITION": 0}, "indices": 1, "material": i}
        for i, _ in enumerate(material_slots)
    ]

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
        "materials": [{"name": slot} for slot in material_slots],
        "meshes": [
            {
                "name": manifest.get("id", "module"),
                "primitives": module_primitives,
            },
            {
                "name": collision_proxy,
                "primitives": [{"attributes": {"POSITION": 0}, "indices": 1}],
            },
        ],
        "nodes": [
            {"mesh": 0, "name": manifest.get("id", "module")},
            {"mesh": 1, "name": collision_proxy},
        ],
        "scene": 0,
        "scenes": [{"nodes": [0, 1]}],
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


REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # repository root
DEFAULT_MANIFEST = REPO_ROOT / "examples" / "galley_1000.json"
# Golden contract fixture: permanent regression reference. Lives under
# tests/fixtures/ so future real cabinet art landing in examples/assets/
# can never silently erase it.
DEFAULT_GOLDEN_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "galley_1000_contract_box.glb"
# Current manifest asset: what examples/galley_1000.json points at.
# Today this is the same bytes as the golden fixture; tomorrow it may be
# real cabinet art (gated by asset_acceptance.json — see below).
DEFAULT_MANIFEST_ASSET = REPO_ROOT / "examples" / "assets" / "galley_1000.glb"
DEFAULT_ACCEPTANCE_METADATA = REPO_ROOT / "examples" / "assets" / "galley_1000.asset_acceptance.json"


def _manifest_asset_is_real_art(metadata_path: Path) -> bool:
    """True iff the acceptance metadata explicitly declares real art is in place.

    Absent metadata, or metadata that does not flip the flag, is treated
    as "still a generated fixture" — i.e. safe to overwrite.
    """
    if not metadata_path.exists():
        return False
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # If the metadata is unreadable, err on the side of NOT clobbering.
        return True
    return bool(data.get("generated_fixture_replaced", False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the deterministic galley_1000 GLB test fixture.",
    )
    parser.add_argument(
        "--manifest", type=Path, default=DEFAULT_MANIFEST,
        help="Manifest JSON (default: examples/galley_1000.json).",
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help="Write only to this path; do not touch the canonical "
             "golden-fixture or manifest-asset paths. Use this for "
             "candidate checks (e.g. /tmp/...).",
    )
    parser.add_argument(
        "--skip-manifest-asset", action="store_true",
        help="Always skip writing the manifest asset "
             "(examples/assets/galley_1000.glb), even when the "
             "acceptance metadata permits the overwrite.",
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

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(blob)
        print(f"wrote {args.out} ({len(blob)} bytes)")
        return 0

    # Canonical default: golden fixture is always rewritten.
    DEFAULT_GOLDEN_FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_GOLDEN_FIXTURE.write_bytes(blob)
    print(f"wrote golden fixture: {DEFAULT_GOLDEN_FIXTURE} ({len(blob)} bytes)")

    if args.skip_manifest_asset:
        print("skipped manifest asset (forced by --skip-manifest-asset)")
        return 0

    if _manifest_asset_is_real_art(DEFAULT_ACCEPTANCE_METADATA):
        print(
            f"skipped manifest asset: {DEFAULT_MANIFEST_ASSET}\n"
            f"  reason: {DEFAULT_ACCEPTANCE_METADATA} declares "
            f"generated_fixture_replaced=true (real art is in place).\n"
            f"  to overwrite anyway, run with --out {DEFAULT_MANIFEST_ASSET}"
        )
        return 0

    DEFAULT_MANIFEST_ASSET.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_MANIFEST_ASSET.write_bytes(blob)
    print(f"wrote manifest asset: {DEFAULT_MANIFEST_ASSET} ({len(blob)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
