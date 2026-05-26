"""Tests for the DraftMyVan runtime consumer (draftmyvan/runtime/).

Pure Python only — no Blender, no UE5.

These exercise the consumer as a **reader of an already-validated manifest**:
  * the happy path (galley_1000.json loads, fixture exists);
  * field typing (dimensions are ints, not strings);
  * GLB-path resolution (manifest's `assets/foo.glb` → on-disk
    `examples/assets/foo.glb`);
  * missing-asset → NOT CONSUMABLE (no crash);
  * malformed manifest → ConsumerError / exit 2 (clear message);
  * CLI output matches the documented shape.
"""

from __future__ import annotations

import copy
import io
import json
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from runtime import load_module as lm  # noqa: E402
from runtime.module import Dimensions, Module  # noqa: E402

SAMPLE_MANIFEST = REPO_ROOT / "examples" / "galley_1000.json"
FIXTURE_GLB = REPO_ROOT / "examples" / "assets" / "galley_1000.glb"


def _load_sample() -> dict:
    with SAMPLE_MANIFEST.open("r", encoding="utf-8") as f:
        return json.load(f)


def _temp_manifest(mutator) -> Path:
    src = _load_sample()
    mutator(src)
    fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="manifest_")
    Path(tmp_path).write_text(json.dumps(src), encoding="utf-8")
    return Path(tmp_path)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_sample_manifest_loads_to_typed_module() -> None:
    module = lm.load_module(SAMPLE_MANIFEST)
    assert isinstance(module, Module)
    assert module.id == "galley_1000_sink_left_oak"
    assert module.type == "cabinet"
    assert module.anchor == "floor_back_left"
    assert module.placement == "floor"
    assert module.glb_path == "assets/galley_1000.glb"


def test_dimensions_are_typed_integers_in_mm() -> None:
    module = lm.load_module(SAMPLE_MANIFEST)
    assert isinstance(module.dimensions, Dimensions)
    # Strict integer typing — no floats sneaking through.
    assert isinstance(module.dimensions.width_mm, int)
    assert isinstance(module.dimensions.depth_mm, int)
    assert isinstance(module.dimensions.height_mm, int)
    assert (module.dimensions.width_mm,
            module.dimensions.depth_mm,
            module.dimensions.height_mm) == (1000, 520, 900)


def test_metre_accessors_match_manifest_mm() -> None:
    module = lm.load_module(SAMPLE_MANIFEST)
    assert module.dimensions.width_m == 1.0
    assert module.dimensions.depth_m == 0.52
    assert module.dimensions.height_m == 0.9


def test_glb_path_resolves_to_committed_fixture() -> None:
    module = lm.load_module(SAMPLE_MANIFEST)
    assert module.resolved_asset_path == FIXTURE_GLB
    assert module.resolved_asset_path.exists()


def test_asset_exists_true_for_current_fixture() -> None:
    module = lm.load_module(SAMPLE_MANIFEST)
    assert module.asset_exists is True
    assert module.consumable is True


# ---------------------------------------------------------------------------
# Missing-asset path — does NOT crash, reports NOT CONSUMABLE
# ---------------------------------------------------------------------------

def test_missing_glb_loads_cleanly_with_asset_exists_false() -> None:
    # A temp manifest pointing at a real (schema-valid) glb_path that
    # happens not to exist on disk: load_module must succeed and report
    # asset_exists=False rather than raising.
    bad_manifest = _temp_manifest(
        lambda m: m["visual"].__setitem__("glb_path", "assets/ghost.glb")
    )
    try:
        module = lm.load_module(bad_manifest)
        assert module.asset_exists is False
        assert module.consumable is False
        assert module.glb_path == "assets/ghost.glb"
        assert module.resolved_asset_path.name == "ghost.glb"
    finally:
        bad_manifest.unlink(missing_ok=True)


def test_cli_missing_asset_returns_1_and_prints_not_consumable() -> None:
    bad_manifest = _temp_manifest(
        lambda m: m["visual"].__setitem__("glb_path", "assets/ghost.glb")
    )
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = lm.main([str(bad_manifest)])
        assert code == 1
        out = buf.getvalue()
        assert "RESULT: NOT CONSUMABLE" in out
        assert "ghost.glb" in out
    finally:
        bad_manifest.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Malformed-manifest paths — clear errors, exit 2
# ---------------------------------------------------------------------------

def test_missing_id_raises_clear_consumer_error() -> None:
    bad_manifest = _temp_manifest(lambda m: m.pop("id"))
    try:
        try:
            lm.load_module(bad_manifest)
        except lm.ConsumerError as e:
            assert "id" in str(e)
            return
        raise AssertionError("missing id should raise ConsumerError")
    finally:
        bad_manifest.unlink(missing_ok=True)


def test_missing_dimensions_field_raises() -> None:
    bad_manifest = _temp_manifest(lambda m: m.pop("dimensions_mm"))
    try:
        try:
            lm.load_module(bad_manifest)
        except lm.ConsumerError as e:
            assert "dimensions_mm" in str(e)
            return
        raise AssertionError("missing dimensions_mm should raise")
    finally:
        bad_manifest.unlink(missing_ok=True)


def test_missing_dimensions_subfield_names_the_subfield() -> None:
    bad_manifest = _temp_manifest(lambda m: m["dimensions_mm"].pop("height"))
    try:
        try:
            lm.load_module(bad_manifest)
        except lm.ConsumerError as e:
            assert "dimensions_mm.height" in str(e)
            return
        raise AssertionError("missing height should raise naming the path")
    finally:
        bad_manifest.unlink(missing_ok=True)


def test_missing_visual_glb_path_raises() -> None:
    bad_manifest = _temp_manifest(lambda m: m["visual"].pop("glb_path"))
    try:
        try:
            lm.load_module(bad_manifest)
        except lm.ConsumerError as e:
            assert "visual.glb_path" in str(e)
            return
        raise AssertionError("missing visual.glb_path should raise")
    finally:
        bad_manifest.unlink(missing_ok=True)


def test_non_glb_extension_raises() -> None:
    bad_manifest = _temp_manifest(
        lambda m: m["visual"].__setitem__("glb_path", "assets/wrong.fbx")
    )
    try:
        try:
            lm.load_module(bad_manifest)
        except lm.ConsumerError as e:
            assert ".glb" in str(e)
            return
        raise AssertionError(".fbx visual.glb_path should raise")
    finally:
        bad_manifest.unlink(missing_ok=True)


def test_fractional_dimensions_raise() -> None:
    bad_manifest = _temp_manifest(
        lambda m: m["dimensions_mm"].__setitem__("width", 1000.5)
    )
    try:
        try:
            lm.load_module(bad_manifest)
        except lm.ConsumerError as e:
            msg = str(e)
            assert "integer" in msg
            assert "width" in msg
            return
        raise AssertionError("fractional dimensions should raise — int(1000.5) silent truncation is unsafe")
    finally:
        bad_manifest.unlink(missing_ok=True)


def test_manifest_not_found_raises() -> None:
    try:
        lm.load_module(Path("/tmp/does_not_exist_manifest.json"))
    except lm.ConsumerError as e:
        assert "not found" in str(e)
        return
    raise AssertionError("missing manifest should raise ConsumerError")


def test_invalid_json_raises_with_helpful_message() -> None:
    fd, tmp_path = tempfile.mkstemp(suffix=".json")
    Path(tmp_path).write_text("{not valid json", encoding="utf-8")
    try:
        try:
            lm.load_module(Path(tmp_path))
        except lm.ConsumerError as e:
            assert "not valid JSON" in str(e)
            return
        raise AssertionError("invalid JSON should raise ConsumerError")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_cli_malformed_manifest_returns_exit_2() -> None:
    bad_manifest = _temp_manifest(lambda m: m.pop("id"))
    try:
        out_buf, err_buf = io.StringIO(), io.StringIO()
        with redirect_stdout(out_buf), redirect_stderr(err_buf):
            code = lm.main([str(bad_manifest)])
        assert code == 2
        assert "ERROR" in err_buf.getvalue()
        assert "id" in err_buf.getvalue()
    finally:
        bad_manifest.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# CLI happy path
# ---------------------------------------------------------------------------

def test_cli_happy_path_prints_consumable_block() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = lm.main([str(SAMPLE_MANIFEST)])
    assert code == 0
    out = buf.getvalue()
    for label in (
        "module id:",
        "type:",
        "dimensions:",
        "anchor:",
        "placement:",
        "glb_path:",
        "resolved path:",
        "asset present:    yes",
        "RESULT: CONSUMABLE",
    ):
        assert label in out, f"missing CLI label {label!r} in:\n{out}"


def test_module_is_frozen_dataclass() -> None:
    # Defensive — the contract belongs to the manifest, not to in-memory copies.
    module = lm.load_module(SAMPLE_MANIFEST)
    try:
        module.id = "tampered"  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("Module should be immutable (frozen=True)")


def main() -> int:
    tests = [
        test_sample_manifest_loads_to_typed_module,
        test_dimensions_are_typed_integers_in_mm,
        test_metre_accessors_match_manifest_mm,
        test_glb_path_resolves_to_committed_fixture,
        test_asset_exists_true_for_current_fixture,
        test_missing_glb_loads_cleanly_with_asset_exists_false,
        test_cli_missing_asset_returns_1_and_prints_not_consumable,
        test_missing_id_raises_clear_consumer_error,
        test_missing_dimensions_field_raises,
        test_missing_dimensions_subfield_names_the_subfield,
        test_missing_visual_glb_path_raises,
        test_non_glb_extension_raises,
        test_fractional_dimensions_raise,
        test_manifest_not_found_raises,
        test_invalid_json_raises_with_helpful_message,
        test_cli_malformed_manifest_returns_exit_2,
        test_cli_happy_path_prints_consumable_block,
        test_module_is_frozen_dataclass,
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
