#!/usr/bin/env python3
"""Validate DraftMyVan project files against project.schema.json.

Usage:
    python tools/validate_project.py examples/projects/weekend_explorer.json
    python tools/validate_project.py --all   # every *.json under examples/projects/

Exit codes:
    0  all files valid
    1  one or more files invalid
    2  bad arguments / schema load failure

This is the structural gate (JSON Schema only). Cross-reference checks —
that every module_id resolves and that placements fit the van — live in
runtime/project.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:
    sys.stderr.write("ERROR: jsonschema is not installed. Run: pip install jsonschema\n")
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "project.schema.json"
PROJECTS_DIR = REPO_ROOT / "examples" / "projects"


def load_schema() -> dict:
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_file(path: Path, validator: Draft202012Validator) -> list[str]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"invalid JSON: {e}"]

    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    return [
        f"{'/'.join(str(p) for p in err.absolute_path) or '<root>'}: {err.message}"
        for err in errors
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DraftMyVan project files.")
    parser.add_argument("paths", nargs="*", type=Path, help="Project JSON files to validate.")
    parser.add_argument("--all", action="store_true", help="Validate every *.json under examples/projects/.")
    args = parser.parse_args()

    if args.all:
        targets = sorted(PROJECTS_DIR.glob("*.json"))
    else:
        targets = args.paths

    if not targets:
        parser.error("no files provided (pass paths or --all)")
        return 2

    try:
        schema = load_schema()
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
    except Exception as e:
        sys.stderr.write(f"ERROR loading schema {SCHEMA_PATH}: {e}\n")
        return 2

    failed = 0
    for path in targets:
        if not path.exists():
            print(f"FAIL  {path}: file not found")
            failed += 1
            continue
        errors = validate_file(path, validator)
        if errors:
            failed += 1
            print(f"FAIL  {path}")
            for err in errors:
                print(f"      - {err}")
        else:
            print(f"OK    {path}")

    print()
    print(f"{len(targets) - failed}/{len(targets)} valid")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
