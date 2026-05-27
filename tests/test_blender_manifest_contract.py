"""Tests for the pure-Python parts of the Blender-side manifest validator.

Run from the draftmyvan/ directory:
    python -m tests.test_blender_manifest_contract

These tests never launch Blender. They exercise:
  * argparse construction
  * manifest loading + dimension extraction
  * GLB header parsing (against a synthetic minimal GLB built in-memory)
  * tolerance comparison (within / outside)
  * error messages for missing manifest fields and missing GLB file
  * .glb extension enforcement on visual.glb_path
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import struct
import sys
import tempfile
from pathlib import Path

# Make tools/blender importable.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "blender"))

import validate_glb_against_manifest as v  # noqa: E402

SAMPLE_MANIFEST = REPO_ROOT / "examples" / "galley_1000.json"


# ---------------------------------------------------------------------------
# Synthetic GLB builder
# ---------------------------------------------------------------------------

def _build_glb(min_xyz: tuple[float, float, float],
               max_xyz: tuple[float, float, float],
               *,
               omit_min_max: bool = False,
               bad_magic: bool = False,
               wrong_version: bool = False,
               no_position: bool = False,
               material_names: tuple[str, ...] = ("oak_body", "sink_metal"),
               collision_proxy: str | None = "UCX_galley_1000") -> bytes:
    """Hand-build a minimal valid GLB 2.0 file for parser testing."""
    accessor: dict = {
        "bufferView": 0,
        "componentType": 5126,
        "count": 1,
        "type": "VEC3",
    }
    if not omit_min_max:
        accessor["min"] = list(min_xyz)
        accessor["max"] = list(max_xyz)

    primitive_attrs = {} if no_position else {"POSITION": 0}
    module_primitives = [
        {"attributes": primitive_attrs, "material": i}
        for i, _ in enumerate(material_names)
    ]
    if not module_primitives:
        module_primitives = [{"attributes": primitive_attrs}]
    nodes = [{"mesh": 0, "name": "galley_1000_sink_left_oak"}]
    meshes = [{"name": "galley_1000_sink_left_oak", "primitives": module_primitives}]
    if collision_proxy is not None:
        nodes.append({"mesh": 1, "name": collision_proxy})
        meshes.append({"name": collision_proxy, "primitives": [{"attributes": primitive_attrs}]})
    gltf = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": meshes,
        "materials": [{"name": name} for name in material_names],
        "accessors": [accessor],
        "bufferViews": [{"buffer": 0, "byteLength": 12, "byteOffset": 0}],
        "buffers": [{"byteLength": 12}],
    }
    json_bytes = json.dumps(gltf).encode("utf-8")
    json_pad = (4 - len(json_bytes) % 4) % 4
    json_bytes += b" " * json_pad

    bin_payload = b"\x00" * 12
    bin_pad = (4 - len(bin_payload) % 4) % 4
    bin_payload += b"\x00" * bin_pad

    json_chunk = struct.pack("<II", len(json_bytes), v.CHUNK_TYPE_JSON) + json_bytes
    bin_chunk = struct.pack("<II", len(bin_payload), v.CHUNK_TYPE_BIN) + bin_payload

    magic = b"XXXX" if bad_magic else v.GLB_MAGIC
    version = 99 if wrong_version else v.GLB_VERSION
    total_length = 12 + len(json_chunk) + len(bin_chunk)
    header = struct.pack("<4sII", magic, version, total_length)
    return header + json_chunk + bin_chunk


# ---------------------------------------------------------------------------
# argparse / config loading
# ---------------------------------------------------------------------------

def test_argparse_requires_manifest_and_glb() -> None:
    parser = v.build_parser()
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            parser.parse_args([])
    except SystemExit:
        return
    raise AssertionError("parser should reject empty args")


def test_argparse_defaults_are_sensible() -> None:
    parser = v.build_parser()
    args = parser.parse_args(["--manifest", "m.json", "--glb", "g.glb"])
    assert args.tolerance_mm == 1.0
    assert args.glb_units == "meters"
    assert args.ignore_path_mismatch is False


def test_argparse_rejects_unknown_units() -> None:
    parser = v.build_parser()
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            parser.parse_args(["--manifest", "m.json", "--glb", "g.glb",
                               "--glb-units", "furlongs"])
    except SystemExit:
        return
    raise AssertionError("parser should reject unknown --glb-units")


# ---------------------------------------------------------------------------
# Manifest extraction
# ---------------------------------------------------------------------------

def test_extract_dimensions_from_real_sample() -> None:
    manifest = v.load_manifest(SAMPLE_MANIFEST)
    assert v.extract_manifest_dimensions_mm(manifest) == (1000, 520, 900)


def test_extract_glb_path_from_real_sample() -> None:
    manifest = v.load_manifest(SAMPLE_MANIFEST)
    assert v.extract_manifest_glb_path(manifest) == "assets/galley_1000.glb"


def test_extract_material_slots_from_real_sample() -> None:
    manifest = v.load_manifest(SAMPLE_MANIFEST)
    assert v.extract_manifest_material_slots(manifest) == ("oak_body", "sink_metal")


def test_extract_collision_proxy_from_real_sample() -> None:
    manifest = v.load_manifest(SAMPLE_MANIFEST)
    assert v.extract_manifest_collision_proxy(manifest) == "UCX_galley_1000"


def test_missing_dimensions_field_gives_clear_error() -> None:
    manifest = v.load_manifest(SAMPLE_MANIFEST)
    broken = copy.deepcopy(manifest)
    del broken["dimensions_mm"]
    try:
        v.extract_manifest_dimensions_mm(broken)
    except v.ManifestError as e:
        assert "dimensions_mm" in str(e)
        return
    raise AssertionError("missing dimensions_mm should raise ManifestError")


def test_missing_single_dimension_key_names_the_key() -> None:
    manifest = v.load_manifest(SAMPLE_MANIFEST)
    broken = copy.deepcopy(manifest)
    del broken["dimensions_mm"]["height"]
    try:
        v.extract_manifest_dimensions_mm(broken)
    except v.ManifestError as e:
        assert "height" in str(e)
        return
    raise AssertionError("missing height should raise ManifestError naming it")


def test_missing_glb_path_field_gives_clear_error() -> None:
    manifest = v.load_manifest(SAMPLE_MANIFEST)
    broken = copy.deepcopy(manifest)
    del broken["visual"]["glb_path"]
    try:
        v.extract_manifest_glb_path(broken)
    except v.ManifestError as e:
        assert "glb_path" in str(e)
        return
    raise AssertionError("missing visual.glb_path should raise ManifestError")


def test_non_glb_extension_rejected_at_extraction() -> None:
    manifest = v.load_manifest(SAMPLE_MANIFEST)
    broken = copy.deepcopy(manifest)
    broken["visual"]["glb_path"] = "assets/galley_1000.fbx"
    try:
        v.extract_manifest_glb_path(broken)
    except v.ManifestError as e:
        assert ".glb" in str(e)
        return
    raise AssertionError(".fbx visual.glb_path should raise ManifestError")


def test_missing_material_slots_field_gives_clear_error() -> None:
    manifest = v.load_manifest(SAMPLE_MANIFEST)
    broken = copy.deepcopy(manifest)
    del broken["visual"]["material_slots"]
    try:
        v.extract_manifest_material_slots(broken)
    except v.ManifestError as e:
        assert "material_slots" in str(e)
        return
    raise AssertionError("missing visual.material_slots should raise ManifestError")


def test_missing_collision_proxy_field_gives_clear_error() -> None:
    manifest = v.load_manifest(SAMPLE_MANIFEST)
    broken = copy.deepcopy(manifest)
    del broken["visual"]["collision_proxy"]
    try:
        v.extract_manifest_collision_proxy(broken)
    except v.ManifestError as e:
        assert "collision_proxy" in str(e)
        return
    raise AssertionError("missing visual.collision_proxy should raise ManifestError")


def test_load_manifest_missing_file_raises() -> None:
    try:
        v.load_manifest(Path("/nope/does/not/exist.json"))
    except v.ManifestError as e:
        assert "not found" in str(e)
        return
    raise AssertionError("missing manifest file should raise ManifestError")


# ---------------------------------------------------------------------------
# GLB parsing
# ---------------------------------------------------------------------------

def test_parse_glb_bbox_returns_accessor_extents() -> None:
    # 1000mm x 520mm x 900mm in metres = (1.0, 0.52, 0.9)
    blob = _build_glb((0.0, 0.0, 0.0), (1.0, 0.52, 0.9))
    bbox = v.parse_glb_bbox(blob)
    assert bbox.size_xyz == (1.0, 0.52, 0.9)


def test_parse_glb_bbox_rejects_bad_magic() -> None:
    blob = _build_glb((0, 0, 0), (1, 1, 1), bad_magic=True)
    try:
        v.parse_glb_bbox(blob)
    except v.GlbParseError as e:
        assert "magic" in str(e)
        return
    raise AssertionError("bad magic should raise GlbParseError")


def test_parse_glb_bbox_rejects_wrong_version() -> None:
    blob = _build_glb((0, 0, 0), (1, 1, 1), wrong_version=True)
    try:
        v.parse_glb_bbox(blob)
    except v.GlbParseError as e:
        assert "version" in str(e)
        return
    raise AssertionError("wrong version should raise GlbParseError")


def test_parse_glb_bbox_rejects_missing_position_accessor() -> None:
    blob = _build_glb((0, 0, 0), (1, 1, 1), no_position=True)
    try:
        v.parse_glb_bbox(blob)
    except v.GlbParseError as e:
        assert "POSITION" in str(e)
        return
    raise AssertionError("no POSITION should raise GlbParseError")


def test_parse_glb_bbox_rejects_accessor_without_min_max() -> None:
    blob = _build_glb((0, 0, 0), (1, 1, 1), omit_min_max=True)
    try:
        v.parse_glb_bbox(blob)
    except v.GlbParseError as e:
        assert "min/max" in str(e)
        return
    raise AssertionError("accessor without min/max should raise GlbParseError")


def test_load_glb_bbox_missing_file_raises() -> None:
    try:
        v.load_glb_bbox(Path("/nope/does/not/exist.glb"))
    except v.GlbParseError as e:
        assert "not found" in str(e)
        return
    raise AssertionError("missing GLB file should raise GlbParseError")


def test_glb_material_names_reads_material_names() -> None:
    blob = _build_glb((0, 0, 0), (1, 1, 1))
    gltf = v.parse_glb_json(blob)
    assert v.glb_material_names(gltf) == {"oak_body", "sink_metal"}


def test_glb_node_mesh_names_reads_collision_proxy_names() -> None:
    blob = _build_glb((0, 0, 0), (1, 1, 1))
    gltf = v.parse_glb_json(blob)
    assert "UCX_galley_1000" in v.glb_node_mesh_names(gltf)


# ---------------------------------------------------------------------------
# Tolerance comparison
# ---------------------------------------------------------------------------

def test_compare_within_tolerance_passes() -> None:
    bbox = v.BBox(0, 0, 0, 1000.5, 520.0, 900.0)  # already mm
    ok, _ = v.compare(bbox, (1000, 520, 900), tolerance_mm=1.0)
    assert ok is True


def test_compare_outside_tolerance_fails() -> None:
    bbox = v.BBox(0, 0, 0, 1005.0, 520.0, 900.0)
    ok, lines = v.compare(bbox, (1000, 520, 900), tolerance_mm=1.0)
    assert ok is False
    assert any("FAIL" in line and "width" in line for line in lines)


def test_compare_reports_each_axis() -> None:
    bbox = v.BBox(0, 0, 0, 1000.0, 520.0, 900.0)
    _, lines = v.compare(bbox, (1000, 520, 900), tolerance_mm=1.0)
    joined = "\n".join(lines)
    for axis in ("width", "depth", "height"):
        assert axis in joined


# ---------------------------------------------------------------------------
# End-to-end (using a synthetic GLB written to a temp file)
# ---------------------------------------------------------------------------

def test_validate_full_path_passes_for_matching_glb() -> None:
    blob = _build_glb((0.0, 0.0, 0.0), (1.0, 0.52, 0.9))
    with tempfile.TemporaryDirectory() as td:
        glb_path = Path(td) / "galley_1000.glb"
        glb_path.write_bytes(blob)
        report = v.validate(
            manifest_path=SAMPLE_MANIFEST,
            glb_path=glb_path,
            tolerance_mm=1.0,
            glb_units="meters",
        )
        assert report.ok is True, "\n".join(report.messages)


def test_validate_full_path_fails_for_drift_outside_tolerance() -> None:
    # 1005 mm wide instead of 1000 mm.
    blob = _build_glb((0.0, 0.0, 0.0), (1.005, 0.52, 0.9))
    with tempfile.TemporaryDirectory() as td:
        glb_path = Path(td) / "galley_1000.glb"
        glb_path.write_bytes(blob)
        report = v.validate(
            manifest_path=SAMPLE_MANIFEST,
            glb_path=glb_path,
            tolerance_mm=1.0,
            glb_units="meters",
        )
        assert report.ok is False


def test_validate_full_path_fails_on_basename_mismatch() -> None:
    blob = _build_glb((0.0, 0.0, 0.0), (1.0, 0.52, 0.9))
    with tempfile.TemporaryDirectory() as td:
        glb_path = Path(td) / "wrong_name.glb"
        glb_path.write_bytes(blob)
        report = v.validate(
            manifest_path=SAMPLE_MANIFEST,
            glb_path=glb_path,
            tolerance_mm=1.0,
            glb_units="meters",
        )
        assert report.ok is False
        assert any("basename" in m for m in report.messages)


def test_validate_full_path_allows_basename_override() -> None:
    blob = _build_glb((0.0, 0.0, 0.0), (1.0, 0.52, 0.9))
    with tempfile.TemporaryDirectory() as td:
        glb_path = Path(td) / "wrong_name.glb"
        glb_path.write_bytes(blob)
        report = v.validate(
            manifest_path=SAMPLE_MANIFEST,
            glb_path=glb_path,
            tolerance_mm=1.0,
            glb_units="meters",
            ignore_path_mismatch=True,
        )
        assert report.ok is True


def test_validate_full_path_fails_when_material_slot_missing() -> None:
    blob = _build_glb(
        (0.0, 0.0, 0.0),
        (1.0, 0.52, 0.9),
        material_names=("oak_body",),
    )
    with tempfile.TemporaryDirectory() as td:
        glb_path = Path(td) / "galley_1000.glb"
        glb_path.write_bytes(blob)
        report = v.validate(
            manifest_path=SAMPLE_MANIFEST,
            glb_path=glb_path,
            tolerance_mm=1.0,
            glb_units="meters",
        )
        assert report.ok is False
        joined = "\n".join(report.messages)
        assert "[OK] material slot 'oak_body'" in joined
        assert "[FAIL] missing material slot 'sink_metal'" in joined
        assert "material slot contract is incomplete" in joined


def test_validate_full_path_fails_when_collision_proxy_missing() -> None:
    blob = _build_glb(
        (0.0, 0.0, 0.0),
        (1.0, 0.52, 0.9),
        collision_proxy=None,
    )
    with tempfile.TemporaryDirectory() as td:
        glb_path = Path(td) / "galley_1000.glb"
        glb_path.write_bytes(blob)
        report = v.validate(
            manifest_path=SAMPLE_MANIFEST,
            glb_path=glb_path,
            tolerance_mm=1.0,
            glb_units="meters",
        )
        assert report.ok is False
        joined = "\n".join(report.messages)
        assert "[FAIL] missing collision proxy 'UCX_galley_1000'" in joined
        assert "collision proxy contract is incomplete" in joined


# ---------------------------------------------------------------------------
# Origin / anchor enforcement (PR #5)
# ---------------------------------------------------------------------------

import _anchor_contract as ac  # noqa: E402


def _temp_manifest_with_anchor(anchor_value: str) -> Path:
    """Write a temp copy of galley_1000.json with anchor swapped, return its path."""
    src = v.load_manifest(SAMPLE_MANIFEST)
    src["anchor"] = anchor_value
    fd, tmp_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(src, f)
    return Path(tmp_path)


def test_anchor_floor_back_left_passes_when_bbox_min_at_origin() -> None:
    blob = _build_glb((0.0, 0.0, 0.0), (1.0, 0.52, 0.9))
    with tempfile.TemporaryDirectory() as td:
        glb_path = Path(td) / "galley_1000.glb"
        glb_path.write_bytes(blob)
        report = v.validate(
            manifest_path=SAMPLE_MANIFEST,
            glb_path=glb_path,
            tolerance_mm=1.0,
            glb_units="meters",
        )
        assert report.ok is True, "\n".join(report.messages)
        joined = "\n".join(report.messages)
        assert "Anchor enforcement" in joined
        assert "[OK] min.x" in joined and "[OK] max.x" in joined


def test_anchor_floor_back_left_fails_when_bbox_shifted_in_positive_x() -> None:
    # Correct size 1.0 x 0.52 x 0.9 metres but shifted +0.1 m in X.
    blob = _build_glb((0.1, 0.0, 0.0), (1.1, 0.52, 0.9))
    with tempfile.TemporaryDirectory() as td:
        glb_path = Path(td) / "galley_1000.glb"
        glb_path.write_bytes(blob)
        report = v.validate(
            manifest_path=SAMPLE_MANIFEST,
            glb_path=glb_path,
            tolerance_mm=1.0,
            glb_units="meters",
        )
        assert report.ok is False
        joined = "\n".join(report.messages)
        # The size check should pass (it's still 1000 mm wide); only the
        # origin/anchor check should reject it.
        assert "RESULT: FAIL — origin/anchor alignment violates contract" in joined
        assert "[FAIL] min.x" in joined
        assert "[FAIL] max.x" in joined


def test_anchor_floor_back_left_fails_when_bbox_min_is_negative() -> None:
    # Centered on origin: min = (-0.5, -0.26, 0), max = (0.5, 0.26, 0.9).
    blob = _build_glb((-0.5, -0.26, 0.0), (0.5, 0.26, 0.9))
    with tempfile.TemporaryDirectory() as td:
        glb_path = Path(td) / "galley_1000.glb"
        glb_path.write_bytes(blob)
        report = v.validate(
            manifest_path=SAMPLE_MANIFEST,
            glb_path=glb_path,
            tolerance_mm=1.0,
            glb_units="meters",
        )
        assert report.ok is False
        joined = "\n".join(report.messages)
        assert "[FAIL] min.x" in joined
        assert "[FAIL] min.y" in joined


def test_anchor_unsupported_value_fails_clearly_even_if_geometry_is_correct() -> None:
    # Geometry would satisfy floor_back_left, but the manifest declares an
    # anchor we don't enforce yet — must fail loudly, not pass silently.
    manifest_path = _temp_manifest_with_anchor("ceiling_back_right")
    try:
        blob = _build_glb((0.0, 0.0, 0.0), (1.0, 0.52, 0.9))
        with tempfile.TemporaryDirectory() as td:
            glb_path = Path(td) / "galley_1000.glb"
            glb_path.write_bytes(blob)
            report = v.validate(
                manifest_path=manifest_path,
                glb_path=glb_path,
                tolerance_mm=1.0,
                glb_units="meters",
            )
            assert report.ok is False
            joined = "\n".join(report.messages)
            assert "anchor enforcement not implemented for 'ceiling_back_right'" in joined
    finally:
        manifest_path.unlink(missing_ok=True)


def test_dimension_mismatch_still_fails_after_anchor_check_added() -> None:
    # +5 mm width drift, anchor would otherwise match.
    blob = _build_glb((0.0, 0.0, 0.0), (1.005, 0.52, 0.9))
    with tempfile.TemporaryDirectory() as td:
        glb_path = Path(td) / "galley_1000.glb"
        glb_path.write_bytes(blob)
        report = v.validate(
            manifest_path=SAMPLE_MANIFEST,
            glb_path=glb_path,
            tolerance_mm=1.0,
            glb_units="meters",
        )
        assert report.ok is False
        joined = "\n".join(report.messages)
        assert "Dimension check:" in joined
        assert "[FAIL] width" in joined


def test_anchor_contract_unsupported_anchor_raises() -> None:
    try:
        ac.expected_corners_mm("wall_left_back", (1000, 520, 900))
    except ac.UnsupportedAnchorError as e:
        assert e.anchor == "wall_left_back"
        assert "not implemented" in str(e)
        return
    raise AssertionError("expected UnsupportedAnchorError for unsupported anchor")


def test_anchor_contract_expected_corners_for_floor_back_left() -> None:
    mn, mx = ac.expected_corners_mm("floor_back_left", (1000, 520, 900))
    assert mn == (0.0, 0.0, 0.0)
    assert mx == (1000.0, 520.0, 900.0)


def main() -> int:
    tests = [
        test_argparse_requires_manifest_and_glb,
        test_argparse_defaults_are_sensible,
        test_argparse_rejects_unknown_units,
        test_extract_dimensions_from_real_sample,
        test_extract_glb_path_from_real_sample,
        test_extract_material_slots_from_real_sample,
        test_extract_collision_proxy_from_real_sample,
        test_missing_dimensions_field_gives_clear_error,
        test_missing_single_dimension_key_names_the_key,
        test_missing_glb_path_field_gives_clear_error,
        test_non_glb_extension_rejected_at_extraction,
        test_missing_material_slots_field_gives_clear_error,
        test_missing_collision_proxy_field_gives_clear_error,
        test_load_manifest_missing_file_raises,
        test_parse_glb_bbox_returns_accessor_extents,
        test_parse_glb_bbox_rejects_bad_magic,
        test_parse_glb_bbox_rejects_wrong_version,
        test_parse_glb_bbox_rejects_missing_position_accessor,
        test_parse_glb_bbox_rejects_accessor_without_min_max,
        test_load_glb_bbox_missing_file_raises,
        test_glb_material_names_reads_material_names,
        test_glb_node_mesh_names_reads_collision_proxy_names,
        test_compare_within_tolerance_passes,
        test_compare_outside_tolerance_fails,
        test_compare_reports_each_axis,
        test_validate_full_path_passes_for_matching_glb,
        test_validate_full_path_fails_for_drift_outside_tolerance,
        test_validate_full_path_fails_on_basename_mismatch,
        test_validate_full_path_allows_basename_override,
        test_validate_full_path_fails_when_material_slot_missing,
        test_validate_full_path_fails_when_collision_proxy_missing,
        test_anchor_floor_back_left_passes_when_bbox_min_at_origin,
        test_anchor_floor_back_left_fails_when_bbox_shifted_in_positive_x,
        test_anchor_floor_back_left_fails_when_bbox_min_is_negative,
        test_anchor_unsupported_value_fails_clearly_even_if_geometry_is_correct,
        test_dimension_mismatch_still_fails_after_anchor_check_added,
        test_anchor_contract_unsupported_anchor_raises,
        test_anchor_contract_expected_corners_for_floor_back_left,
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
