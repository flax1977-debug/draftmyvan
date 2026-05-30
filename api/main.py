"""FastAPI application skeleton for the DraftMyVan configurator.

Task 1 scope (intentionally minimal):
  - GET /api/health        liveness/info probe.
  - GET /assets/<file>     static mount for committed GLB assets so the
                           browser 3D view can load them directly.

Catalog, selected-module, and build-status endpoints arrive in later tasks
and will reuse the existing runtime consumer rather than duplicate it.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import catalog

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
    allow_methods=["GET"],
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


# Mounted last so it never shadows /api routes.
if ASSETS_DIR.is_dir():
    app.mount(ASSETS_MOUNT, StaticFiles(directory=ASSETS_DIR), name="assets")
