"""Aggregate build-readiness for the configurator status bar / Build-Ready badge.

Combines the checks that actually exist today, reusing committed code:
  * schema validation of every manifest — via tools/validate_manifest.py;
  * catalog integrity (no duplicate ids/asset paths, assets present) — via
    runtime.package_report.scan_package;
  * total module weight — summed from the catalog cards.

Two checks the target UI shows are NOT enforceable yet and are reported
honestly rather than faked:
  * collision detection has no engine (Phase 2): collisions is [] AND
    ``collision_check_implemented`` is False, so "not checked" is not
    mistaken for "no collisions";
  * there is no van payload budget yet (Phase 2/3): ``weight_limit_kg`` is
    null and ``weight_ok`` is true only because no limit is configured.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from runtime.package_report import scan_package

from . import catalog

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples"


def _load_validate_manifest_module():
    """Load tools/validate_manifest.py by path (it is a CLI, not a package)."""
    path = REPO_ROOT / "tools" / "validate_manifest.py"
    spec = importlib.util.spec_from_file_location("dmv_validate_manifest", path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError(f"cannot load validator module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_validate_manifest = _load_validate_manifest_module()


def compute() -> dict[str, Any]:
    """Return the aggregate build-readiness payload."""
    validator = Draft202012Validator(_validate_manifest.load_schema())

    schema_errors: dict[str, list[str]] = {}
    for path in sorted(EXAMPLES_DIR.glob("*.json")):
        if not path.is_file():
            continue
        errors = _validate_manifest.validate_file(path, validator)
        if errors:
            schema_errors[path.name] = errors

    report = scan_package(EXAMPLES_DIR)

    cards = catalog.list_modules()
    weights = [c["weight_kg"] for c in cards if isinstance(c.get("weight_kg"), (int, float))]
    total_weight_kg = round(sum(weights), 3)

    all_valid = (
        not schema_errors
        and not report.errors
        and report.missing_assets == 0
        and report.total_modules > 0
    )

    # Phase 2: no collision engine yet.
    collisions: list[Any] = []
    collision_check_implemented = False

    # Phase 2/3: no van payload budget yet, so no limit to exceed.
    weight_limit_kg = None
    weight_ok = weight_limit_kg is None or total_weight_kg <= weight_limit_kg

    build_ready = all_valid and not collisions and weight_ok

    return {
        "build_ready": build_ready,
        "all_valid": all_valid,
        "collisions": collisions,
        "collision_check_implemented": collision_check_implemented,
        "weight_ok": weight_ok,
        "total_weight_kg": total_weight_kg,
        "weight_limit_kg": weight_limit_kg,
        "module_count": report.total_modules,
        "missing_assets": report.missing_assets,
        "schema_errors": schema_errors,
        "package_errors": report.errors,
    }
