"""Tests for POST /api/projects/{id}/save-layout (validated persistence).

Writes go to a TEMP project directory (via DRAFTMYVAN_PROJECTS_DIR) seeded
with a copy of the real example, so the committed project is never mutated.
Requires the API/dev deps; skips cleanly when absent.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

REAL_PROJECT = REPO_ROOT / "examples" / "projects" / "weekend_explorer.json"

try:
    from fastapi.testclient import TestClient  # noqa: E402

    from api.main import app  # noqa: E402

    _DEPS_AVAILABLE = True
except ImportError:
    _DEPS_AVAILABLE = False


def _setup_tmp() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="dmv_save_"))
    shutil.copy(REAL_PROJECT, tmp / "weekend_explorer.json")
    os.environ["DRAFTMYVAN_PROJECTS_DIR"] = str(tmp)
    return tmp


def _teardown(tmp: Path) -> None:
    os.environ.pop("DRAFTMYVAN_PROJECTS_DIR", None)
    shutil.rmtree(tmp, ignore_errors=True)


def _instances(x: int = 0, y: int = 0, z: int = 0, rot: float = 0, module_id: str = "galley_1000_sink_left_oak"):
    return [
        {
            "instance_id": "galley_back_left",
            "module_id": module_id,
            "position_mm": {"x": x, "y": y, "z": z},
            "rotation_deg": rot,
            "zone": "kitchen",
            "visible": True,
        }
    ]


def _saved_pos(tmp: Path) -> dict:
    data = json.loads((tmp / "weekend_explorer.json").read_text(encoding="utf-8"))
    return data["module_instances"][0]["position_mm"]


def test_save_valid_layout_persists_and_reload_returns_it() -> None:
    tmp = _setup_tmp()
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/projects/weekend_explorer/save-layout",
            json={"instances": _instances(y=1000)},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["saved"] is True, body
        assert body["build_ready"] is True, body
        # Written to disk.
        assert _saved_pos(tmp) == {"x": 0, "y": 1000, "z": 0}, _saved_pos(tmp)
        # Reload via the API returns the saved position.
        reload = client.get("/api/projects/weekend_explorer").json()
        assert reload["module_instances"][0]["position_mm"]["y"] == 1000, reload
        # The committed example file is untouched.
        real = json.loads(REAL_PROJECT.read_text(encoding="utf-8"))
        assert real["module_instances"][0]["position_mm"] == {"x": 0, "y": 0, "z": 0}
    finally:
        _teardown(tmp)


def test_out_of_bounds_rejected_by_default() -> None:
    tmp = _setup_tmp()
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/projects/weekend_explorer/save-layout",
            json={"instances": _instances(x=2000)},
        )
        assert resp.status_code == 409, resp.text
        # File NOT modified.
        assert _saved_pos(tmp) == {"x": 0, "y": 0, "z": 0}, _saved_pos(tmp)
    finally:
        _teardown(tmp)


def test_out_of_bounds_written_with_allow_invalid() -> None:
    tmp = _setup_tmp()
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/projects/weekend_explorer/save-layout",
            json={"instances": _instances(x=2000), "allow_invalid": True},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["build_ready"] is False, resp.text
        assert _saved_pos(tmp) == {"x": 2000, "y": 0, "z": 0}, _saved_pos(tmp)
    finally:
        _teardown(tmp)


def test_unknown_project_returns_404() -> None:
    tmp = _setup_tmp()
    try:
        client = TestClient(app)
        resp = client.post("/api/projects/nope/save-layout", json={"instances": _instances()})
        assert resp.status_code == 404, resp.text
    finally:
        _teardown(tmp)


def test_unknown_module_id_returns_422() -> None:
    tmp = _setup_tmp()
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/projects/weekend_explorer/save-layout",
            json={"instances": _instances(module_id="does_not_exist")},
        )
        assert resp.status_code == 422, resp.text
        # File NOT modified.
        assert _saved_pos(tmp) == {"x": 0, "y": 0, "z": 0}, _saved_pos(tmp)
    finally:
        _teardown(tmp)


def test_fractional_position_rejected() -> None:
    tmp = _setup_tmp()
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/projects/weekend_explorer/save-layout",
            json={"instances": [{
                "instance_id": "galley_back_left",
                "module_id": "galley_1000_sink_left_oak",
                "position_mm": {"x": 10.5, "y": 0, "z": 0},
                "rotation_deg": 0,
                "zone": "kitchen",
                "visible": True,
            }]},
        )
        assert resp.status_code == 422, resp.text
    finally:
        _teardown(tmp)


def main() -> int:
    if not _DEPS_AVAILABLE:
        print('SKIP  api save-layout suite: fastapi/httpx not installed (pip install -e ".[dev]")')
        print()
        print("0/0 passed (skipped)")
        return 0

    tests = [
        test_save_valid_layout_persists_and_reload_returns_it,
        test_out_of_bounds_rejected_by_default,
        test_out_of_bounds_written_with_allow_invalid,
        test_unknown_project_returns_404,
        test_unknown_module_id_returns_422,
        test_fractional_position_rejected,
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
