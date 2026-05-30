"""Project endpoints serialization.

Reuses runtime.project (typed load + containment) and the existing catalog
(module weight / glb_url) so no contract or geometry logic is duplicated here.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

from runtime import layout_validation
from runtime.project import (
    EXAMPLES_DIR,
    Project,
    ProjectError,
    Van,
    containment_issues,
    index_modules,
    load_project,
    parse_project,
)

from . import catalog


class InvalidLayoutError(ValueError):
    """A save was rejected because the layout is not build-ready."""

    def __init__(self, status: dict[str, Any]) -> None:
        super().__init__("layout is not build-ready")
        self.status = status


def projects_dir() -> Path:
    """Directory holding project files.

    Overridable via DRAFTMYVAN_PROJECTS_DIR so tests can point at a temp copy
    and never mutate the committed example project.
    """
    override = os.environ.get("DRAFTMYVAN_PROJECTS_DIR")
    return Path(override) if override else EXAMPLES_DIR / "projects"


def _project_files() -> list[Path]:
    return sorted(p for p in projects_dir().glob("*.json") if p.is_file())


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


def _find_path(project_id: str) -> Optional[Path]:
    """The on-disk file whose project id matches, or None."""
    for path in _project_files():
        try:
            project = load_project(path)
        except ProjectError:
            continue
        if project.id == project_id:
            return path
    return None


def _atomic_write_json(path: Path, data: Any) -> None:
    """Write JSON via a temp file in the same dir, then atomically replace."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)  # atomic on the same filesystem
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def save_layout(
    project_id: str,
    instances: list[dict[str, Any]],
    *,
    allow_invalid: bool = False,
) -> Optional[dict[str, Any]]:
    """Validate and persist edited module_instances for a project.

    Returns the saved build-status (with "saved": True); None if the project
    is not found. Raises ProjectError for an invalid layout (unknown module
    id, bad positions, duplicate instance ids), and InvalidLayoutError when
    the layout is not build-ready and allow_invalid is False. Writes only the
    one project file, atomically. Never creates a DB/auth/accounts.
    """
    candidate = _candidate(project_id, instances)
    if candidate is None:
        return None
    path, merged, status = candidate

    if not allow_invalid and not status["build_ready"]:
        raise InvalidLayoutError(status)

    _atomic_write_json(path, merged)
    return {**status, "saved": True}


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


def _candidate(
    project_id: str, instances: list[dict[str, Any]]
) -> Optional[tuple[Path, dict[str, Any], dict[str, Any]]]:
    """Build + validate a candidate project from a full instance list.

    The candidate is the saved project (van/name/id preserved) with its
    module_instances REPLACED by the payload — so it covers edited positions
    AND newly added instances. In-memory only; never writes. Returns
    (path, merged_dict, build_status) or None if the project is not found.
    Raises ProjectError for an invalid layout (unknown module id, non-integer
    positions, duplicate/invalid instances).
    """
    path = _find_path(project_id)
    if path is None:
        return None
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    merged = {**raw, "module_instances": instances}
    project = parse_project(merged, EXAMPLES_DIR)
    status = _build_status_dict(project)
    return path, merged, status


def validate_layout(
    project_id: str, instances: list[dict[str, Any]]
) -> Optional[dict[str, Any]]:
    """Validate a candidate full instance list without writing. None if unknown."""
    candidate = _candidate(project_id, instances)
    return candidate[2] if candidate is not None else None
