"""Tests for the galley_v1 Fusion parameter mapping dry-run."""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "fusion"))

import export_galley_v1_parameters as exporter  # noqa: E402
import validate_fusion_parameter_map as v  # noqa: E402

SAMPLE_MANIFEST = REPO_ROOT / "examples" / "galley_1000.json"
PARAMETER_MAP = REPO_ROOT / "tools" / "fusion" / "galley_v1_parameter_map.json"
EXPECTED_EXPORT = REPO_ROOT / "tests" / "fixtures" / "galley_1000_fusion_parameters.expected.json"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _temp_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="dmv_fusion_map_"))
    (root / "examples").mkdir()
    (root / "tools" / "fusion").mkdir(parents=True)
    shutil.copy2(SAMPLE_MANIFEST, root / "examples" / "galley_1000.json")
    shutil.copy2(PARAMETER_MAP, root / "tools" / "fusion" / "galley_v1_parameter_map.json")
    return root


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _validate_mutation(
    *,
    map_mutator=None,
    manifest_mutator=None,
) -> tuple[str, str]:
    root = _temp_root()
    try:
        manifest_path = root / "examples" / "galley_1000.json"
        map_path = root / "tools" / "fusion" / "galley_v1_parameter_map.json"
        manifest = _load_json(manifest_path)
        mapping = _load_json(map_path)
        if manifest_mutator is not None:
            manifest_mutator(manifest)
            _write_json(manifest_path, manifest)
        if map_mutator is not None:
            map_mutator(mapping)
            _write_json(map_path, mapping)
        status, lines = v.validate_fusion_parameter_map(map_path, root)
        return status, "\n".join(lines)
    finally:
        shutil.rmtree(root)


def test_map_validates() -> None:
    status, lines = v.validate_fusion_parameter_map(PARAMETER_MAP, REPO_ROOT)
    joined = "\n".join(lines)
    assert status == v.STATUS_VALID, joined
    assert "RESULT: FUSION PARAMETER MAP VALID" in joined


def test_dry_run_export_matches_expected_fixture() -> None:
    out_dir = Path(tempfile.mkdtemp(prefix="dmv_fusion_export_"))
    try:
        out = out_dir / "galley_1000_fusion_parameters.json"
        exporter.export_parameters(SAMPLE_MANIFEST, PARAMETER_MAP, out, REPO_ROOT)
        assert out.read_text(encoding="utf-8") == EXPECTED_EXPORT.read_text(encoding="utf-8")
    finally:
        shutil.rmtree(out_dir)


def test_missing_width_mapping_fails() -> None:
    def mutate(mapping: dict) -> None:
        del mapping["parameters"]["Width"]

    status, joined = _validate_mutation(map_mutator=mutate)
    assert status == v.STATUS_INVALID
    assert "required Fusion parameter missing: Width" in joined


def test_wrong_fusion_template_fails() -> None:
    def mutate(manifest: dict) -> None:
        manifest["manufacturing"]["fusion_template"] = "galley_v2"

    status, joined = _validate_mutation(manifest_mutator=mutate)
    assert status == v.STATUS_INVALID
    assert 'manifest manufacturing.fusion_template must be "galley_v1"' in joined


def test_non_integer_dimension_fails() -> None:
    def mutate(manifest: dict) -> None:
        manifest["dimensions_mm"]["width"] = 1000.5

    status, joined = _validate_mutation(manifest_mutator=mutate)
    assert status == v.STATUS_INVALID
    assert "dimensions_mm.width must resolve to an integer millimetre value" in joined


def test_bool_dimension_fails() -> None:
    def mutate(manifest: dict) -> None:
        manifest["dimensions_mm"]["width"] = True

    status, joined = _validate_mutation(manifest_mutator=mutate)
    assert status == v.STATUS_INVALID
    assert "dimensions_mm.width must resolve to an integer millimetre value" in joined


def test_visual_fields_are_ignored_not_consumed() -> None:
    mapping = _load_json(PARAMETER_MAP)
    for field in ("visual.glb_path", "visual.material_slots", "visual.collision_proxy"):
        assert field in mapping["ignored_fields"]

    def mutate(mapping: dict) -> None:
        mapping["metadata"]["visual_asset"] = {
            "source": "visual.glb_path",
            "type": "string",
        }

    status, joined = _validate_mutation(map_mutator=mutate)
    assert status == v.STATUS_INVALID
    assert "visual fields must not be consumed as Fusion parameters" in joined


def test_missing_ignored_deferred_field_list_fails() -> None:
    def mutate(mapping: dict) -> None:
        mapping.pop("ignored_fields")

    status, joined = _validate_mutation(map_mutator=mutate)
    assert status == v.STATUS_INVALID
    assert "ignored_fields must be a list" in joined


def test_generated_build_output_is_not_committed() -> None:
    rel = "build/fusion/galley_1000_fusion_parameters.json"
    tracked = subprocess.run(
        ["git", "ls-files", rel],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert tracked.stdout.strip() == ""

    ignored = subprocess.run(
        ["git", "check-ignore", rel],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert ignored.returncode == 0, ignored.stderr


def test_cli_default_map_returns_0() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = v.main([])
    assert code == 0
    assert "RESULT: FUSION PARAMETER MAP VALID" in buf.getvalue()


def main() -> int:
    tests = [
        test_map_validates,
        test_dry_run_export_matches_expected_fixture,
        test_missing_width_mapping_fails,
        test_wrong_fusion_template_fails,
        test_non_integer_dimension_fails,
        test_bool_dimension_fails,
        test_visual_fields_are_ignored_not_consumed,
        test_missing_ignored_deferred_field_list_fails,
        test_generated_build_output_is_not_committed,
        test_cli_default_map_returns_0,
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
