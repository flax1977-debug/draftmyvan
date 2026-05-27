"""Blender-side variant of the manifest-vs-GLB validator.

Runs inside Blender (uses `bpy`) so the bounding box comes from the
imported scene graph, not just the glTF accessor extents. Use this when:

  * The asset has non-identity node transforms.
  * You suspect the exporter wrote stale or wrong accessor min/max.
  * You want the authoritative answer before pushing a new GLB.

Invoke from a shell (Blender must be on PATH):

    blender --background --python \\
        tools/blender/validate_in_blender.py -- \\
        --manifest examples/galley_1000.json \\
        --glb path/to/galley_1000.glb \\
        [--tolerance-mm 1.0]

Note the bare `--` between Blender's args and ours; Blender forwards
everything after it to `sys.argv`.

Exit codes mirror the pure-Python validator (0 pass, 1 fail, 2 error).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Allow `import _anchor_contract` when invoked as
#   blender --background --python tools/blender/validate_in_blender.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _anchor_contract import check_origin_anchor  # noqa: E402
import validate_glb_against_manifest as pure  # noqa: E402


def _split_argv() -> list[str]:
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1:]
    return []


def _load_manifest(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"ERROR (manifest): not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _world_bbox_mm():
    """Union AABB of every mesh object in the active scene, in millimetres.

    Blender's default unit is metres; we multiply by 1000 to land in mm.
    """
    import bpy  # type: ignore  # available only inside Blender

    big = float("inf")
    bbox_min = [big, big, big]
    bbox_max = [-big, -big, -big]
    saw_mesh = False
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        saw_mesh = True
        for corner in obj.bound_box:
            world = obj.matrix_world @ __import__("mathutils").Vector(corner)
            for i in range(3):
                if world[i] < bbox_min[i]:
                    bbox_min[i] = world[i]
                if world[i] > bbox_max[i]:
                    bbox_max[i] = world[i]
    if not saw_mesh:
        raise SystemExit("ERROR (glb): imported scene contains no mesh objects")
    return [v * 1000.0 for v in bbox_min], [v * 1000.0 for v in bbox_max]


def _material_names() -> set[str]:
    import bpy  # type: ignore  # available only inside Blender

    return {m.name for m in bpy.data.materials}


def _object_mesh_names() -> set[str]:
    import bpy  # type: ignore  # available only inside Blender

    names: set[str] = set()
    for obj in bpy.context.scene.objects:
        names.add(obj.name)
        data = getattr(obj, "data", None)
        if data is not None:
            names.add(data.name)
    return names


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--glb", required=True, type=Path)
    parser.add_argument("--tolerance-mm", type=float, default=1.0)
    args = parser.parse_args(_split_argv())

    manifest = _load_manifest(args.manifest)
    dims = manifest.get("dimensions_mm") or {}
    try:
        expected = (int(dims["width"]), int(dims["depth"]), int(dims["height"]))
    except KeyError as e:
        raise SystemExit(f"ERROR (manifest): dimensions_mm missing {e}")
    anchor = manifest.get("anchor")
    if not isinstance(anchor, str):
        raise SystemExit("ERROR (manifest): missing required field 'anchor'")
    try:
        material_slots = pure.extract_manifest_material_slots(manifest)
        collision_proxy = pure.extract_manifest_collision_proxy(manifest)
    except pure.ManifestError as e:
        raise SystemExit(f"ERROR (manifest): {e}") from e

    import bpy  # type: ignore

    # Clean default scene then import the GLB.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if not args.glb.exists():
        raise SystemExit(f"ERROR (glb): file not found: {args.glb}")
    bpy.ops.import_scene.gltf(filepath=str(args.glb))

    mn, mx = _world_bbox_mm()
    actual_size = tuple(mx[i] - mn[i] for i in range(3))

    print(f"Manifest id:   {manifest.get('id', '?')}")
    print(f"Manifest dims: width={expected[0]} depth={expected[1]} height={expected[2]} (mm)")
    print(f"GLB bbox (mm): width={actual_size[0]:.3f} depth={actual_size[1]:.3f} height={actual_size[2]:.3f}")

    size_ok = True
    for name, a, e in zip(("width", "depth", "height"), actual_size, expected):
        delta = a - e
        marker = "OK" if abs(delta) <= args.tolerance_mm else "FAIL"
        print(f"  [{marker}] {name}: delta={delta:+.3f} mm (tol={args.tolerance_mm} mm)")
        if marker == "FAIL":
            size_ok = False

    print(f"Anchor enforcement (anchor={anchor!r}):")
    anchor_ok, anchor_lines = check_origin_anchor(
        (mn[0], mn[1], mn[2]),
        (mx[0], mx[1], mx[2]),
        expected,
        anchor,
        args.tolerance_mm,
    )
    for line in anchor_lines:
        print(line)

    print("Material slot check:")
    material_ok, material_lines = pure.check_material_slots(
        _material_names(), material_slots
    )
    for line in material_lines:
        print(line)

    print("Collision proxy check:")
    collision_ok, collision_lines = pure.check_collision_proxy(
        _object_mesh_names(), collision_proxy
    )
    for line in collision_lines:
        print(line)

    ok = size_ok and anchor_ok and material_ok and collision_ok
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
