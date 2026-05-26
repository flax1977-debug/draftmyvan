"""Smoke tests for the manifest validator.

Run from the draftmyvan/ directory:
    python -m tests.test_validator

Confirms:
  1. The schema itself is a valid Draft 2020-12 schema.
  2. The shipped galley_1000.json example validates.
  3. Every required invariant is enforced (negative tests).
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "manifest.schema.json"
SAMPLE_PATH = REPO_ROOT / "examples" / "galley_1000.json"


def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validator() -> Draft202012Validator:
    return Draft202012Validator(_load(SCHEMA_PATH))


def _broken_sample() -> dict:
    return copy.deepcopy(_load(SAMPLE_PATH))


def _assert_rejected(sample: dict, hint: str) -> None:
    errors = list(_validator().iter_errors(sample))
    assert errors, f"expected rejection ({hint}); validator accepted it"


def test_schema_is_valid() -> None:
    schema = _load(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)


def test_galley_1000_validates() -> None:
    schema = _load(SCHEMA_PATH)
    sample = _load(SAMPLE_PATH)
    errors = list(Draft202012Validator(schema).iter_errors(sample))
    assert not errors, f"galley_1000.json should validate, got: {errors}"


def test_negative_missing_required_field() -> None:
    broken = _broken_sample()
    del broken["dimensions_mm"]
    _assert_rejected(broken, "missing dimensions_mm")


def test_negative_fractional_mm_rejected() -> None:
    broken = _broken_sample()
    broken["dimensions_mm"]["width"] = 1000.5
    _assert_rejected(broken, "fractional mm width")


def test_negative_id_with_spaces_or_capitals_rejected() -> None:
    for bad_id in ("Galley 1000", "GALLEY_1000", "galley 1000", "_galley", "galley-1000"):
        broken = _broken_sample()
        broken["id"] = bad_id
        _assert_rejected(broken, f"bad id {bad_id!r}")


def test_negative_missing_glb_path_rejected() -> None:
    broken = _broken_sample()
    del broken["visual"]["glb_path"]
    _assert_rejected(broken, "missing visual.glb_path")


def test_negative_fbx_visual_path_rejected() -> None:
    broken = _broken_sample()
    broken["visual"]["glb_path"] = "assets/galley_1000.fbx"
    _assert_rejected(broken, ".fbx visual path")


def test_negative_negative_clearance_rejected() -> None:
    broken = _broken_sample()
    broken["clearances"]["front_mm"] = -10
    _assert_rejected(broken, "negative clearance")


def test_negative_unknown_extra_field_at_root_rejected() -> None:
    broken = _broken_sample()
    broken["secret_field"] = "nope"
    _assert_rejected(broken, "unknown root field")


def test_negative_unknown_extra_field_nested_rejected() -> None:
    broken = _broken_sample()
    broken["visual"]["preview_jpg"] = "assets/galley_1000.jpg"
    _assert_rejected(broken, "unknown nested field under visual")


def main() -> int:
    tests = [
        test_schema_is_valid,
        test_galley_1000_validates,
        test_negative_missing_required_field,
        test_negative_fractional_mm_rejected,
        test_negative_id_with_spaces_or_capitals_rejected,
        test_negative_missing_glb_path_rejected,
        test_negative_fbx_visual_path_rejected,
        test_negative_negative_clearance_rejected,
        test_negative_unknown_extra_field_at_root_rejected,
        test_negative_unknown_extra_field_nested_rejected,
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
