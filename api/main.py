"""FastAPI application for the DraftMyVan configurator.

Endpoints (all read-only):
  - GET /api/health             liveness/info probe.
  - GET /api/modules            catalog cards for every committed module.
  - GET /api/modules/{id}       selected-module detail (404 if unknown).
  - GET /api/build-status       aggregate readiness for the Build-Ready badge.
  - GET /assets/<file>          static mount for committed GLB assets so the
                                browser 3D view can load them directly.

Serialization/aggregation reuses the existing runtime consumer
(runtime.load_module / runtime.package_report) and the schema gate
(tools/validate_manifest.py) rather than duplicating contract logic.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import build_status, catalog, projects


class PositionIn(BaseModel):
    x: int
    y: int
    z: int


class InstanceOverrideIn(BaseModel):
    instance_id: str
    position_mm: PositionIn
    rotation_deg: float


class LayoutEditIn(BaseModel):
    """Unsaved local edits: position/rotation overrides keyed by instance_id."""

    instances: list[InstanceOverrideIn] = []

API_VERSION = "0.1.0"

# api/ lives at the repo root, alongside examples/.
REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = REPO_ROOT / "examples" / "assets"

# The manifest writes glb_path as "assets/<file>.glb", so mounting the
# committed assets at /assets makes the browser path mirror the manifest path.
ASSETS_MOUNT = "/assets"

# Local frontend dev servers. The configurator SPA (Vite) runs on a different
# origin during development, so it needs explicit CORS access to the API.
DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app = FastAPI(
    title="DraftMyVan API",
    version=API_VERSION,
    description="Configurator API over the DraftMyVan module manifest contract.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=DEV_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, object]:
    """Liveness probe plus enough info to confirm asset wiring is live."""
    return {
        "status": "ok",
        "service": "draftmyvan-api",
        "version": API_VERSION,
        "assets_dir_present": ASSETS_DIR.is_dir(),
    }


@app.get("/api/modules")
def list_modules() -> dict[str, object]:
    """Catalog: every committed module as a lightweight card."""
    return {"modules": catalog.list_modules()}


@app.get("/api/modules/{module_id}")
def get_module(module_id: str) -> dict[str, object]:
    """Selected-module detail; 404 if no manifest has that id."""
    module = catalog.get_module(module_id)
    if module is None:
        raise HTTPException(status_code=404, detail=f"module not found: {module_id}")
    return module


@app.get("/api/build-status")
def get_build_status() -> dict[str, object]:
    """Aggregate readiness for the Build-Ready badge and status bar."""
    return build_status.compute()


@app.get("/api/projects")
def list_projects() -> dict[str, object]:
    """All committed projects as summaries."""
    return {"projects": projects.list_projects()}


@app.get("/api/projects/{project_id}")
def get_project(project_id: str) -> dict[str, object]:
    """Full project detail; 404 if no project has that id."""
    project = projects.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"project not found: {project_id}")
    return project


@app.get("/api/projects/{project_id}/build-status")
def get_project_build_status(project_id: str) -> dict[str, object]:
    """Per-project readiness for the saved project: collision/clearance/payload."""
    status = projects.project_build_status(project_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"project not found: {project_id}")
    return status


@app.post("/api/projects/{project_id}/validate-layout")
def validate_project_layout(project_id: str, edit: LayoutEditIn) -> dict[str, object]:
    """Validate the saved project with unsaved local edits applied (no writes).

    Returns the same shape as build-status. 404 if the project is unknown,
    422 if an override references an unknown instance_id.
    """
    overrides = [o.model_dump() for o in edit.instances]
    try:
        status = projects.validate_layout_overrides(project_id, overrides)
    except projects.LayoutEditError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    if status is None:
        raise HTTPException(status_code=404, detail=f"project not found: {project_id}")
    return status


# Mounted last so it never shadows /api routes.
if ASSETS_DIR.is_dir():
    app.mount(ASSETS_MOUNT, StaticFiles(directory=ASSETS_DIR), name="assets")
