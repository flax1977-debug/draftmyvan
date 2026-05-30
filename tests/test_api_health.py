"""Smoke tests for the DraftMyVan API skeleton (api/).

Pure HTTP-layer checks against the in-process app via FastAPI's TestClient:
  * GET /api/health returns 200 with the expected service info;
  * the committed GLB asset is served from the /assets static mount.

Requires the optional API/dev dependencies (``pip install -e ".[dev]"``).
If FastAPI/httpx are not installed this suite SKIPS cleanly (exit 0) so a
fresh clone without the web deps still gets a green pure-contract suite.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

try:
    from fastapi.testclient import TestClient  # noqa: E402

    from api.main import API_VERSION, app  # noqa: E402

    _DEPS_AVAILABLE = True
except ImportError:
    _DEPS_AVAILABLE = False


def test_health_returns_ok() -> None:
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200, resp.status_code
    body = resp.json()
    assert body["status"] == "ok", body
    assert body["service"] == "draftmyvan-api", body
    assert body["version"] == API_VERSION, body
    assert body["assets_dir_present"] is True, body


def test_committed_glb_is_served() -> None:
    client = TestClient(app)
    resp = client.get("/assets/galley_1000.glb")
    assert resp.status_code == 200, resp.status_code
    assert resp.content[:4] == b"glTF", resp.content[:4]


def main() -> int:
    if not _DEPS_AVAILABLE:
        print("SKIP  api health suite: fastapi/httpx not installed "
              '(run: pip install -e ".[dev]")')
        print()
        print("0/0 passed (skipped)")
        return 0

    tests = [
        test_health_returns_ok,
        test_committed_glb_is_served,
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
