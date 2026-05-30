"""Tests for the catalog endpoints (GET /api/modules, /api/modules/{id}).

Verifies the API surfaces real manifest data (dims, weight, anchor,
materials from examples/galley_1000.json) and that fields absent from the
manifest schema (cost, finish, display_name, category) come back as null
rather than fabricated values.

Requires the optional API/dev dependencies (``pip install -e ".[dev]"``);
skips cleanly when they are absent.
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

GALLEY_ID = "galley_1000_sink_left_oak"


def test_list_modules_includes_galley() -> None:
    client = TestClient(app)
    resp = client.get("/api/modules")
    assert resp.status_code == 200, resp.status_code
    modules = resp.json()["modules"]
    ids = [m["id"] for m in modules]
    assert GALLEY_ID in ids, ids
    galley = next(m for m in modules if m["id"] == GALLEY_ID)
    assert galley["type"] == "cabinet", galley
    assert galley["dimensions_mm"] == {"width": 1000, "depth": 520, "height": 900}, galley
    assert galley["weight_kg"] == 45, galley
    assert galley["glb_url"] == "/assets/galley_1000.glb", galley
    assert galley["asset_present"] is True, galley


def test_card_absent_fields_are_null_not_faked() -> None:
    client = TestClient(app)
    galley = next(
        m for m in client.get("/api/modules").json()["modules"] if m["id"] == GALLEY_ID
    )
    for field in ("cost_gbp", "display_name", "category", "thumbnail_url"):
        assert galley[field] is None, (field, galley[field])


def test_module_detail_returns_expected_fields() -> None:
    client = TestClient(app)
    resp = client.get(f"/api/modules/{GALLEY_ID}")
    assert resp.status_code == 200, resp.status_code
    detail = resp.json()
    assert detail["anchor"] == "floor_back_left", detail
    assert detail["placement"] == "floor", detail
    assert detail["material_slots"] == ["oak_body", "sink_metal"], detail
    assert detail["collision_proxy"] == "UCX_galley_1000", detail
    assert detail["plywood_thickness_mm"] == 18, detail
    assert detail["fusion_template"] == "galley_v1", detail
    assert detail["hardware"] == ["hinges_4x", "runners_2x"], detail
    assert detail["hardware_line_items"] == 2, detail
    assert detail["clearances"] == {"front_mm": 450, "sides_mm": 20, "above_mm": 50}, detail
    assert detail["rules"]["build_difficulty"] == "medium", detail
    # Absent-in-manifest fields stay null.
    assert detail["finish"] is None, detail
    assert detail["cost_gbp"] is None, detail


def test_unknown_module_returns_404() -> None:
    client = TestClient(app)
    resp = client.get("/api/modules/does_not_exist")
    assert resp.status_code == 404, resp.status_code


def main() -> int:
    if not _DEPS_AVAILABLE:
        print("SKIP  api modules suite: fastapi/httpx not installed "
              '(run: pip install -e ".[dev]")')
        print()
        print("0/0 passed (skipped)")
        return 0

    tests = [
        test_list_modules_includes_galley,
        test_card_absent_fields_are_null_not_faked,
        test_module_detail_returns_expected_fields,
        test_unknown_module_returns_404,
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
