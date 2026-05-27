#!/usr/bin/env python3
"""Render repeatable local views for a candidate GLB.

Run inside Blender:

    blender --background --python tools/blender/render_candidate_views.py -- \
      --candidate examples/assets/candidates/galley_1000_candidate.glb \
      --out examples/assets/candidates/render_evidence/galley_1000_candidate/

The generated PNGs are local visual-review evidence. They are intentionally
not required by CI and are ignored unless a future PR decides to commit them.
The script orients the imported GLB contract axes for Blender review and hides
`UCX_` collision proxy meshes from the rendered views.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

try:
    import bpy
    from mathutils import Matrix
    from mathutils import Vector
except ImportError as e:  # pragma: no cover - this script is run inside Blender.
    raise SystemExit("render_candidate_views.py must be run inside Blender") from e


VIEWS = ("front", "rear", "left", "right", "top", "three_quarter")


def _argv_after_blender_separator() -> list[str]:
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1 :]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render repeatable PNG views for a DraftMyVan candidate GLB.",
    )
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--views",
        nargs="+",
        default=list(VIEWS),
        choices=VIEWS,
        help="Views to render. Defaults to all six audit views.",
    )
    parser.add_argument("--resolution", type=int, default=1024)
    return parser.parse_args(_argv_after_blender_separator())


def _clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def _import_glb(path: Path) -> list[bpy.types.Object]:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    mesh_objects = [obj for obj in imported if obj.type == "MESH"]
    if not mesh_objects:
        raise RuntimeError(f"no mesh objects imported from {path}")
    return mesh_objects


def _world_bbox(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points: list[Vector] = []
    for obj in objects:
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))
    if not points:
        raise RuntimeError("cannot compute bounds for empty object list")
    min_v = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    max_v = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return min_v, max_v


def _orient_contract_axes_for_review(objects: list[bpy.types.Object]) -> None:
    """Display glTF contract axes as Blender Z-up for visual review only."""
    rotation = Matrix.Rotation(-math.pi / 2.0, 4, "X")
    for obj in objects:
        obj.matrix_world = rotation @ obj.matrix_world
    bpy.context.view_layer.update()


def _hide_collision_proxies(objects: list[bpy.types.Object]) -> None:
    for obj in objects:
        data_name = getattr(getattr(obj, "data", None), "name", "")
        if obj.name.startswith("UCX_") or data_name.startswith("UCX_"):
            obj.hide_render = True
            obj.hide_set(True)


def _look_at(camera: bpy.types.Object, target: Vector) -> None:
    direction = target - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _setup_camera_and_light(center: Vector, size: Vector, resolution: int) -> bpy.types.Object:
    bpy.context.scene.render.resolution_x = resolution
    bpy.context.scene.render.resolution_y = resolution
    bpy.context.scene.render.film_transparent = False
    bpy.context.scene.render.image_settings.file_format = "PNG"

    try:
        bpy.context.scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass

    camera_data = bpy.data.cameras.new("audit_camera")
    camera = bpy.data.objects.new("audit_camera", camera_data)
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    camera.data.lens = 55

    light_data = bpy.data.lights.new("audit_key_light", type="AREA")
    light = bpy.data.objects.new("audit_key_light", light_data)
    bpy.context.collection.objects.link(light)
    light.location = center + Vector((-size.x, -size.y, size.z * 2.5))
    light.data.energy = 450
    light.data.size = max(size.x, size.y, size.z, 1.0)
    return camera


def _camera_location(view: str, center: Vector, size: Vector) -> Vector:
    span = max(size.x, size.y, size.z, 1.0)
    distance = span * 2.8
    height = max(size.z * 0.35, span * 0.25)
    locations = {
        "front": center + Vector((0, -distance, height)),
        "rear": center + Vector((0, distance, height)),
        "left": center + Vector((-distance, 0, height)),
        "right": center + Vector((distance, 0, height)),
        "top": center + Vector((0, 0, distance)),
        "three_quarter": center + Vector((-distance, -distance, distance * 0.75)),
    }
    return locations[view]


def _render_views(
    camera: bpy.types.Object,
    views: list[str],
    out_dir: Path,
    center: Vector,
    size: Vector,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for view in views:
        camera.location = _camera_location(view, center, size)
        _look_at(camera, center)
        out_path = out_dir / f"{view}.png"
        bpy.context.scene.render.filepath = str(out_path)
        bpy.ops.render.render(write_still=True)
        print(f"WROTE {out_path}")


def main() -> int:
    args = _parse_args()
    candidate = args.candidate.resolve()
    out_dir = args.out.resolve()
    if not candidate.is_file():
        raise SystemExit(f"candidate does not exist: {candidate}")

    _clear_scene()
    objects = _import_glb(candidate)
    _orient_contract_axes_for_review(objects)
    min_v, max_v = _world_bbox(objects)
    _hide_collision_proxies(objects)
    center = (min_v + max_v) / 2.0
    size = max_v - min_v
    camera = _setup_camera_and_light(center, size, args.resolution)
    _render_views(camera, args.views, out_dir, center, size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
