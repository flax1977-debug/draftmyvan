"""Tests for the galley_1000 GLB fixtures and their generator.

Two GLB files participate in this test suite, with two distinct roles:

  1. The **golden contract fixture** at
     ``tests/fixtures/galley_1000_contract_box.glb``.
     Permanent regression reference. Pinned byte-for-byte to the
     output of ``tools/assets/generate_galley_fixture_glb.py``. Never
     replaced by real cabinet art — when real art lands in the manifest
     asset slot (file 2), the golden fixture stays exactly as it is.

  2. The **current manifest asset** at
     ``examples/assets/galley_1000.glb``.
     This is what ``examples/galley_1000.json`` actually points at.
     Today it is the same generated box bytes; tomorrow it may be real
     art. We test that it always **validates** end-to-end, and — while
     the acceptance metadata says ``generated_fixture_replaced: false``
     — that its bytes still equal the golden fixture's.

The generator's anchor / dimension / material / collision-proxy
contract is exercised against in-memory bytes (no file output), so those
tests stay agnostic to either committed location.

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

# Golden contract fixture — permanent regression reference.
GOLDEN_FIXTURE_GLB = REPO_ROOT / "tests" / "fixtures" / "galley_1000_contract_box.glb"

# Current manifest asset — what the manifest's visual.glb_path resolves to.
MANIFEST_ASSET_GLB = REPO_ROOT / "examples" / "assets" / "galley_1000.glb"

# Acceptance metadata — gates the "is the manifest asset still a
# generated fixture?" question.
ACCEPTANCE_METADATA = (
    REPO_ROOT / "examples" / "assets" / "galley_1000.asset_acceptance.json"
)


def _load_manifest() -> dict:
    with SAMPLE_MANIFEST.open("r", encoding="utf-8") as f:
        return json.load(f)


def _generated_fixture_replaced() -> bool:
    """Read the acceptance flag. Absent metadata = treat as 'not replaced'."""
    if not ACCEPTANCE_METADATA.exists():
        return False
    with ACCEPTANCE_METADATA.open("r", encoding="utf-8") as f:
        return bool(json.load(f).get("generated_fixture_replaced", False))


# ---------------------------------------------------------------------------
# Golden contract fixture — permanent regression reference
# ---------------------------------------------------------------------------

def test_golden_fixture_file_exists() -> None:
    assert GOLDEN_FIXTURE_GLB.exists(), (
        f"golden contract fixture missing: {GOLDEN_FIXTURE_GLB}. "
        f"Regenerate with: python tools/assets/generate_galley_fixture_glb.py"
    )


def test_golden_fixture_matches_generator_byte_for_byte() -> None:
    """If this fails, either the generator drifted or the golden fixture
    was hand-edited. The golden fixture is permanent — to change its
    bytes, change the generator (or the source manifest), then
    regenerate. Never edit the binary."""
    generated = gen.make_box_glb_from_manifest(_load_manifest())
    committed = GOLDEN_FIXTURE_GLB.read_bytes()
    assert generated == committed, (
        "tests/fixtures/galley_1000_contract_box.glb does not match the "
        "output of tools/assets/generate_galley_fixture_glb.py. "
        "Regenerate with: python tools/assets/generate_galley_fixture_glb.py"
    )


def test_golden_fixture_passes_full_validator() -> None:
    report = v.validate(
        manifest_path=SAMPLE_MANIFEST,
        glb_path=GOLDEN_FIXTURE_GLB,
        tolerance_mm=1.0,
        glb_units="meters",
        ignore_path_mismatch=True,  # golden fixture basename != manifest's
    )
    assert report.ok, "\n".join(report.messages)
    joined = "\n".join(report.messages)
    assert "RESULT: PASS" in joined


def test_golden_fixture_bbox_matches_manifest_exactly() -> None:
    bbox = v.load_glb_bbox(GOLDEN_FIXTURE_GLB).scaled(1000.0)  # m → mm
    w, d, h = bbox.size_xyz
    assert (round(w, 6), round(d, 6), round(h, 6)) == (1000.0, 520.0, 900.0)
    assert (round(bbox.min_x, 6), round(bbox.min_y, 6), round(bbox.min_z, 6)) == (0.0, 0.0, 0.0)


def test_golden_fixture_declares_material_slots_and_collision_proxy() -> None:
    gltf = v.load_glb_json(GOLDEN_FIXTURE_GLB)
    manifest = _load_manifest()
    assert v.glb_material_names(gltf) == set(manifest["visual"]["material_slots"])
    assert manifest["visual"]["collision_proxy"] in v.glb_node_mesh_names(gltf)


# ---------------------------------------------------------------------------
# Current manifest asset — must validate; today must also equal golden
# ---------------------------------------------------------------------------

def test_manifest_asset_file_exists() -> None:
    assert MANIFEST_ASSET_GLB.exists(), (
        f"manifest asset missing: {MANIFEST_ASSET_GLB}"
    )


def test_manifest_asset_validates_against_manifest() -> None:
    """This holds whether the manifest asset is still the generated box
    or has been replaced with real cabinet art — validation is the
    contract the asset must satisfy in either world."""
    report = v.validate(
        manifest_path=SAMPLE_MANIFEST,
        glb_path=MANIFEST_ASSET_GLB,
        tolerance_mm=1.0,
        glb_units="meters",
    )
    assert report.ok, "\n".join(report.messages)


def test_manifest_asset_equals_golden_while_fixture_not_replaced() -> None:
    """While the acceptance metadata declares
    ``generated_fixture_replaced: false``, the manifest asset must
    still be byte-identical to the golden fixture. The day real cabinet
    art lands the flag flips and this assertion is bypassed — but the
    golden fixture continues to exist as a separate permanent
    reference."""
    if _generated_fixture_replaced():
        return  # real art is in place; manifest asset bytes are not pinned
    assert MANIFEST_ASSET_GLB.read_bytes() == GOLDEN_FIXTURE_GLB.read_bytes(), (
        "manifest asset and golden contract fixture have drifted while "
        "the acceptance metadata still declares "
        "generated_fixture_replaced=false. Regenerate both with: "
        "python tools/assets/generate_galley_fixture_glb.py"
    )


# ---------------------------------------------------------------------------
# Generator contract — exercised against in-memory bytes
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Fixture-swap safety — the generator must not overwrite real art
# ---------------------------------------------------------------------------

def test_generator_skips_manifest_asset_when_metadata_says_replaced(tmp_path: Path | None = None) -> None:
    """If acceptance metadata declares ``generated_fixture_replaced=true``,
    the generator's default invocation must NOT overwrite the manifest
    asset. This is the safety net that keeps a future real-art GLB
    from being silently erased by ``python tools/assets/generate_galley_fixture_glb.py``.
    """
    tmp = Path(tempfile.mkdtemp(prefix="dmv_fixture_swap_"))
    try:
        meta = tmp / "metadata.json"
        meta.write_text(json.dumps({"generated_fixture_replaced": True}), encoding="utf-8")
        assert gen._manifest_asset_is_real_art(meta) is True

        meta.write_text(json.dumps({"generated_fixture_replaced": False}), encoding="utf-8")
        assert gen._manifest_asset_is_real_art(meta) is False

        meta_missing = tmp / "nope.json"
        assert gen._manifest_asset_is_real_art(meta_missing) is False
    finally:
        import shutil
        shutil.rmtree(tmp)


def test_default_constants_point_to_canonical_paths() -> None:
    # Names matter — these are the contract for the canonical defaults.
    assert gen.DEFAULT_GOLDEN_FIXTURE == GOLDEN_FIXTURE_GLB
    assert gen.DEFAULT_MANIFEST_ASSET == MANIFEST_ASSET_GLB
    assert gen.DEFAULT_ACCEPTANCE_METADATA == ACCEPTANCE_METADATA


def main() -> int:
    tests = [
        test_golden_fixture_file_exists,
        test_golden_fixture_matches_generator_byte_for_byte,
        test_golden_fixture_passes_full_validator,
        test_golden_fixture_bbox_matches_manifest_exactly,
        test_golden_fixture_declares_material_slots_and_collision_proxy,
        test_manifest_asset_file_exists,
        test_manifest_asset_validates_against_manifest,
        test_manifest_asset_equals_golden_while_fixture_not_replaced,
        test_generator_refuses_unsupported_anchor,
        test_generator_refuses_missing_dimensions,
        test_generator_refuses_missing_material_slots,
        test_generator_refuses_missing_collision_proxy,
        test_generator_is_deterministic_across_repeated_calls,
        test_generated_glb_for_different_dims_still_passes_anchor_check,
        test_generator_skips_manifest_asset_when_metadata_says_replaced,
        test_default_constants_point_to_canonical_paths,
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
