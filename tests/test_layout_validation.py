"""Tests for the layout validation engine (runtime/layout_validation.py).

Pure Python. Uses two placements of the one committed module (the galley)
rather than inventing modules. Galley facts: width 1000, depth 520,
height 900 mm; weight 45 kg; clearances sides 20 / above 50 / front 450.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from runtime import anchors  # noqa: E402
from runtime import layout_validation as lv  # noqa: E402
from runtime.project import (  # noqa: E402
    ModuleInstance,
    Project,
    Van,
    Vec3,
    containment_issues,
    index_modules,
    load_project,
)

GALLEY = "galley_1000_sink_left_oak"
LOCKER = "overhead_locker_1200"  # ceiling_left, 1200x300x350
SPECS = lv.module_specs()
EXAMPLE = REPO_ROOT / "examples" / "projects" / "weekend_explorer.json"


def _van(payload: float | None = 1200) -> Van:
    return Van(
        make=None, model=None, wheelbase_mm=None,
        length_mm=5932, width_mm=2020, height_mm=2760, max_payload_kg=payload,
    )


def _inst(iid: str, x: int, y: int, z: int, rot: float = 0) -> ModuleInstance:
    return ModuleInstance(
        instance_id=iid, module_id=GALLEY, position_mm=Vec3(x, y, z),
        rotation_deg=rot, zone="kitchen", visible=True,
    )


def _project(instances, payload: float | None = 1200) -> Project:
    return Project(id="t", name="t", van=_van(payload), instances=tuple(instances))


# --- collision ----------------------------------------------------------

def test_non_overlapping_modules_have_no_collision() -> None:
    p = _project([_inst("a", 0, 0, 0), _inst("b", 0, 600, 0)])  # separated in Y
    assert lv.detect_collisions(p, SPECS) == []


def test_overlapping_modules_are_detected() -> None:
    p = _project([_inst("a", 0, 0, 0), _inst("b", 500, 0, 0)])  # overlap 500 in X
    collisions = lv.detect_collisions(p, SPECS)
    assert len(collisions) == 1, collisions
    c = collisions[0]
    assert {c.instance_a, c.instance_b} == {"a", "b"}
    assert c.overlap_mm == {"x": 500, "y": 520, "z": 900}, c.overlap_mm


def test_touching_faces_are_not_a_collision() -> None:
    # b starts exactly where a ends in X.
    p = _project([_inst("a", 0, 0, 0), _inst("b", 1000, 0, 0)])
    assert lv.detect_collisions(p, SPECS) == []


def test_rotation_90_swaps_footprint() -> None:
    spec = SPECS[GALLEY]
    box0 = lv.instance_aabb(spec.module, _inst("r0", 0, 0, 0, rot=0))
    box90 = lv.instance_aabb(spec.module, _inst("r90", 0, 0, 0, rot=90))
    # Unrotated: X spans width (1000), Y spans depth (520).
    assert (box0.x1 - box0.x0, box0.y1 - box0.y0) == (1000, 520)
    # Rotated 90 about the anchor corner: extents swap (X=520, Y=1000).
    assert (box90.x1 - box90.x0, box90.y1 - box90.y0) == (520, 1000)


# --- clearance ----------------------------------------------------------

def test_side_clearance_warns_when_too_close() -> None:
    # 10 mm gap in X (< galley sides_mm of 20), overlapping in Y and Z.
    p = _project([_inst("a", 0, 0, 0), _inst("b", 1010, 0, 0)])
    assert lv.detect_collisions(p, SPECS) == []
    warns = lv.clearance_warnings(p, SPECS)
    kinds = {(w.kind, w.required_mm) for w in warns}
    assert ("sides", 20) in kinds, warns


def test_no_clearance_warning_when_far_apart() -> None:
    p = _project([_inst("a", 0, 0, 0), _inst("b", 1100, 0, 0)])  # 100 mm gap > 20
    assert lv.clearance_warnings(p, SPECS) == []


def test_front_and_other_geometry_marked_not_enforced() -> None:
    assert "front_clearance" in lv.CLEARANCE_NOT_ENFORCED
    for k in ("door_swing", "drawer_travel", "service_access"):
        assert k in lv.CLEARANCE_NOT_ENFORCED


# --- payload ------------------------------------------------------------

def test_payload_under_limit_is_ok() -> None:
    r = lv.validate_payload(_project([_inst("a", 0, 0, 0)], payload=1200), SPECS)
    assert r.total_weight_kg == 45
    assert r.limit_kg == 1200
    assert r.remaining_kg == 1155
    assert r.weight_ok is True
    assert r.limit_enforced is True


def test_payload_over_limit_is_not_ok() -> None:
    r = lv.validate_payload(_project([_inst("a", 0, 0, 0)], payload=40), SPECS)
    assert r.weight_ok is False
    assert r.remaining_kg == -5


def test_missing_payload_limit_is_not_enforced() -> None:
    r = lv.validate_payload(_project([_inst("a", 0, 0, 0)], payload=None), SPECS)
    assert r.weight_ok is True
    assert r.limit_enforced is False
    assert r.limit_kg is None
    assert r.remaining_kg is None


# --- integration: the committed example -------------------------------

def test_example_project_is_clean() -> None:
    project = load_project(EXAMPLE)
    v = lv.validate_layout(project, SPECS)
    assert v.collisions == []
    assert v.clearance_warnings == []
    assert v.payload.weight_ok is True
    assert v.payload.limit_enforced is True


# --- anchor semantics --------------------------------------------------

def test_anchor_floor_back_left_box() -> None:
    assert anchors.aabb("floor_back_left", 0, 0, 0, 1000, 520, 900) == (0, 1000, 0, 520, 0, 900)


def test_anchor_wall_right_extends_in_negative_x() -> None:
    # Against the right wall: x runs [x-w, x]; z is floor-style (up).
    box = anchors.aabb("wall_right", 2020, 0, 100, 1000, 520, 900)
    assert (box[0], box[1]) == (1020, 2020), box
    assert (box[4], box[5]) == (100, 1000), box


def test_anchor_ceiling_hangs_down_from_z() -> None:
    # z is the TOP (at the ceiling); height extends downward.
    box = anchors.aabb("ceiling_left", 0, 0, 2760, 1200, 300, 350)
    assert (box[4], box[5]) == (2410, 2760), box
    assert (box[0], box[1], box[2], box[3]) == (0, 1200, 0, 300), box


def test_unsupported_anchor_raises() -> None:
    try:
        anchors.aabb("floor_back_right", 0, 0, 0, 1, 1, 1)
        assert False, "expected UnsupportedAnchorError"
    except anchors.UnsupportedAnchorError:
        pass


def _van_box(payload: float | None = 1200) -> Van:
    return _van(payload)


def test_wall_left_module_inside_van_is_in_bounds() -> None:
    # A 300-deep module on the left wall at mid-height fits the van box.
    box = anchors.aabb("wall_left", 0, 1000, 1200, 300, 1000, 350)
    x0, x1, y0, y1, z0, z1 = box
    inside = 0 <= x0 and x1 <= 2020 and 0 <= y0 and y1 <= 5932 and 0 <= z0 and z1 <= 2760
    assert inside, box


def test_wall_right_module_out_of_bounds_when_too_wide() -> None:
    # 2500 mm extending in -x from the right wall passes x=0 → out of bounds.
    x0, x1, *_ = anchors.aabb("wall_right", 2020, 0, 100, 2500, 300, 300)
    assert x0 < 0, (x0, x1)


def test_ceiling_module_inside_van_passes_containment() -> None:
    idx = index_modules()
    inst = ModuleInstance("locker_a", LOCKER, Vec3(0, 1000, 2760), 0, "utilities", True)
    project = Project("t", "t", _van_box(), (inst,))
    assert containment_issues(project, idx) == []


def test_ceiling_module_out_of_bounds_is_flagged() -> None:
    idx = index_modules()
    # Top at z=300 → hangs down to z=-50 → below the floor → out of bounds.
    inst = ModuleInstance("locker_b", LOCKER, Vec3(0, 1000, 300), 0, "utilities", True)
    project = Project("t", "t", _van_box(), (inst,))
    issues = containment_issues(project, idx)
    assert len(issues) == 1 and "outside the van box" in issues[0], issues


def test_collision_between_floor_and_ceiling_modules() -> None:
    # Galley on the floor (z 0..900) and a ceiling locker hung low (top z=900
    # → z 550..900) overlapping in x/y → AABB collision across mount types.
    galley = ModuleInstance("g", GALLEY, Vec3(0, 0, 0), 0, "kitchen", True)
    locker = ModuleInstance("l", LOCKER, Vec3(0, 0, 900), 0, "utilities", True)
    project = Project("t", "t", _van_box(), (galley, locker))
    collisions = lv.detect_collisions(project, SPECS)
    assert len(collisions) == 1, collisions
    assert {collisions[0].instance_a, collisions[0].instance_b} == {"g", "l"}


def main() -> int:
    tests = [
        test_non_overlapping_modules_have_no_collision,
        test_overlapping_modules_are_detected,
        test_touching_faces_are_not_a_collision,
        test_rotation_90_swaps_footprint,
        test_side_clearance_warns_when_too_close,
        test_no_clearance_warning_when_far_apart,
        test_front_and_other_geometry_marked_not_enforced,
        test_payload_under_limit_is_ok,
        test_payload_over_limit_is_not_ok,
        test_missing_payload_limit_is_not_enforced,
        test_anchor_floor_back_left_box,
        test_anchor_wall_right_extends_in_negative_x,
        test_anchor_ceiling_hangs_down_from_z,
        test_unsupported_anchor_raises,
        test_wall_left_module_inside_van_is_in_bounds,
        test_wall_right_module_out_of_bounds_when_too_wide,
        test_ceiling_module_inside_van_passes_containment,
        test_ceiling_module_out_of_bounds_is_flagged,
        test_collision_between_floor_and_ceiling_modules,
        test_example_project_is_clean,
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
