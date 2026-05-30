"""Project endpoints serialization.

Reuses runtime.project (typed load + containment) and the existing catalog
(module weight / glb_url) so no contract or geometry logic is duplicated here.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Optional

from runtime import layout_validation
from runtime.project import (
    EXAMPLES_DIR,
    ModuleInstance,
    Project,
    ProjectError,
    Van,
    Vec3,
    containment_issues,
    index_modules,
    load_project,
)

from . import catalog


class LayoutEditError(ValueError):
    """A layout edit payload referenced an unknown instance or bad values."""

PROJECTS_DIR = EXAMPLES_DIR / "projects"


def _project_files() -> list[Path]:
    return sorted(p for p in PROJECTS_DIR.glob("*.json") if p.is_file())


def _cards_by_id() -> dict[str, dict[str, Any]]:
    return {c["id"]: c for c in catalog.list_modules()}


def _total_weight(project: Project, cards: dict[str, dict[str, Any]]) -> float:
    total = 0.0
    for inst in project.instances:
        card = cards.get(inst.module_id)
        w = card["weight_kg"] if card else None
        if isinstance(w, (int, float)):
            total += w
    return round(total, 3)


def _van_dict(van: Van) -> dict[str, Any]:
    return {
        "make": van.make,
        "model": van.model,
        "wheelbase_mm": van.wheelbase_mm,
        "dimensions_mm": {
            "length": van.length_mm,
            "width": van.width_mm,
            "height": van.height_mm,
        },
        "max_payload_kg": van.max_payload_kg,
    }


def _instance_dict(inst: Any, card: Optional[dict[str, Any]]) -> dict[str, Any]:
    return {
        "instance_id": inst.instance_id,
        "module_id": inst.module_id,
        "position_mm": {
            "x": inst.position_mm.x,
            "y": inst.position_mm.y,
            "z": inst.position_mm.z,
        },
        "rotation_deg": inst.rotation_deg,
        "zone": inst.zone,
        "visible": inst.visible,
        "module": None
        if card is None
        else {
            "type": card["type"],
            "display_name": card["display_name"],
            "dimensions_mm": card["dimensions_mm"],
            "weight_kg": card["weight_kg"],
            "glb_url": card["glb_url"],
        },
    }


def list_projects() -> list[dict[str, Any]]:
    """All committed projects as summaries. Malformed files are skipped."""
    cards = _cards_by_id()
    out: list[dict[str, Any]] = []
    for path in _project_files():
        try:
            project = load_project(path)
        except ProjectError:
            continue
        out.append(
            {
                "id": project.id,
                "name": project.name,
                "van": {
                    "make": project.van.make,
                    "model": project.van.model,
                    "dimensions_mm": {
                        "length": project.van.length_mm,
                        "width": project.van.width_mm,
                        "height": project.van.height_mm,
                    },
                    "max_payload_kg": project.van.max_payload_kg,
                },
                "instance_count": len(project.instances),
                "total_weight_kg": _total_weight(project, cards),
            }
        )
    return out


def _find(project_id: str) -> Optional[Project]:
    for path in _project_files():
        try:
            project = load_project(path)
        except ProjectError:
            continue
        if project.id == project_id:
            return project
    return None


def get_project(project_id: str) -> Optional[dict[str, Any]]:
    """Full project detail, with each instance's module resolved for convenience."""
    project = _find(project_id)
    if project is None:
        return None
    cards = _cards_by_id()
    return {
        "id": project.id,
        "name": project.name,
        "van": _van_dict(project.van),
        "module_instances": [
            _instance_dict(inst, cards.get(inst.module_id)) for inst in project.instances
        ],
    }


def _build_status_dict(project: Project) -> dict[str, Any]:
    """Validation/build-status payload for a saved or in-memory edited project."""
    index = index_modules()
    specs = layout_validation.module_specs()

    issues = containment_issues(project, index)
    within_bounds = len(issues) == 0

    validation = layout_validation.validate_layout(project, specs)
    payload = validation.payload
    collisions = [
        {"instance_a": c.instance_a, "instance_b": c.instance_b, "overlap_mm": c.overlap_mm}
        for c in validation.collisions
    ]
    clearance = [
        {
            "instance_a": w.instance_a,
            "instance_b": w.instance_b,
            "kind": w.kind,
            "gap_mm": w.gap_mm,
            "required_mm": w.required_mm,
        }
        for w in validation.clearance_warnings
    ]

    build_ready = within_bounds and not collisions and payload.weight_ok

    return {
        "project_id": project.id,
        "instance_count": len(project.instances),
        # Payload (existing keys kept stable; max_payload_kg may be null).
        "total_weight_kg": payload.total_weight_kg,
        "max_payload_kg": payload.limit_kg,
        "payload_headroom_kg": payload.remaining_kg,
        "payload_ok": payload.weight_ok,
        "limit_enforced": payload.limit_enforced,
        # Van-box containment (existing keys).
        "within_bounds": within_bounds,
        "bounds_issues": issues,
        # Collision + clearance (new).
        "collisions": collisions,
        "collision_count": len(collisions),
        "clearance_warnings": clearance,
        "clearance_not_enforced": list(validation.clearance_not_enforced),
        # Overall.
        "build_ready": build_ready,
    }


def project_build_status(project_id: str) -> Optional[dict[str, Any]]:
    """Build status for the saved project on disk; None if not found."""
    project = _find(project_id)
    if project is None:
        return None
    return _build_status_dict(project)


def _apply_overrides(project: Project, overrides: list[dict[str, Any]]) -> Project:
    """Return a new Project with position/rotation replaced for matching ids.

    In-memory only — never writes to disk. Raises LayoutEditError for an
    unknown instance_id.
    """
    by_id = {inst.instance_id: inst for inst in project.instances}
    edited: dict[str, ModuleInstance] = {}
    for ov in overrides:
        iid = ov.get("instance_id")
        if iid not in by_id:
            raise LayoutEditError(f"unknown instance_id: {iid!r}")
        pos = ov["position_mm"]
        edited[iid] = replace(
            by_id[iid],
            position_mm=Vec3(x=int(pos["x"]), y=int(pos["y"]), z=int(pos["z"])),
            rotation_deg=float(ov["rotation_deg"]),
        )
    new_instances = tuple(edited.get(inst.instance_id, inst) for inst in project.instances)
    return replace(project, instances=new_instances)


def validate_layout_overrides(
    project_id: str, overrides: list[dict[str, Any]]
) -> Optional[dict[str, Any]]:
    """Validate the saved project with in-memory instance overrides applied.

    Returns the same shape as ``project_build_status``; None if the project
    is not found. Raises LayoutEditError for an unknown instance_id.
    """
    project = _find(project_id)
    if project is None:
        return None
    return _build_status_dict(_apply_overrides(project, overrides))
