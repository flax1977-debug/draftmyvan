"""DraftMyVan configurator HTTP API.

A thin FastAPI layer over the existing manifest contract. It does not
re-implement any contract logic: future endpoints read modules through
``runtime.load_module`` / ``runtime.package_report`` and validate through
``tools.validate_manifest``. This skeleton exposes only a health check and a
static mount for the committed GLB assets.

Run the dev server (after ``pip install -e ".[dev]"``):

    uvicorn api.main:app --reload --port 8000

Then:

    curl http://127.0.0.1:8000/api/health
    curl http://127.0.0.1:8000/assets/galley_1000.glb --output /tmp/g.glb
"""
