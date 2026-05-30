"""Tests for the extraction-readiness helper (pure-Python static checks).

These tests exercise the cheap static checks only — file existence and
the host-app-reference grep. They do **not** invoke the dynamic mode
(`--include-dynamic`), because that would recursively run every other
test module via subprocess; the CI already runs those suites directly,
so doing it again here would be wasteful and circular.
"""

from __future__ import annotations

import io
import shutil
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "handoff"))

import check_handoff_ready as h  # noqa: E402


# ---------------------------------------------------------------------------
# Required-file checker — happy path and negative
# ---------------------------------------------------------------------------

def test_required_files_pass_on_current_repo() -> None:
    ok, lines = h.check_required_files(REPO_ROOT)
    assert ok, "\n".join(lines)
    # Spot-check a few representative paths.
    joined = "\n".join(lines)
    for rel in (
        "manifest.schema.json",
        "examples/galley_1000.json",
        "examples/assets/galley_1000.glb",
        "examples/assets/galley_1000.asset_acceptance.json",
        "examples/assets/candidates/README.md",
        "examples/assets/candidates/PROMOTION_CRITERIA.md",
        "examples/assets/candidates/candidate_review_checklist.md",
        "examples/assets/candidates/galley_1000_candidate.glb",
        "examples/assets/candidates/galley_1000_candidate.asset_acceptance.json",
        "examples/assets/candidates/galley_1000_candidate_review.json",
        "examples/assets/candidates/galley_1000_candidate_review.md",
        "examples/assets/candidates/galley_1000_candidate_visual_audit.json",
        "examples/assets/candidates/galley_1000_candidate_visual_audit.md",
        "examples/assets/candidates/galley_1000_candidate_render_evidence.json",
        "examples/assets/candidates/galley_1000_candidate_human_visual_review.json",
        "examples/assets/candidates/galley_1000_candidate_human_visual_review.md",
        "examples/assets/candidates/render_evidence/README.md",
        "examples/assets/candidates/render_evidence/galley_1000_candidate/front.png",
        "examples/assets/candidates/render_evidence/galley_1000_candidate/rear.png",
        "examples/assets/candidates/render_evidence/galley_1000_candidate/left.png",
        "examples/assets/candidates/render_evidence/galley_1000_candidate/right.png",
        "examples/assets/candidates/render_evidence/galley_1000_candidate/top.png",
        "examples/assets/candidates/render_evidence/galley_1000_candidate/three_quarter.png",
        "tests/fixtures/galley_1000_contract_box.glb",
        "runtime/load_module.py",
        "runtime/package_report.py",
        "tools/assets/validate_asset_acceptance.py",
        "tools/assets/validate_candidate_asset.py",
        "tools/assets/validate_candidate_review.py",
        "tools/assets/validate_candidate_visual_audit.py",
        "tools/assets/validate_render_evidence.py",
        "tools/assets/validate_human_visual_review.py",
        "tools/blender/_anchor_contract.py",
        "tools/blender/EXPORT_REAL_ASSET.md",
        "tools/blender/RENDER_CANDIDATE_AUDIT.md",
        "tools/blender/create_galley_candidate.py",
        "tools/blender/render_candidate_views.py",
        "tools/fusion/README.md",
        "tools/fusion/GALLEY_V1_PARAMETRIC_PLAN.md",
        "tools/fusion/galley_v1_parameter_map.json",
        "tools/fusion/validate_fusion_parameter_map.py",
        "tools/fusion/export_galley_v1_parameters.py",
        "tools/fusion/fusion_galley_v1_skeleton.py",
        "tools/fusion/check_fusion_payload.py",
        "tools/fusion/compute_galley_panels.py",
        "tools/fusion/export_galley_v1_panels.py",
        "tools/fusion/fusion_create_galley_v1.py",
        "tools/fusion/check_fusion_geometry_plan.py",
        "tools/fusion/RUN_FUSION_GEOMETRY_MANUAL.md",
        "tools/fusion/MANUAL_FUSION_GEOMETRY_CHECKLIST.md",
        "tools/fusion/fusion_command_bridge.py",
        "tools/mcp/fusion_bridge_server.py",
        "tools/mcp/smoke_fusion_bridge.py",
        "tools/blender/check_asset_ready.py",
        "docs/FUSION_MCP_BRIDGE.md",
        "docs/FUSION_MCP_OPT_IN_CONFIG.md",
        "tests/test_check_asset_ready.py",
        "HANDOFF.md",
        "EXTRACT_TO_REAL_REPO.md",
        "COMMANDS.md",
    ):
        assert f"[OK]   {rel}" in joined, f"missing required-file check for {rel}"


def test_required_files_fail_when_one_is_missing() -> None:
    # Build a temp project root that has *everything except* manifest.schema.json,
    # then point the checker at it.
    tmp = Path(tempfile.mkdtemp(prefix="dmv_handoff_"))
    try:
        for rel in h.REQUIRED_FILES:
            if rel == "manifest.schema.json":
                continue
            dest = tmp / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text("placeholder", encoding="utf-8")
        ok, lines = h.check_required_files(tmp)
        assert ok is False
        joined = "\n".join(lines)
        assert "[FAIL] missing file: manifest.schema.json" in joined
    finally:
        shutil.rmtree(tmp)


def test_required_file_fails_when_path_is_a_directory() -> None:
    # The Codex review caught this: path.exists() is too weak — a required
    # file path that has been replaced by a directory of the same name
    # would silently pass the old check. Build a tree where every required
    # path is satisfied except manifest.schema.json, which is a directory
    # instead of a file.
    tmp = Path(tempfile.mkdtemp(prefix="dmv_handoff_dir_"))
    try:
        for rel in h.REQUIRED_FILES:
            if rel == "manifest.schema.json":
                # Create it as a directory, not a file.
                (tmp / rel).mkdir(parents=True, exist_ok=True)
                continue
            dest = tmp / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text("placeholder", encoding="utf-8")
        ok, lines = h.check_required_files(tmp)
        assert ok is False, (
            "a directory at a required-file path must fail the check; "
            "path.exists() would have accepted it"
        )
        joined = "\n".join(lines)
        assert (
            "[FAIL] expected file but found directory/non-file: manifest.schema.json"
            in joined
        ), joined
    finally:
        shutil.rmtree(tmp)


# ---------------------------------------------------------------------------
# Host-app reference grep — happy path and negative
# ---------------------------------------------------------------------------

def test_no_host_app_references_in_current_draftmyvan() -> None:
    ok, lines = h.check_no_host_app_references(REPO_ROOT)
    assert ok, "\n".join(lines)


def test_host_app_reference_grep_flags_temp_offender() -> None:
    # Build the offending substring at runtime by concatenation so the
    # literal does not appear anywhere in this test file's own source.
    # The forbidden substrings are listed in
    # check_handoff_ready.FORBIDDEN_PY_SUBSTRINGS; we look up the first
    # one rather than spell it inline.
    forbidden_pattern = h.FORBIDDEN_PY_SUBSTRINGS[0]
    forbidden_full = forbidden_pattern + "something"
    offender = REPO_ROOT / "tests" / "_handoff_offender_TMP.py"
    offender.write_text(
        f'"""Temp offender for test_handoff_ready."""\nBAD = "{forbidden_full}"\n',
        encoding="utf-8",
    )
    try:
        ok, lines = h.check_no_host_app_references(REPO_ROOT)
        assert ok is False
        joined = "\n".join(lines)
        assert "_handoff_offender_TMP.py" in joined
        assert repr(forbidden_pattern) in joined
    finally:
        offender.unlink(missing_ok=True)


def test_host_app_reference_grep_skips_ignored_dirs() -> None:
    # A forbidden substring living inside a local / gitignored artifact dir
    # (e.g. a `.venv` created by `pip install -e ".[dev]"`, or build/ , dist/,
    # node_modules/, an .egg-info) must NOT trip the grep. CI is clean, but
    # locally these dirs hold third-party source with forbidden substrings.
    forbidden = h.FORBIDDEN_PY_SUBSTRINGS[0] + "something"
    tmp = Path(tempfile.mkdtemp(prefix="dmv_handoff_ignored_"))
    try:
        # A clean first-party source file that must still be scanned.
        (tmp / "pkg").mkdir()
        (tmp / "pkg" / "mod.py").write_text('"""clean."""\nX = 1\n', encoding="utf-8")
        # An offender buried in each kind of ignored directory. Paths are
        # built from components (not literals) so this test file's own source
        # never spells one of the FORBIDDEN_PY_SUBSTRINGS the checker greps for.
        ignored_dirs = (
            (".venv", "site-packages", "dep"),
            ("venv", "sub"),
            ("build",),
            ("dist",),
            ("node_modules", "dep"),
            (".pytest_cache",),
            ("draftmyvan.egg-info",),
            ("pkg", "__pycache__"),
        )
        for parts in ignored_dirs:
            d = tmp.joinpath(*parts)
            d.mkdir(parents=True, exist_ok=True)
            (d / "vendored.py").write_text(f'BAD = "{forbidden}"\n', encoding="utf-8")
        ok, lines = h.check_no_host_app_references(tmp)
        assert ok is True, (
            "offenders inside ignored dirs must be skipped:\n" + "\n".join(lines)
        )
    finally:
        shutil.rmtree(tmp)


def test_host_app_reference_grep_still_flags_offender_outside_ignored_dirs() -> None:
    # Guard against the skip being too broad: an offender in an ordinary
    # first-party directory of the same temp tree must still be caught.
    forbidden = h.FORBIDDEN_PY_SUBSTRINGS[0] + "something"
    tmp = Path(tempfile.mkdtemp(prefix="dmv_handoff_notignored_"))
    try:
        (tmp / ".venv" / "sub").mkdir(parents=True, exist_ok=True)
        (tmp / ".venv" / "sub" / "vendored.py").write_text(
            f'BAD = "{forbidden}"\n', encoding="utf-8"
        )
        (tmp / "pkg").mkdir()
        (tmp / "pkg" / "real_offender.py").write_text(
            f'BAD = "{forbidden}"\n', encoding="utf-8"
        )
        ok, lines = h.check_no_host_app_references(tmp)
        joined = "\n".join(lines)
        assert ok is False, "a first-party offender must still be flagged"
        assert "real_offender.py" in joined, joined
        assert "vendored.py" not in joined, "the .venv offender must not be reported"
    finally:
        shutil.rmtree(tmp)


def test_host_app_reference_grep_does_not_flag_itself() -> None:
    # check_handoff_ready.py literally contains the forbidden substrings
    # (it has to, in order to grep for them). The checker must ignore itself.
    ok, _ = h.check_no_host_app_references(REPO_ROOT)
    assert ok is True, (
        "the checker should ignore its own source — otherwise it would "
        "always fail because it lists the forbidden substrings"
    )


# ---------------------------------------------------------------------------
# CLI (default / static-only mode)
# ---------------------------------------------------------------------------

def test_cli_default_mode_returns_0_for_current_repo() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = h.main([])
    assert code == 0
    out = buf.getvalue()
    assert "RESULT: HANDOFF READY" in out
    assert "=== required files ===" in out
    assert "=== no host-app references ===" in out
    # Default mode must NOT run dynamic checks.
    assert "=== package report ===" not in out
    assert "=== test modules ===" not in out
    assert "skipping dynamic checks" in out


def test_cli_explicit_root_argument_works() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = h.main(["--root", str(REPO_ROOT)])
    assert code == 0
    assert "RESULT: HANDOFF READY" in buf.getvalue()


def test_cli_fails_when_pointed_at_an_empty_directory() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="dmv_empty_"))
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = h.main(["--root", str(tmp)])
        assert code == 1
        out = buf.getvalue()
        assert "RESULT: HANDOFF NOT READY" in out
        assert "[FAIL] missing file:" in out
    finally:
        shutil.rmtree(tmp)


# ---------------------------------------------------------------------------
# Required-file list — guard against accidental shrinkage
# ---------------------------------------------------------------------------

def test_required_files_list_includes_all_critical_categories() -> None:
    rels = set(h.REQUIRED_FILES)
    assert "manifest.schema.json" in rels
    assert "examples/galley_1000.json" in rels
    assert "examples/assets/galley_1000.glb" in rels
    assert "examples/assets/galley_1000.asset_acceptance.json" in rels
    assert "examples/assets/candidates/README.md" in rels
    assert "examples/assets/candidates/PROMOTION_CRITERIA.md" in rels
    assert "examples/assets/candidates/candidate_review_checklist.md" in rels
    assert "examples/assets/candidates/galley_1000_candidate.glb" in rels
    assert "examples/assets/candidates/galley_1000_candidate.asset_acceptance.json" in rels
    assert "examples/assets/candidates/galley_1000_candidate_review.json" in rels
    assert "examples/assets/candidates/galley_1000_candidate_review.md" in rels
    assert "examples/assets/candidates/galley_1000_candidate_visual_audit.json" in rels
    assert "examples/assets/candidates/galley_1000_candidate_visual_audit.md" in rels
    assert "examples/assets/candidates/galley_1000_candidate_render_evidence.json" in rels
    assert "examples/assets/candidates/galley_1000_candidate_human_visual_review.json" in rels
    assert "examples/assets/candidates/galley_1000_candidate_human_visual_review.md" in rels
    assert "examples/assets/candidates/render_evidence/README.md" in rels
    for view in ("front", "rear", "left", "right", "top", "three_quarter"):
        assert (
            f"examples/assets/candidates/render_evidence/galley_1000_candidate/{view}.png"
            in rels
        )
    assert "tests/fixtures/galley_1000_contract_box.glb" in rels
    assert any(r.startswith("runtime/") for r in rels)
    assert any(r.startswith("tools/blender/") for r in rels)
    assert any(r.startswith("tools/assets/") for r in rels)
    assert any(r.startswith("tests/") for r in rels)
    for rel in (
        "tools/blender/EXPORT_REAL_ASSET.md",
        "tools/blender/asset_export_checklist.md",
        "tools/blender/create_galley_candidate.py",
        "tools/blender/check_asset_ready.py",
        "tools/assets/validate_asset_acceptance.py",
        "tools/assets/validate_candidate_asset.py",
        "tools/assets/validate_candidate_review.py",
        "tools/assets/validate_candidate_visual_audit.py",
        "tools/assets/validate_render_evidence.py",
        "tools/assets/validate_human_visual_review.py",
        "tools/fusion/README.md",
        "tools/fusion/GALLEY_V1_PARAMETRIC_PLAN.md",
        "tools/fusion/galley_v1_parameter_map.json",
        "tools/fusion/validate_fusion_parameter_map.py",
        "tools/fusion/export_galley_v1_parameters.py",
        "tools/fusion/fusion_galley_v1_skeleton.py",
        "tools/fusion/check_fusion_payload.py",
        "tools/fusion/compute_galley_panels.py",
        "tools/fusion/export_galley_v1_panels.py",
        "tools/fusion/fusion_create_galley_v1.py",
        "tools/fusion/check_fusion_geometry_plan.py",
        "tools/fusion/RUN_FUSION_GEOMETRY_MANUAL.md",
        "tools/fusion/MANUAL_FUSION_GEOMETRY_CHECKLIST.md",
        "tools/fusion/fusion_command_bridge.py",
        "tools/mcp/fusion_bridge_server.py",
        "tools/mcp/smoke_fusion_bridge.py",
        "docs/FUSION_MCP_BRIDGE.md",
        "docs/FUSION_MCP_OPT_IN_CONFIG.md",
        "tests/test_check_asset_ready.py",
        "tests/test_asset_acceptance.py",
        "tests/test_candidate_asset.py",
        "tests/test_create_galley_candidate.py",
        "tests/test_candidate_review.py",
        "tests/test_candidate_visual_audit.py",
        "tests/test_render_evidence.py",
        "tests/test_human_visual_review.py",
        "tests/test_fusion_parameter_map.py",
        "tests/test_fusion_skeleton.py",
        "tests/test_fusion_panel_math.py",
        "tests/test_fusion_geometry_plan.py",
        "tests/test_fusion_geometry_execution_skeleton.py",
        "tests/test_fusion_local_availability.py",
        "tests/test_fusion_mcp_bridge.py",
        "tests/test_fusion_mcp_opt_in_docs.py",
        "tests/fixtures/galley_1000_fusion_parameters.expected.json",
        "tests/fixtures/galley_1000_panels.expected.json",
        "tests/fixtures/galley_1000_fusion_geometry_plan.expected.json",
    ):
        assert rel in rels, f"required-files list dropped {rel}"
    assert "tests.test_check_asset_ready" in h.DYNAMIC_TEST_MODULES
    assert "tests.test_asset_acceptance" in h.DYNAMIC_TEST_MODULES
    assert "tests.test_candidate_asset" in h.DYNAMIC_TEST_MODULES
    assert "tests.test_create_galley_candidate" in h.DYNAMIC_TEST_MODULES
    assert "tests.test_candidate_review" in h.DYNAMIC_TEST_MODULES
    assert "tests.test_candidate_visual_audit" in h.DYNAMIC_TEST_MODULES
    assert "tests.test_render_evidence" in h.DYNAMIC_TEST_MODULES
    assert "tests.test_human_visual_review" in h.DYNAMIC_TEST_MODULES
    assert "tests.test_fusion_parameter_map" in h.DYNAMIC_TEST_MODULES
    assert "tests.test_fusion_skeleton" in h.DYNAMIC_TEST_MODULES
    assert "tests.test_fusion_panel_math" in h.DYNAMIC_TEST_MODULES
    assert "tests.test_fusion_geometry_plan" in h.DYNAMIC_TEST_MODULES
    assert "tests.test_fusion_geometry_execution_skeleton" in h.DYNAMIC_TEST_MODULES
    assert "tests.test_fusion_local_availability" in h.DYNAMIC_TEST_MODULES
    assert "tests.test_fusion_mcp_bridge" in h.DYNAMIC_TEST_MODULES
    assert "tests.test_fusion_mcp_opt_in_docs" in h.DYNAMIC_TEST_MODULES
    # Handoff docs must be listed as required (this PR's whole point).
    for doc in ("HANDOFF.md", "EXTRACT_TO_REAL_REPO.md", "COMMANDS.md"):
        assert doc in rels, f"required-files list dropped {doc}"


def main() -> int:
    tests = [
        test_required_files_pass_on_current_repo,
        test_required_files_fail_when_one_is_missing,
        test_required_file_fails_when_path_is_a_directory,
        test_no_host_app_references_in_current_draftmyvan,
        test_host_app_reference_grep_flags_temp_offender,
        test_host_app_reference_grep_skips_ignored_dirs,
        test_host_app_reference_grep_still_flags_offender_outside_ignored_dirs,
        test_host_app_reference_grep_does_not_flag_itself,
        test_cli_default_mode_returns_0_for_current_repo,
        test_cli_explicit_root_argument_works,
        test_cli_fails_when_pointed_at_an_empty_directory,
        test_required_files_list_includes_all_critical_categories,
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
