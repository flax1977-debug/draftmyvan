"""Tests for GET /api/build-status.

Verifies the aggregate readiness payload reflects real checks (schema valid,
assets present, summed weight) and reports the not-yet-implemented checks
(collisions, weight limit) honestly rather than faking a pass.

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


def test_build_status_is_ready_for_current_catalog() -> None:
    client = TestClient(app)
    resp = client.get("/api/build-status")
    assert resp.status_code == 200, resp.status_code
    body = resp.json()
    assert body["build_ready"] is True, body
    assert body["all_valid"] is True, body
    assert body["collisions"] == [], body
    assert body["weight_ok"] is True, body
    assert body["module_count"] == 2, body
    assert body["missing_assets"] == 0, body
    assert body["schema_errors"] == {}, body
    assert body["package_errors"] == [], body


def test_summed_weight_matches_manifest() -> None:
    client = TestClient(app)
    body = client.get("/api/build-status").json()
    # galley_1000 (45 kg) + bench_900 (28 kg).
    assert body["total_weight_kg"] == 73, body


def test_not_yet_enforced_checks_are_reported_honestly() -> None:
    client = TestClient(app)
    body = client.get("/api/build-status").json()
    # No collision engine yet: empty list AND an explicit "not implemented" flag.
    assert body["collision_check_implemented"] is False, body
    # No van payload budget yet: limit is null, not a fabricated number.
    assert body["weight_limit_kg"] is None, body


def main() -> int:
    if not _DEPS_AVAILABLE:
        print("SKIP  api build-status suite: fastapi/httpx not installed "
              '(run: pip install -e ".[dev]")')
        print()
        print("0/0 passed (skipped)")
        return 0

    tests = [
        test_build_status_is_ready_for_current_catalog,
        test_summed_weight_matches_manifest,
        test_not_yet_enforced_checks_are_reported_honestly,
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
