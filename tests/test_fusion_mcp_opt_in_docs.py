"""Tests for the Fusion MCP opt-in documentation and smoke helper."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "mcp"))

import smoke_fusion_bridge as smoke  # noqa: E402


OPT_IN_DOC = REPO_ROOT / "docs" / "FUSION_MCP_OPT_IN_CONFIG.md"


def _doc_text() -> str:
    return OPT_IN_DOC.read_text(encoding="utf-8")


def test_opt_in_doc_says_global_config_is_not_modified() -> None:
    text = _doc_text().lower()
    normalized = " ".join(text.split())
    assert "does not modify global mcp configuration" in normalized
    assert "nothing in this repo edits" in normalized
    assert "~/.codex" in text
    assert "~/.claude" in text


def test_opt_in_doc_lists_only_four_allowlisted_tools() -> None:
    text = _doc_text()
    for tool in (
        "check_fusion_payload",
        "check_geometry_plan",
        "dry_run_geometry",
        "report_manual_verification_status",
    ):
        assert f"- `{tool}`" in text
    assert "Only these four allowlisted tools exist" in text


def test_opt_in_doc_names_security_boundaries() -> None:
    text = _doc_text().lower()
    assert "does not expose arbitrary shell execution" in text
    assert "no localhost listener" in text
    assert "fusion geometry execution remains manual/deferred" in text
    assert "manufacturing-ready output" in text


def test_opt_in_doc_marks_config_snippets_as_examples_only() -> None:
    text = _doc_text().lower()
    assert "example only" in text
    assert "pseudo-config only" in text
    assert "verify the exact current codex documentation" in text
    assert "verify the exact location and schema" in text


def test_smoke_helper_rejects_unknown_tools() -> None:
    assert smoke.unknown_tool_rejected() is True


def test_smoke_helper_runs_without_fusion() -> None:
    lines = smoke.smoke_check()
    assert "tools/list exposed exactly four allowlisted tools" in lines
    assert "dry_run_geometry returned FUSION GEOMETRY DRY RUN VALID" in lines


def main() -> int:
    tests = [
        test_opt_in_doc_says_global_config_is_not_modified,
        test_opt_in_doc_lists_only_four_allowlisted_tools,
        test_opt_in_doc_names_security_boundaries,
        test_opt_in_doc_marks_config_snippets_as_examples_only,
        test_smoke_helper_rejects_unknown_tools,
        test_smoke_helper_runs_without_fusion,
    ]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS  {test.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {test.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"ERROR {test.__name__}: {e}")
    print()
    print(f"{len(tests) - failed}/{len(tests)} passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
