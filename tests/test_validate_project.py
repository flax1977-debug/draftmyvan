"""Tests for the project schema gate (project.schema.json via jsonschema).

Skips cleanly when jsonschema is not installed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

SCHEMA_PATH = REPO_ROOT / "project.schema.json"
EXAMPLE = REPO_ROOT / "examples" / "projects" / "weekend_explorer.json"

try:
    from jsonschema import Draft202012Validator

    _DEPS_AVAILABLE = True
except ImportError:
    _DEPS_AVAILABLE = False


def _validator() -> "Draft202012Validator":
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _load_example() -> dict:
    with EXAMPLE.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_schema_is_valid() -> None:
    _validator()  # raises if the schema itself is malformed


def test_example_project_validates() -> None:
    errors = list(_validator().iter_errors(_load_example()))
    assert errors == [], [e.message for e in errors]


def test_missing_required_field_fails() -> None:
    data = _load_example()
    del data["van"]
    errors = list(_validator().iter_errors(data))
    assert errors, "removing van must fail schema validation"


def test_unknown_zone_fails() -> None:
    data = _load_example()
    data["module_instances"][0]["zone"] = "garage"
    errors = list(_validator().iter_errors(data))
    assert errors, "an out-of-enum zone must fail schema validation"


def test_additional_property_fails() -> None:
    data = _load_example()
    data["surprise"] = True
    errors = list(_validator().iter_errors(data))
    assert errors, "additionalProperties:false must reject unknown top-level keys"


def test_payload_limit_is_optional() -> None:
    data = _load_example()
    del data["van"]["max_payload_kg"]
    errors = list(_validator().iter_errors(data))
    assert errors == [], [e.message for e in errors]


def main() -> int:
    if not _DEPS_AVAILABLE:
        print('SKIP  project schema suite: jsonschema not installed (pip install -e ".[dev]")')
        print()
        print("0/0 passed (skipped)")
        return 0

    tests = [
        test_schema_is_valid,
        test_example_project_validates,
        test_missing_required_field_fails,
        test_unknown_zone_fails,
        test_additional_property_fails,
        test_payload_limit_is_optional,
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
