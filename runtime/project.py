"""Typed runtime view of a DraftMyVan project (van + placed module instances).

Mirrors ``runtime.load_module``: this is a *consumer* of an already-validated
project file (schema validation lives in ``tools/validate_project.py``). It
still guards required fields and types so a malformed project produces a clear
``ProjectError`` instead of an ``AttributeError`` deep in caller code, and it
cross-checks things JSON Schema cannot express:

  * every ``module_id`` resolves to an existing module manifest;
  * ``position_mm`` components are integers (millimetres are canonical);
  * (separately, via ``containment_issues``) a placed module stays inside the
    van bounding box, where the anchor semantics make that checkable.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .load_module import ConsumerError, load_module
from .module import Module

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples"

ZONES = ("kitchen", "seating", "storage", "bed", "utilities")

# Containment is only enforced for this anchor (the one the rest of the repo
# enforces); see manifest README "currently only floor_back_left is enforced".
_CHECKABLE_ANCHOR = "floor_back_left"


class ProjectError(Exception):
    """A project file is malformed or references something that does not exist."""


@dataclass(frozen=True)
class Vec3:
    x: int
    y: int
    z: int


@dataclass(frozen=True)
class Van:
    make: str | None
    model: str | None
    wheelbase_mm: int | None
    length_mm: int
    width_mm: int
    height_mm: int
    max_payload_kg: float | None


@dataclass(frozen=True)
class ModuleInstance:
    instance_id: str
    module_id: str
    position_mm: Vec3
    rotation_deg: float
    zone: str
    visible: bool


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    van: Van
    instances: tuple[ModuleInstance, ...]


def _require(obj: Any, key: str, where: str) -> Any:
    if not isinstance(obj, dict) or key not in obj:
        raise ProjectError(f"project missing required field {where!r}")
    return obj[key]


def _require_int(value: Any, where: str) -> int:
    # Reject bool (a subclass of int) and float, matching load_module's strict
    # millimetres-as-integers rule.
    if not isinstance(value, int) or isinstance(value, bool):
        raise ProjectError(
            f"{where} must be an integer; got {type(value).__name__} {value!r}"
        )
    return value


def _require_number(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProjectError(
            f"{where} must be a number; got {type(value).__name__} {value!r}"
        )
    return float(value)


def index_modules(manifests_dir: Path = EXAMPLES_DIR) -> dict[str, Module]:
    """Map module id -> typed ``Module`` for every loadable manifest in a dir.

    Non-recursive, so project files under ``examples/projects/`` are not read
    as manifests. Manifests that fail to load are skipped (they are caught by
    the manifest validation gates); a project referencing a skipped/absent id
    then fails with a clear unknown-module error.
    """
    index: dict[str, Module] = {}
    for path in sorted(manifests_dir.glob("*.json")):
        if not path.is_file():
            continue
        try:
            module = load_module(path)
        except ConsumerError:
            continue
        index[module.id] = module
    return index


def _parse_van(raw: Any) -> Van:
    dims = _require(raw, "dimensions_mm", "van.dimensions_mm")
    make = raw.get("make") if isinstance(raw, dict) else None
    model = raw.get("model") if isinstance(raw, dict) else None
    wheelbase = raw.get("wheelbase_mm") if isinstance(raw, dict) else None
    if wheelbase is not None:
        wheelbase = _require_int(wheelbase, "van.wheelbase_mm")
    payload = raw.get("max_payload_kg") if isinstance(raw, dict) else None
    if payload is not None:
        payload = _require_number(payload, "van.max_payload_kg")
    return Van(
        make=str(make) if make is not None else None,
        model=str(model) if model is not None else None,
        wheelbase_mm=wheelbase,
        length_mm=_require_int(_require(dims, "length", "van.dimensions_mm.length"), "van.dimensions_mm.length"),
        width_mm=_require_int(_require(dims, "width", "van.dimensions_mm.width"), "van.dimensions_mm.width"),
        height_mm=_require_int(_require(dims, "height", "van.dimensions_mm.height"), "van.dimensions_mm.height"),
        max_payload_kg=payload,
    )


def _parse_instance(raw: Any, ordinal: int) -> ModuleInstance:
    where = f"module_instances[{ordinal}]"
    instance_id = str(_require(raw, "instance_id", f"{where}.instance_id"))
    module_id = str(_require(raw, "module_id", f"{where}.module_id"))
    pos = _require(raw, "position_mm", f"{where}.position_mm")
    position = Vec3(
        x=_require_int(_require(pos, "x", f"{where}.position_mm.x"), f"{where}.position_mm.x"),
        y=_require_int(_require(pos, "y", f"{where}.position_mm.y"), f"{where}.position_mm.y"),
        z=_require_int(_require(pos, "z", f"{where}.position_mm.z"), f"{where}.position_mm.z"),
    )
    rotation = _require_number(_require(raw, "rotation_deg", f"{where}.rotation_deg"), f"{where}.rotation_deg")
    zone = str(_require(raw, "zone", f"{where}.zone"))
    if zone not in ZONES:
        raise ProjectError(f"{where}.zone {zone!r} is not one of {ZONES}")
    visible = _require(raw, "visible", f"{where}.visible")
    if not isinstance(visible, bool):
        raise ProjectError(f"{where}.visible must be a boolean; got {type(visible).__name__}")
    return ModuleInstance(
        instance_id=instance_id,
        module_id=module_id,
        position_mm=position,
        rotation_deg=rotation,
        zone=zone,
        visible=visible,
    )


def parse_project(raw: Any, manifests_dir: Path = EXAMPLES_DIR) -> Project:
    """Validate an in-memory project dict into a typed ``Project``.

    Same checks as ``load_project`` but without disk I/O — used by the save
    path to validate a candidate layout before it is written.
    """
    if not isinstance(raw, dict):
        raise ProjectError("project must be a JSON object")

    project_id = str(_require(raw, "id", "id"))
    name = str(_require(raw, "name", "name"))
    van = _parse_van(_require(raw, "van", "van"))

    instances_raw = _require(raw, "module_instances", "module_instances")
    if not isinstance(instances_raw, list):
        raise ProjectError("module_instances must be a list")

    index = index_modules(manifests_dir)
    instances: list[ModuleInstance] = []
    seen_instance_ids: set[str] = set()
    for ordinal, item in enumerate(instances_raw):
        inst = _parse_instance(item, ordinal)
        if inst.instance_id in seen_instance_ids:
            raise ProjectError(f"duplicate instance_id {inst.instance_id!r}")
        seen_instance_ids.add(inst.instance_id)
        if inst.module_id not in index:
            raise ProjectError(
                f"module_instances[{ordinal}] references unknown module_id "
                f"{inst.module_id!r} (no manifest with that id in {manifests_dir})"
            )
        instances.append(inst)

    return Project(id=project_id, name=name, van=van, instances=tuple(instances))


def load_project(project_path: Path, manifests_dir: Path = EXAMPLES_DIR) -> Project:
    """Read a project JSON file into a typed ``Project``.

    Raises ``ProjectError`` for malformed JSON/structure, non-integer
    positions, duplicate instance ids, or a ``module_id`` that does not
    resolve to a manifest in ``manifests_dir``.
    """
    if not project_path.exists():
        raise ProjectError(f"project not found: {project_path}")
    try:
        with project_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        raise ProjectError(f"project {project_path} is not valid JSON: {e}") from e
    return parse_project(raw, manifests_dir)


def _footprint_bounds(
    module: Module, inst: ModuleInstance
) -> tuple[float, float, float, float]:
    """Axis-aligned (minx, maxx, miny, maxy) of the rotated footprint, in mm.

    The module's width maps to van X, depth to van Y. The footprint rectangle
    is rotated about the anchor corner by rotation_deg, then offset by the
    instance position. For rotation_deg == 0 this is simply
    [px, px+width] x [py, py+depth].
    """
    w = module.dimensions.width_mm
    d = module.dimensions.depth_mm
    theta = math.radians(inst.rotation_deg)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    corners = ((0.0, 0.0), (w, 0.0), (0.0, d), (w, d))
    xs = [cx * cos_t - cy * sin_t for cx, cy in corners]
    ys = [cx * sin_t + cy * cos_t for cx, cy in corners]
    px, py = inst.position_mm.x, inst.position_mm.y
    return (px + min(xs), px + max(xs), py + min(ys), py + max(ys))


def containment_issues(project: Project, index: dict[str, Module] | None = None) -> list[str]:
    """Return human-readable issues for instances that fall outside the van box.

    Only instances whose module uses the ``floor_back_left`` anchor are checked
    (the only anchor with enforced semantics); others are not enough data and
    are skipped. An empty list means every checkable instance fits.
    """
    if index is None:
        index = index_modules()
    van = project.van
    issues: list[str] = []
    for inst in project.instances:
        module = index.get(inst.module_id)
        if module is None or module.anchor != _CHECKABLE_ANCHOR:
            continue
        x0, x1, y0, y1 = _footprint_bounds(module, inst)
        z0 = float(inst.position_mm.z)
        z1 = z0 + module.dimensions.height_mm
        if x0 < 0 or x1 > van.width_mm or y0 < 0 or y1 > van.length_mm or z0 < 0 or z1 > van.height_mm:
            issues.append(
                f"instance {inst.instance_id!r} (module {inst.module_id!r}) extends outside the van box: "
                f"footprint x[{x0:.0f},{x1:.0f}] y[{y0:.0f},{y1:.0f}] z[{z0:.0f},{z1:.0f}] mm "
                f"vs van width={van.width_mm} length={van.length_mm} height={van.height_mm} mm"
            )
    return issues
