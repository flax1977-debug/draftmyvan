"""Catalog serialization for the configurator API.

Turns committed module manifests into the JSON shapes the frontend needs:
a lightweight *card* (catalog list) and a fuller *detail* (selected-module
inspector). The validated core (id, type, dimensions, anchor, placement,
glb path, asset presence) comes from ``runtime.load_module`` — the contract
reader — so no parsing/validation logic is duplicated here. Presentational
extras the typed ``Module`` does not carry (weight, material slots, hardware,
clearances, rules) are read from the raw manifest for display only.

Fields the target UI shows but the manifest schema does not yet define
(``cost``, ``finish``, ``display_name``, ``category``, ``thumbnail``) are
returned as ``null`` rather than fabricated. They become real when the schema
gains those fields.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from runtime.load_module import ConsumerError, load_module
from runtime.module import Module

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples"

# Must match the static mount prefix in api.main.
ASSETS_MOUNT = "/assets"

# Honestly-absent: present in the target UI, not in the manifest schema yet.
ABSENT: None = None


def _manifest_files() -> list[Path]:
    return sorted(p for p in EXAMPLES_DIR.glob("*.json") if p.is_file())


def _read_raw(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _glb_url(glb_path: str) -> str:
    """manifest ``assets/<file>.glb`` -> browser ``/assets/<file>.glb``."""
    return f"{ASSETS_MOUNT}/{Path(glb_path).name}"


def card(module: Module, raw: dict[str, Any]) -> dict[str, Any]:
    """Lightweight shape for a catalog list entry."""
    manufacturing = raw.get("manufacturing", {})
    return {
        "id": module.id,
        "type": module.type,
        "anchor": module.anchor,
        "display_name": ABSENT,  # no name field in the manifest
        "category": ABSENT,      # no category field in the manifest
        "dimensions_mm": {
            "width": module.dimensions.width_mm,
            "depth": module.dimensions.depth_mm,
            "height": module.dimensions.height_mm,
        },
        "weight_kg": manufacturing.get("weight_kg"),
        "cost_gbp": ABSENT,      # not in the manifest yet
        "glb_url": _glb_url(module.glb_path),
        "thumbnail_url": ABSENT,
        "asset_present": module.asset_exists,
    }


def detail(module: Module, raw: dict[str, Any]) -> dict[str, Any]:
    """Fuller shape for the selected-module inspector."""
    visual = raw.get("visual", {})
    manufacturing = raw.get("manufacturing", {})
    rules = raw.get("rules") or ABSENT
    hardware = manufacturing.get("hardware")
    out = card(module, raw)
    out.update(
        {
            "anchor": module.anchor,
            "placement": module.placement,
            "clearances": raw.get("clearances"),
            "material_slots": visual.get("material_slots"),
            "collision_proxy": visual.get("collision_proxy"),
            "finish": ABSENT,  # not in the manifest yet
            "plywood_thickness_mm": manufacturing.get("plywood_thickness_mm"),
            "fusion_template": manufacturing.get("fusion_template"),
            "hardware": hardware,
            # Count of hardware line items (e.g. "hinges_4x" is one line item),
            # not a parsed total piece count — that would be manufacturing logic.
            "hardware_line_items": len(hardware) if isinstance(hardware, list) else ABSENT,
            "rules": rules,
        }
    )
    return out


def list_modules() -> list[dict[str, Any]]:
    """All committed modules as catalog cards.

    Malformed manifests are skipped here (the catalog is a display list);
    structural integrity is the job of the build-status endpoint.
    """
    cards: list[dict[str, Any]] = []
    for path in _manifest_files():
        try:
            module = load_module(path)
            raw = _read_raw(path)
        except (ConsumerError, ValueError, OSError):
            continue
        cards.append(card(module, raw))
    return cards


def get_module(module_id: str) -> Optional[dict[str, Any]]:
    """Detail for one module by id, or ``None`` if no manifest matches."""
    for path in _manifest_files():
        try:
            module = load_module(path)
        except ConsumerError:
            continue
        if module.id == module_id:
            return detail(module, _read_raw(path))
    return None
