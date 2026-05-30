"""Tests for the project endpoints (GET /api/projects[/{id}[/build-status]]).

Requires the optional API/dev dependencies; skips cleanly when absent.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

try:
    from fastapi.testclient import TestClient  # noqa: E402

    from api.main import app  # noqa: E402

    _DEPS_AVAILABLE = True
except ImportError:
    _DEPS_AVAILABLE = False

PROJECT_ID = "weekend_explorer"


def test_list_projects_includes_example() -> None:
    client = TestClient(app)
    resp = client.get("/api/projects")
    assert resp.status_code == 200, resp.status_code
    projects = resp.json()["projects"]
    p = next(p for p in projects if p["id"] == PROJECT_ID)
    assert p["name"] == "Weekend Explorer", p
    assert p["instance_count"] == 1, p
    assert p["total_weight_kg"] == 45, p
    assert p["van"]["dimensions_mm"] == {"length": 5932, "width": 2020, "height": 2760}, p


def test_project_detail_resolves_module() -> None:
    client = TestClient(app)
    resp = client.get(f"/api/projects/{PROJECT_ID}")
    assert resp.status_code == 200, resp.status_code
    body = resp.json()
    assert body["van"]["make"] == "Mercedes-Benz", body
    inst = body["module_instances"][0]
    assert inst["instance_id"] == "galley_back_left", inst
    assert inst["module_id"] == "galley_1000_sink_left_oak", inst
    assert inst["position_mm"] == {"x": 0, "y": 0, "z": 0}, inst
    assert inst["zone"] == "kitchen", inst
    # Resolved module convenience block.
    assert inst["module"]["weight_kg"] == 45, inst
    assert inst["module"]["glb_url"] == "/assets/galley_1000.glb", inst


def test_project_build_status() -> None:
    client = TestClient(app)
    resp = client.get(f"/api/projects/{PROJECT_ID}/build-status")
    assert resp.status_code == 200, resp.status_code
    body = resp.json()
    assert body["total_weight_kg"] == 45, body
    assert body["max_payload_kg"] == 1200, body
    assert body["payload_ok"] is True, body
    assert body["within_bounds"] is True, body
    assert body["bounds_issues"] == [], body
    assert body["build_ready"] is True, body
    # Task 7 fields.
    assert body["collisions"] == [], body
    assert body["collision_count"] == 0, body
    assert body["clearance_warnings"] == [], body
    assert "front_clearance" in body["clearance_not_enforced"], body
    assert body["limit_enforced"] is True, body


def test_unknown_project_returns_404() -> None:
    client = TestClient(app)
    assert client.get("/api/projects/nope").status_code == 404
    assert client.get("/api/projects/nope/build-status").status_code == 404


def test_validate_layout_noop_matches_saved() -> None:
    client = TestClient(app)
    resp = client.post(f"/api/projects/{PROJECT_ID}/validate-layout", json={"instances": []})
    assert resp.status_code == 200, resp.status_code
    body = resp.json()
    assert body["build_ready"] is True, body
    assert body["within_bounds"] is True, body
    assert body["collision_count"] == 0, body


def test_validate_layout_detects_out_of_bounds_edit() -> None:
    client = TestClient(app)
    # Galley width 1000 mm; anchor at x=2000 pushes it past the 2020 mm width.
    resp = client.post(
        f"/api/projects/{PROJECT_ID}/validate-layout",
        json={"instances": [{"instance_id": "galley_back_left",
                             "position_mm": {"x": 2000, "y": 0, "z": 0},
                             "rotation_deg": 0}]},
    )
    assert resp.status_code == 200, resp.status_code
    body = resp.json()
    assert body["within_bounds"] is False, body
    assert len(body["bounds_issues"]) == 1, body
    assert body["build_ready"] is False, body


def test_validate_layout_unknown_instance_returns_422() -> None:
    client = TestClient(app)
    resp = client.post(
        f"/api/projects/{PROJECT_ID}/validate-layout",
        json={"instances": [{"instance_id": "nope",
                             "position_mm": {"x": 0, "y": 0, "z": 0},
                             "rotation_deg": 0}]},
    )
    assert resp.status_code == 422, resp.status_code


def test_validate_layout_unknown_project_returns_404() -> None:
    client = TestClient(app)
    resp = client.post("/api/projects/nope/validate-layout", json={"instances": []})
    assert resp.status_code == 404, resp.status_code


def main() -> int:
    if not _DEPS_AVAILABLE:
        print('SKIP  api projects suite: fastapi/httpx not installed (pip install -e ".[dev]")')
        print()
        print("0/0 passed (skipped)")
        return 0

    tests = [
        test_list_projects_includes_example,
        test_project_detail_resolves_module,
        test_project_build_status,
        test_unknown_project_returns_404,
        test_validate_layout_noop_matches_saved,
        test_validate_layout_detects_out_of_bounds_edit,
        test_validate_layout_unknown_instance_returns_422,
        test_validate_layout_unknown_project_returns_404,
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
