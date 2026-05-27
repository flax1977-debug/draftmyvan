"""Pure-Python tests for the Blender candidate generator guardrails.

The generator itself runs inside Blender, but its manifest parsing discipline
must be CI-testable without `bpy`.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "blender"))

import create_galley_candidate as g  # noqa: E402

MANIFEST = REPO_ROOT / "examples" / "galley_1000.json"
CANDIDATE_GLB = REPO_ROOT / "examples" / "assets" / "candidates" / "galley_1000_candidate.glb"
EXPECTED_CANDIDATE_SHA = "0821e06ce68396f413447ec46e16ea5cf179c4d1c5458c59681c77f27e115ee8"


def _load_manifest() -> dict:
    with MANIFEST.open("r", encoding="utf-8") as f:
        return json.load(f)


def _rejects(mutator, expected: str) -> None:
    manifest = copy.deepcopy(_load_manifest())
    mutator(manifest)
    try:
        g._dimensions_m(manifest)
    except SystemExit as e:
        assert expected in str(e), str(e)
        return
    raise AssertionError("invalid dimensions should raise SystemExit")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def test_valid_manifest_dimensions_are_meters_without_casting() -> None:
    assert g._dimensions_m(_load_manifest()) == (1.0, 0.52, 0.9)


def test_fractional_width_is_rejected() -> None:
    _rejects(
        lambda m: m["dimensions_mm"].__setitem__("width", 1000.5),
        "dimensions_mm.width",
    )


def test_string_width_is_rejected() -> None:
    _rejects(
        lambda m: m["dimensions_mm"].__setitem__("width", "1000"),
        "dimensions_mm.width",
    )


def test_bool_width_is_rejected() -> None:
    _rejects(
        lambda m: m["dimensions_mm"].__setitem__("width", True),
        "dimensions_mm.width",
    )


def test_missing_dimension_field_is_rejected() -> None:
    def mutate(manifest: dict) -> None:
        del manifest["dimensions_mm"]["width"]

    _rejects(mutate, "dimensions_mm.width is required")


def test_non_positive_dimension_is_rejected() -> None:
    _rejects(
        lambda m: m["dimensions_mm"].__setitem__("width", 0),
        "dimensions_mm.width must be > 0",
    )


def test_current_candidate_sha_matches_script_generated_expectation() -> None:
    assert _sha256(CANDIDATE_GLB) == EXPECTED_CANDIDATE_SHA


def main() -> int:
    tests = [
        test_valid_manifest_dimensions_are_meters_without_casting,
        test_fractional_width_is_rejected,
        test_string_width_is_rejected,
        test_bool_width_is_rejected,
        test_missing_dimension_field_is_rejected,
        test_non_positive_dimension_is_rejected,
        test_current_candidate_sha_matches_script_generated_expectation,
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
