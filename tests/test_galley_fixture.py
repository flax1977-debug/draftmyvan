"""Tests for the committed galley_1000 GLB fixture and its generator.

These are the regression / determinism gates for the test-fixture asset:

  * The committed `examples/assets/galley_1000.glb` is byte-identical to
    what `tools/assets/generate_galley_fixture_glb.py` produces from the manifest.
    If someone hand-edits the binary, or changes the generator, this
    test fails immediately.
  * The committed fixture passes the full Blender-side validator
    (manifest, dimension, anchor/origin, material, and collision gates)
    end-to-end.
  * The generator refuses anchors it does not support.

No Blender required.
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "blender"))
sys.path.insert(0, str(REPO_ROOT / "tools" / "assets"))

import generate_galley_fixture_glb as gen  # noqa: E402
import validate_glb_against_manifest as v  # noqa: E402

SAMPLE_MANIFEST = REPO_ROOT / "examples" / "galley_1000.json"
FIXTURE_GLB = REPO_ROOT / "examples" / "assets" / "galley_1000.glb"


def _load_manifest() -> dict:
    with SAMPLE_MANIFEST.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_fixture_file_exists() -> None:
    assert FIXTURE_GLB.exists(), f"committed fixture missing: {FIXTURE_GLB}"


def test_committed_fixture_matches_generator_byte_for_byte() -> None:
    """If this fails, either the generator drifted or the fixture was hand-edited."""
    generated = gen.make_box_glb_from_manifest(_load_manifest())
    committed = FIXTURE_GLB.read_bytes()
    assert generated == committed, (
        "committed examples/assets/galley_1000.glb does not match the "
        "output of tools/assets/generate_galley_fixture_glb.py. Regenerate with: "
        "python tools/assets/generate_galley_fixture_glb.py"
    )


def test_committed_fixture_passes_full_validator() -> None:
    report = v.validate(
        manifest_path=SAMPLE_MANIFEST,
        glb_path=FIXTURE_GLB,
        tolerance_mm=1.0,
        glb_units="meters",
    )
    assert report.ok, "\n".join(report.messages)
    joined = "\n".join(report.messages)
    assert "RESULT: PASS" in joined


def test_committed_fixture_bbox_matches_manifest_exactly() -> None:
    bbox = v.load_glb_bbox(FIXTURE_GLB).scaled(1000.0)  # m → mm
    w, d, h = bbox.size_xyz
    assert (round(w, 6), round(d, 6), round(h, 6)) == (1000.0, 520.0, 900.0)
    assert (round(bbox.min_x, 6), round(bbox.min_y, 6), round(bbox.min_z, 6)) == (0.0, 0.0, 0.0)


def test_committed_fixture_declares_material_slots_and_collision_proxy() -> None:
    gltf = v.load_glb_json(FIXTURE_GLB)
    manifest = _load_manifest()
    assert v.glb_material_names(gltf) == set(manifest["visual"]["material_slots"])
    assert manifest["visual"]["collision_proxy"] in v.glb_node_mesh_names(gltf)


def test_generator_refuses_unsupported_anchor() -> None:
    manifest = _load_manifest()
    manifest["anchor"] = "wall_left_back"
    try:
        gen.make_box_glb_from_manifest(manifest)
    except ValueError as e:
        assert "wall_left_back" in str(e)
        return
    raise AssertionError("generator should refuse unsupported anchor")


def test_generator_refuses_missing_dimensions() -> None:
    manifest = _load_manifest()
    del manifest["dimensions_mm"]
    try:
        gen.make_box_glb_from_manifest(manifest)
    except ValueError as e:
        assert "dimensions_mm" in str(e)
        return
    raise AssertionError("generator should refuse manifest without dimensions_mm")


def test_generator_refuses_missing_material_slots() -> None:
    manifest = _load_manifest()
    del manifest["visual"]["material_slots"]
    try:
        gen.make_box_glb_from_manifest(manifest)
    except ValueError as e:
        assert "material_slots" in str(e)
        return
    raise AssertionError("generator should refuse manifest without material slots")


def test_generator_refuses_missing_collision_proxy() -> None:
    manifest = _load_manifest()
    del manifest["visual"]["collision_proxy"]
    try:
        gen.make_box_glb_from_manifest(manifest)
    except ValueError as e:
        assert "collision_proxy" in str(e)
        return
    raise AssertionError("generator should refuse manifest without collision proxy")


def test_generator_is_deterministic_across_repeated_calls() -> None:
    manifest = _load_manifest()
    a = gen.make_box_glb_from_manifest(manifest)
    b = gen.make_box_glb_from_manifest(copy.deepcopy(manifest))
    assert a == b, "repeated generator calls must produce identical bytes"


def test_generated_glb_for_different_dims_still_passes_anchor_check() -> None:
    """The generator is dimension-driven; any sane dims should produce a passing GLB."""
    manifest = _load_manifest()
    manifest["dimensions_mm"] = {"width": 800, "depth": 400, "height": 600}
    blob = gen.make_box_glb_from_manifest(manifest)
    with tempfile.TemporaryDirectory() as td:
        glb_path = Path(td) / "galley_1000.glb"
        glb_path.write_bytes(blob)
        # Write a temp manifest with matching dims to validate against.
        manifest_path = Path(td) / "manifest.json"
        with manifest_path.open("w", encoding="utf-8") as f:
            json.dump(manifest, f)
        report = v.validate(
            manifest_path=manifest_path,
            glb_path=glb_path,
            tolerance_mm=1.0,
            glb_units="meters",
        )
        assert report.ok, "\n".join(report.messages)


def main() -> int:
    tests = [
        test_fixture_file_exists,
        test_committed_fixture_matches_generator_byte_for_byte,
        test_committed_fixture_passes_full_validator,
        test_committed_fixture_bbox_matches_manifest_exactly,
        test_committed_fixture_declares_material_slots_and_collision_proxy,
        test_generator_refuses_unsupported_anchor,
        test_generator_refuses_missing_dimensions,
        test_generator_refuses_missing_material_slots,
        test_generator_refuses_missing_collision_proxy,
        test_generator_is_deterministic_across_repeated_calls,
        test_generated_glb_for_different_dims_still_passes_anchor_check,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"ERROR {t.__name__}: {e}")
    print()
    print(f"{len(tests) - failed}/{len(tests)} passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
