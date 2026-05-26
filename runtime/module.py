"""Typed runtime view of a DraftMyVan manifest entry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class ConsumerError(Exception):
    """Manifest is missing a required field for runtime consumption.

    The runtime is the *consumer* of an already-validated manifest. If
    this exception is raised, something upstream let a malformed
    manifest through (schema validator, code review, or hand-edit).
    """


@dataclass(frozen=True)
class Dimensions:
    """A module's external bounding box, in millimetres (the manifest's truth).

    Convenience metre accessors are provided for runtimes whose native unit
    is metres (Blender, glTF, most game engines). The mm fields remain the
    canonical representation.
    """

    width_mm: int
    depth_mm: int
    height_mm: int

    @property
    def width_m(self) -> float:
        return self.width_mm / 1000.0

    @property
    def depth_m(self) -> float:
        return self.depth_mm / 1000.0

    @property
    def height_m(self) -> float:
        return self.height_mm / 1000.0


@dataclass(frozen=True)
class Module:
    """Runtime-side view of a manifest entry.

    Constructed by `runtime.load_module.load_module(manifest_path)`.
    Treat fields as read-only — the contract belongs to the manifest, not
    to in-memory copies.
    """

    id: str
    type: str
    dimensions: Dimensions
    anchor: str
    placement: str
    glb_path: str  # repo-relative, as written in manifest.visual.glb_path
    resolved_asset_path: Path  # on-disk path the runtime would actually open
    asset_exists: bool

    @property
    def consumable(self) -> bool:
        """True iff the manifest loaded cleanly AND the GLB exists on disk.

        Note: this is the runtime's "can I do something with this right now?"
        check, not a validation gate. A consumable=True module has been read
        but not re-validated for dimensional or origin correctness.
        """
        return self.asset_exists
