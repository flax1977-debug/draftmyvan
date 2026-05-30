"""Pure-Python layout validation: collision, clearance, and payload.

Consumes a typed ``Project`` (runtime/project.py) plus the referenced module
manifests, and reports structured results. No Blender, no Fusion, no API.

Scope and honesty boundaries (deliberately conservative for a first version):
  * Collision is solid axis-aligned-bounding-box (AABB) overlap between placed
    instances. Rotations of 0/90/180/270 deg about vertical Z are exact
    (integer footprint); other angles use a float rotated-AABB.
  * Clearance enforces only the direction-unambiguous manifest clearances —
    ``sides_mm`` (the ±X width axis) and ``above_mm`` (+Z) — as inter-module
    proximity warnings. ``front_mm`` is NOT enforced: the manifest carries no
    module facing direction, so "front" is undefined after placement/rotation.
    Door swing, drawer travel, and service-access geometry are likewise not
    represented in the data and are reported as not enforced rather than faked.
  * Payload sums manifest weights and compares to the van limit when present.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import anchors
from .load_module import ConsumerError, load_module
from .module import Module
from .project import EXAMPLES_DIR, ModuleInstance, Project

# Clearance/geometry concerns the current data cannot support, surfaced so the
# UI never mistakes "not checked" for "passed".
CLEARANCE_NOT_ENFORCED = (
    "front_clearance",  # no module facing direction in the manifest
    "door_swing",
    "drawer_travel",
    "service_access",
)


@dataclass(frozen=True)
class ModuleSpec:
    """A module's geometry/weight/clearance, resolved from its manifest."""

    module: Module
    weight_kg: Optional[float]
    clearances_mm: Optional[dict]  # {front_mm, sides_mm, above_mm} or None


@dataclass(frozen=True)
class AABB:
    x0: float
    x1: float
    y0: float
    y1: float
    z0: float
    z1: float


@dataclass(frozen=True)
class Collision:
    instance_a: str
    instance_b: str
    overlap_mm: dict  # {"x": ..., "y": ..., "z": ...}, all positive


@dataclass(frozen=True)
class ClearanceWarning:
    instance_a: str  # the module whose clearance requirement is encroached
    instance_b: str  # the neighbour encroaching
    kind: str        # "sides" | "above"
    gap_mm: float
    required_mm: int


@dataclass(frozen=True)
class PayloadResult:
    total_weight_kg: float
    limit_kg: Optional[float]
    remaining_kg: Optional[float]
    weight_ok: bool
    limit_enforced: bool


@dataclass(frozen=True)
class LayoutValidation:
    collisions: list
    clearance_warnings: list
    clearance_not_enforced: tuple
    payload: PayloadResult


def module_specs(manifests_dir: Path = EXAMPLES_DIR) -> dict[str, ModuleSpec]:
    """Resolve id -> ModuleSpec for every loadable manifest (non-recursive)."""
    specs: dict[str, ModuleSpec] = {}
    for path in sorted(manifests_dir.glob("*.json")):
        if not path.is_file():
            continue
        try:
            module = load_module(path)
        except ConsumerError:
            continue
        try:
            with path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            raw = {}
        manufacturing = raw.get("manufacturing", {}) if isinstance(raw, dict) else {}
        weight = manufacturing.get("weight_kg")
        clearances = raw.get("clearances") if isinstance(raw, dict) else None
        specs[module.id] = ModuleSpec(
            module=module,
            weight_kg=weight if isinstance(weight, (int, float)) and not isinstance(weight, bool) else None,
            clearances_mm=clearances if isinstance(clearances, dict) else None,
        )
    return specs


def instance_aabb(module: Module, inst: ModuleInstance) -> AABB:
    """Van-space AABB for a placed instance, honouring its module's anchor."""
    x0, x1, y0, y1, z0, z1 = anchors.aabb(
        module.anchor,
        inst.position_mm.x,
        inst.position_mm.y,
        inst.position_mm.z,
        module.dimensions.width_mm,
        module.dimensions.depth_mm,
        module.dimensions.height_mm,
        inst.rotation_deg,
    )
    return AABB(x0, x1, y0, y1, z0, z1)


def _overlap_1d(a0: float, a1: float, b0: float, b1: float) -> bool:
    # Strict: shared faces (touching) are not an overlap.
    return a0 < b1 and b0 < a1


def _gap_1d(a0: float, a1: float, b0: float, b1: float) -> float:
    # Positive when separated, <= 0 when overlapping/touching.
    return max(b0 - a1, a0 - b1)


def _placed(project: Project, specs: dict[str, ModuleSpec]) -> list[tuple[ModuleInstance, ModuleSpec, AABB]]:
    placed = []
    for inst in project.instances:
        spec = specs.get(inst.module_id)
        if spec is None:
            continue
        placed.append((inst, spec, instance_aabb(spec.module, inst)))
    return placed


def detect_collisions(project: Project, specs: dict[str, ModuleSpec]) -> list[Collision]:
    """Solid AABB overlaps between distinct placed instances (touching is fine)."""
    placed = _placed(project, specs)
    collisions: list[Collision] = []
    for i in range(len(placed)):
        for j in range(i + 1, len(placed)):
            (ia, _, a) = placed[i]
            (ib, _, b) = placed[j]
            if (
                _overlap_1d(a.x0, a.x1, b.x0, b.x1)
                and _overlap_1d(a.y0, a.y1, b.y0, b.y1)
                and _overlap_1d(a.z0, a.z1, b.z0, b.z1)
            ):
                collisions.append(
                    Collision(
                        instance_a=ia.instance_id,
                        instance_b=ib.instance_id,
                        overlap_mm={
                            "x": round(min(a.x1, b.x1) - max(a.x0, b.x0), 3),
                            "y": round(min(a.y1, b.y1) - max(a.y0, b.y0), 3),
                            "z": round(min(a.z1, b.z1) - max(a.z0, b.z0), 3),
                        },
                    )
                )
    return collisions


def clearance_warnings(project: Project, specs: dict[str, ModuleSpec]) -> list[ClearanceWarning]:
    """Inter-module proximity warnings for the enforceable clearances only.

    For each ordered pair (A, B) that does NOT solid-collide:
      * sides: A and B overlap in Y and Z, but the X separation is below
        A.sides_mm.
      * above: A and B overlap in X and Y, B sits above A, and the Z gap is
        below A.above_mm.
    front_mm is intentionally not checked (see CLEARANCE_NOT_ENFORCED).
    """
    placed = _placed(project, specs)
    warnings: list[ClearanceWarning] = []
    for ia, spec_a, a in placed:
        clear = spec_a.clearances_mm or {}
        sides = clear.get("sides_mm")
        above = clear.get("above_mm")
        for ib, _spec_b, b in placed:
            if ia.instance_id == ib.instance_id:
                continue
            # Skip pairs whose solids already collide (reported separately).
            if (
                _overlap_1d(a.x0, a.x1, b.x0, b.x1)
                and _overlap_1d(a.y0, a.y1, b.y0, b.y1)
                and _overlap_1d(a.z0, a.z1, b.z0, b.z1)
            ):
                continue
            if isinstance(sides, int) and _overlap_1d(a.y0, a.y1, b.y0, b.y1) and _overlap_1d(a.z0, a.z1, b.z0, b.z1):
                gx = _gap_1d(a.x0, a.x1, b.x0, b.x1)
                if 0 <= gx < sides:
                    warnings.append(ClearanceWarning(ia.instance_id, ib.instance_id, "sides", round(gx, 3), sides))
            if isinstance(above, int) and _overlap_1d(a.x0, a.x1, b.x0, b.x1) and _overlap_1d(a.y0, a.y1, b.y0, b.y1):
                if b.z0 >= a.z1:
                    gz = b.z0 - a.z1
                    if 0 <= gz < above:
                        warnings.append(ClearanceWarning(ia.instance_id, ib.instance_id, "above", round(gz, 3), above))
    return warnings


def validate_payload(project: Project, specs: dict[str, ModuleSpec]) -> PayloadResult:
    """Sum manifest weights and compare to the van payload limit if present."""
    total = 0.0
    for inst in project.instances:
        spec = specs.get(inst.module_id)
        if spec is not None and spec.weight_kg is not None:
            total += spec.weight_kg
    total = round(total, 3)

    limit = project.van.max_payload_kg
    if limit is None:
        return PayloadResult(
            total_weight_kg=total,
            limit_kg=None,
            remaining_kg=None,
            weight_ok=True,
            limit_enforced=False,
        )
    return PayloadResult(
        total_weight_kg=total,
        limit_kg=limit,
        remaining_kg=round(limit - total, 3),
        weight_ok=total <= limit,
        limit_enforced=True,
    )


def validate_layout(project: Project, specs: Optional[dict[str, ModuleSpec]] = None) -> LayoutValidation:
    if specs is None:
        specs = module_specs()
    return LayoutValidation(
        collisions=detect_collisions(project, specs),
        clearance_warnings=clearance_warnings(project, specs),
        clearance_not_enforced=CLEARANCE_NOT_ENFORCED,
        payload=validate_payload(project, specs),
    )
