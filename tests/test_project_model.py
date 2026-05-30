"""Tests for the project model loader/validator (runtime/project.py).

Pure Python — exercises typed loading, field-type guards, module-id
resolution, and van-box containment against the committed example project
and temp mutations of it.
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from runtime import project as pj  # noqa: E402
from runtime.project import ProjectError  # noqa: E402

EXAMPLE = REPO_ROOT / "examples" / "projects" / "weekend_explorer.json"


def _load_example_dict() -> dict:
    with EXAMPLE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _temp_project(mutator) -> Path:
    data = _load_example_dict()
    mutator(data)
    fd, tmp = tempfile.mkstemp(suffix=".json", prefix="project_")
    Path(tmp).write_text(json.dumps(data), encoding="utf-8")
    return Path(tmp)


# --- happy path ---------------------------------------------------------

def test_example_project_loads() -> None:
    project = pj.load_project(EXAMPLE)
    assert project.id == "weekend_explorer"
    assert project.name == "Weekend Explorer"
    assert len(project.instances) == 1


def test_van_fields() -> None:
    van = pj.load_project(EXAMPLE).van
    assert van.make == "Mercedes-Benz"
    assert van.length_mm == 5932
    assert van.width_mm == 2020
    assert van.height_mm == 2760
    assert van.wheelbase_mm == 3665
    assert van.max_payload_kg == 1200


def test_instance_fields() -> None:
    inst = pj.load_project(EXAMPLE).instances[0]
    assert inst.instance_id == "galley_back_left"
    assert inst.module_id == "galley_1000_sink_left_oak"
    assert (inst.position_mm.x, inst.position_mm.y, inst.position_mm.z) == (0, 0, 0)
    assert inst.rotation_deg == 0
    assert inst.zone == "kitchen"
    assert inst.visible is True


# --- validation: structure & types -------------------------------------

def test_unknown_module_id_raises() -> None:
    p = _temp_project(lambda d: d["module_instances"][0].__setitem__("module_id", "no_such_module"))
    try:
        pj.load_project(p)
        assert False, "expected ProjectError for unknown module_id"
    except ProjectError as e:
        assert "unknown module_id" in str(e)
    finally:
        p.unlink(missing_ok=True)


def test_float_position_raises() -> None:
    p = _temp_project(lambda d: d["module_instances"][0]["position_mm"].__setitem__("x", 10.5))
    try:
        pj.load_project(p)
        assert False, "expected ProjectError for non-integer position"
    except ProjectError as e:
        assert "position_mm.x must be an integer" in str(e)
    finally:
        p.unlink(missing_ok=True)


def test_bad_zone_raises() -> None:
    p = _temp_project(lambda d: d["module_instances"][0].__setitem__("zone", "garage"))
    try:
        pj.load_project(p)
        assert False, "expected ProjectError for bad zone"
    except ProjectError:
        pass
    finally:
        p.unlink(missing_ok=True)


def test_duplicate_instance_id_raises() -> None:
    def dup(d: dict) -> None:
        clone = copy.deepcopy(d["module_instances"][0])
        d["module_instances"].append(clone)
    p = _temp_project(dup)
    try:
        pj.load_project(p)
        assert False, "expected ProjectError for duplicate instance_id"
    except ProjectError as e:
        assert "duplicate instance_id" in str(e)
    finally:
        p.unlink(missing_ok=True)


def test_missing_van_raises() -> None:
    p = _temp_project(lambda d: d.pop("van"))
    try:
        pj.load_project(p)
        assert False, "expected ProjectError for missing van"
    except ProjectError as e:
        assert "van" in str(e)
    finally:
        p.unlink(missing_ok=True)


# --- validation: containment -------------------------------------------

def test_example_is_within_van_bounds() -> None:
    project = pj.load_project(EXAMPLE)
    assert pj.containment_issues(project) == []


def test_out_of_bounds_instance_is_flagged() -> None:
    # Galley width is 1000 mm; placing its anchor at x=2000 pushes it to
    # x=3000, beyond the 2020 mm van width.
    p = _temp_project(lambda d: d["module_instances"][0]["position_mm"].__setitem__("x", 2000))
    try:
        project = pj.load_project(p)
        issues = pj.containment_issues(project)
        assert len(issues) == 1, issues
        assert "outside the van box" in issues[0]
    finally:
        p.unlink(missing_ok=True)


def test_rotation_into_negative_is_flagged() -> None:
    # Rotating the footprint 90 deg about its back-left corner sweeps it into
    # negative X, which leaves the van box when the anchor is at x=0.
    p = _temp_project(lambda d: d["module_instances"][0].__setitem__("rotation_deg", 90))
    try:
        project = pj.load_project(p)
        issues = pj.containment_issues(project)
        assert len(issues) == 1, issues
    finally:
        p.unlink(missing_ok=True)


def main() -> int:
    tests = [
        test_example_project_loads,
        test_van_fields,
        test_instance_fields,
        test_unknown_module_id_raises,
        test_float_position_raises,
        test_bad_zone_raises,
        test_duplicate_instance_id_raises,
        test_missing_van_raises,
        test_example_is_within_van_bounds,
        test_out_of_bounds_instance_is_flagged,
        test_rotation_into_negative_is_flagged,
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
