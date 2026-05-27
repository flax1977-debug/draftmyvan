#!/usr/bin/env python3
"""Create the galley_1000 Blender blockout candidate GLB.

Run inside Blender from the repository root:

    blender --background --python tools/blender/create_galley_candidate.py -- \
      --manifest examples/galley_1000.json \
      --out examples/assets/candidates/galley_1000_candidate.glb

This is a reproducible candidate generator, not production art. It creates a
simple cabinet blockout that keeps the manifest dimensions, material-slot
names, and collision-proxy contract intact while adding enough visible form to
support visual review renders.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import bpy
except ImportError as e:  # pragma: no cover - this script is run inside Blender.
    raise SystemExit("create_galley_candidate.py must be run inside Blender") from e


REQUIRED_MATERIALS = ("oak_body", "sink_metal")


def _argv_after_blender_separator() -> list[str]:
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1 :]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the galley_1000 blockout candidate GLB.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("examples/galley_1000.json"),
        help="Manifest JSON to read dimensions/material contract from.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("examples/assets/candidates/galley_1000_candidate.glb"),
        help="Output candidate GLB path.",
    )
    return parser.parse_args(_argv_after_blender_separator())


def _load_manifest(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"manifest does not exist: {path}")
    with path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    if manifest.get("anchor") != "floor_back_left":
        raise SystemExit("candidate generator supports only floor_back_left anchor")
    return manifest


def _clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def _material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled is not None:
        principled.inputs["Base Color"].default_value = color
        principled.inputs["Roughness"].default_value = 0.72
        if name == "sink_metal":
            principled.inputs["Metallic"].default_value = 0.8
            principled.inputs["Roughness"].default_value = 0.36
        if color[3] < 1.0:
            principled.inputs["Alpha"].default_value = color[3]
            material.blend_method = "BLEND"
            material.use_screen_refraction = True
    material.diffuse_color = color
    return material


def _make_box(
    name: str,
    min_xyz: tuple[float, float, float],
    max_xyz: tuple[float, float, float],
    material: bpy.types.Material,
) -> bpy.types.Object:
    min_x, min_y, min_z = min_xyz
    max_x, max_y, max_z = max_xyz
    verts = [
        (min_x, min_y, min_z),
        (max_x, min_y, min_z),
        (max_x, max_y, min_z),
        (min_x, max_y, min_z),
        (min_x, min_y, max_z),
        (max_x, min_y, max_z),
        (max_x, max_y, max_z),
        (min_x, max_y, max_z),
    ]
    faces = [
        (0, 3, 2, 1),  # bottom
        (4, 5, 6, 7),  # top
        (0, 1, 5, 4),  # front, y=min
        (3, 7, 6, 2),  # rear, y=max
        (0, 4, 7, 3),  # left
        (1, 2, 6, 5),  # right
    ]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.material_index = 0
    return obj


def _build_candidate(manifest: dict) -> None:
    dims = manifest.get("dimensions_mm") or {}
    width = int(dims["width"]) / 1000.0
    depth = int(dims["depth"]) / 1000.0
    height = int(dims["height"]) / 1000.0

    slots = tuple((manifest.get("visual") or {}).get("material_slots") or ())
    missing = [slot for slot in REQUIRED_MATERIALS if slot not in slots]
    if missing:
        raise SystemExit("manifest material slots missing: " + ", ".join(missing))
    collision_proxy = (manifest.get("visual") or {}).get("collision_proxy")
    if not collision_proxy:
        raise SystemExit("manifest visual.collision_proxy is required")

    oak = _material("oak_body", (0.62, 0.42, 0.22, 1.0))
    metal = _material("sink_metal", (0.68, 0.70, 0.70, 1.0))
    proxy = _material("collision_proxy_transparent", (0.08, 0.22, 0.9, 0.035))

    # Overall dimensions stay exactly 1000 x 520 x 900 mm. The visible body is
    # intentionally blockout-level: panels and a sink marker, no fine detail.
    _make_box("galley_1000_candidate_plinth", (0.0, 0.0, 0.0), (width, depth, 0.055), oak)
    _make_box(
        "galley_1000_candidate_carcass",
        (0.025, 0.028, 0.055),
        (width - 0.025, depth - 0.018, height - 0.060),
        oak,
    )
    sink_min_x, sink_max_x = 0.090, 0.390
    sink_min_y, sink_max_y = 0.095, 0.345
    _make_box(
        "galley_1000_candidate_countertop_left",
        (0.0, 0.0, height - 0.060),
        (sink_min_x, depth, height),
        oak,
    )
    _make_box(
        "galley_1000_candidate_countertop_right",
        (sink_max_x, 0.0, height - 0.060),
        (width, depth, height),
        oak,
    )
    _make_box(
        "galley_1000_candidate_countertop_front",
        (sink_min_x, 0.0, height - 0.060),
        (sink_max_x, sink_min_y, height),
        oak,
    )
    _make_box(
        "galley_1000_candidate_countertop_rear",
        (sink_min_x, sink_max_y, height - 0.060),
        (sink_max_x, depth, height),
        oak,
    )

    # Front panel blockout. Separate slabs create visible seams and reveal the
    # recessed carcass behind them in front/rear/three-quarter renders.
    panel_y = (0.0, 0.024)
    _make_box("galley_1000_candidate_left_door", (0.035, panel_y[0], 0.080), (0.485, panel_y[1], 0.805), oak)
    _make_box("galley_1000_candidate_drawer_front", (0.515, panel_y[0], 0.590), (0.965, panel_y[1], 0.805), oak)
    _make_box("galley_1000_candidate_right_door", (0.515, panel_y[0], 0.080), (0.965, panel_y[1], 0.560), oak)
    _make_box("galley_1000_candidate_center_seam", (0.490, panel_y[0], 0.080), (0.510, panel_y[1], 0.805), metal)
    _make_box("galley_1000_candidate_drawer_seam", (0.515, panel_y[0], 0.565), (0.965, panel_y[1], 0.585), metal)
    _make_box("galley_1000_candidate_countertop_front_seam", (0.0, panel_y[0], 0.830), (width, panel_y[1], 0.845), metal)

    # Sink marker sits flush with the countertop top plane and uses the
    # manifest's sink_metal slot, so it changes the visual read without
    # expanding the bounding box above 900 mm.
    _make_box(
        "galley_1000_candidate_sink_marker",
        (sink_min_x + 0.015, sink_min_y + 0.015, height - 0.030),
        (sink_max_x - 0.015, sink_max_y - 0.015, height - 0.002),
        metal,
    )

    collision = _make_box(collision_proxy, (0.0, 0.0, 0.0), (width, depth, height), proxy)
    collision.show_transparent = True
    collision.display_type = "WIRE"


def _export_glb(out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(out_path),
        export_format="GLB",
        export_yup=False,
        export_apply=True,
        export_animations=False,
        export_cameras=False,
        export_lights=False,
        export_materials="EXPORT",
    )


def main() -> int:
    args = _parse_args()
    manifest = _load_manifest(args.manifest)
    _clear_scene()
    _build_candidate(manifest)
    _export_glb(args.out)
    print(f"WROTE {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
