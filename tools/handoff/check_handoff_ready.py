#!/usr/bin/env python3
"""Is the DraftMyVan foundation internally consistent?

Two modes:

  default (CI-safe, fast)
      * Every canonical file / module exists at the expected path.
      * No Python file contains a forbidden host-app
        reference (`lib/`, `pubspec`, `flutter`, `dart`).

  --include-dynamic (local-only, slower)
      Adds:
      * `python -m runtime.package_report examples/` must exit 0.
      * Every known test module must exit 0 when invoked via
        `python -m tests.<name>`.

Run from the repository root:

    python tools/handoff/check_handoff_ready.py
    python tools/handoff/check_handoff_ready.py --include-dynamic

Exit codes:
    0  HANDOFF READY     — every check passed
    1  HANDOFF NOT READY — at least one check failed
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# tools/handoff/check_handoff_ready.py -> repository root
DRAFTMYVAN_ROOT = Path(__file__).resolve().parent.parent.parent

# Files that must exist for the project to be considered standalone.
# Editing this list is a significant act — it pins what "handoff
# ready" means at this point in time. Anything added here becomes a
# CI-gated invariant.
REQUIRED_FILES: tuple[str, ...] = (
    # Data contract
    "manifest.schema.json",
    "examples/galley_1000.json",
    "examples/assets/galley_1000.glb",
    "examples/assets/galley_1000.asset_acceptance.json",
    "examples/assets/README.md",
    "examples/assets/galley_1000.glb.md",
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
    "examples/assets/candidates/render_evidence/README.md",
    # Runtime consumer
    "runtime/__init__.py",
    "runtime/module.py",
    "runtime/load_module.py",
    "runtime/package_report.py",
    # Tools
    "tools/validate_manifest.py",
    "tools/assets/generate_galley_fixture_glb.py",
    "tools/assets/validate_asset_acceptance.py",
    "tools/assets/validate_candidate_asset.py",
    "tools/assets/validate_candidate_review.py",
    "tools/assets/validate_candidate_visual_audit.py",
    "tools/assets/validate_render_evidence.py",
    "tools/blender/validate_glb_against_manifest.py",
    "tools/blender/validate_in_blender.py",
    "tools/blender/_anchor_contract.py",
    "tools/blender/README.md",
    "tools/blender/EXPORT_REAL_ASSET.md",
    "tools/blender/asset_export_checklist.md",
    "tools/blender/RENDER_CANDIDATE_AUDIT.md",
    "tools/blender/create_galley_candidate.py",
    "tools/blender/render_candidate_views.py",
    "tools/blender/check_asset_ready.py",
    "tools/handoff/check_handoff_ready.py",
    # Tests
    "tests/test_validator.py",
    "tests/test_blender_manifest_contract.py",
    "tests/test_check_asset_ready.py",
    "tests/test_galley_fixture.py",
    "tests/test_asset_acceptance.py",
    "tests/test_candidate_asset.py",
    "tests/test_create_galley_candidate.py",
    "tests/test_candidate_review.py",
    "tests/test_candidate_visual_audit.py",
    "tests/test_render_evidence.py",
    "tests/fixtures/README.md",
    "tests/fixtures/galley_1000_contract_box.glb",
    "tests/test_runtime_consumer.py",
    "tests/test_package_report.py",
    "tests/test_handoff_ready.py",
    # Docs
    "README.md",
    "HANDOFF.md",
    "EXTRACT_TO_REAL_REPO.md",
    "COMMANDS.md",
)

# Substrings that must not appear in DraftMyVan Python files.
# These would mean the standalone project is leaking host-app assumptions.
FORBIDDEN_PY_SUBSTRINGS: tuple[str, ...] = (
    "lib/",
    "pubspec",
    "flutter",
    "import dart",
)

# Test modules invoked under `--include-dynamic`. Add new test modules
# here when they land.
DYNAMIC_TEST_MODULES: tuple[str, ...] = (
    "tests.test_validator",
    "tests.test_blender_manifest_contract",
    "tests.test_check_asset_ready",
    "tests.test_galley_fixture",
    "tests.test_asset_acceptance",
    "tests.test_candidate_asset",
    "tests.test_create_galley_candidate",
    "tests.test_candidate_review",
    "tests.test_candidate_visual_audit",
    "tests.test_render_evidence",
    "tests.test_runtime_consumer",
    "tests.test_package_report",
    "tests.test_handoff_ready",
)


def check_required_files(root: Path) -> tuple[bool, list[str]]:
    """Every entry in REQUIRED_FILES must resolve to a regular file.

    A path that exists but is a directory (or symlink to a directory,
    or a socket, etc.) is treated as a failure — `is_file()` is the
    contract, not bare existence.
    """
    lines: list[str] = []
    ok = True
    for rel in REQUIRED_FILES:
        path = root / rel
        if path.is_file():
            lines.append(f"[OK]   {rel}")
        elif not path.exists():
            ok = False
            lines.append(f"[FAIL] missing file: {rel}")
        else:
            ok = False
            lines.append(
                f"[FAIL] expected file but found directory/non-file: {rel}"
            )
    return ok, lines


def check_no_host_app_references(root: Path) -> tuple[bool, list[str]]:
    """Scan every .py file under `root` for forbidden host-app substrings."""
    findings: list[tuple[Path, str]] = []
    for py in sorted(root.rglob("*.py")):
        # Skip __pycache__ — irrelevant and may contain unrelated strings.
        if "__pycache__" in py.parts:
            continue
        try:
            text = py.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in FORBIDDEN_PY_SUBSTRINGS:
            if pattern in text:
                # Skip the self-reference inside this very check
                # (this file literally has to contain the patterns
                # in order to scan for them).
                if py.resolve() == Path(__file__).resolve():
                    continue
                findings.append((py.relative_to(root), pattern))
    lines: list[str] = []
    if findings:
        for rel, pattern in findings:
            lines.append(f"[FAIL] {rel} contains {pattern!r}")
        return False, lines
    lines.append(
        f"[OK]   no host-app references in Python files "
        f"(checked patterns: {', '.join(repr(p) for p in FORBIDDEN_PY_SUBSTRINGS)})"
    )
    return True, lines


def run_subprocess_module(
    module: str, root: Path, extra_args: tuple[str, ...] = (),
) -> tuple[bool, str]:
    """Run `python -m <module> [extra_args...]` under `root`.

    Returns (ok, summary) where `summary` is `exit=<code>  <last-stdout-line>`,
    or includes the stderr tail when stdout is empty (helps surface argparse
    errors that go to stderr).
    """
    r = subprocess.run(
        [sys.executable, "-m", module, *extra_args],
        capture_output=True, text=True, cwd=root,
    )
    tail = (r.stdout.strip().splitlines() or [""])[-1]
    if not tail:
        tail = (r.stderr.strip().splitlines() or [""])[-1]
    return r.returncode == 0, f"exit={r.returncode}  {tail}"


def check_package_report(root: Path) -> tuple[bool, list[str]]:
    ok, summary = run_subprocess_module(
        "runtime.package_report", root, extra_args=("examples/",),
    )
    if ok:
        return True, [f"[OK]   runtime.package_report examples/  {summary}"]
    return False, [f"[FAIL] runtime.package_report examples/  {summary}"]


def check_test_modules(root: Path) -> tuple[bool, list[str]]:
    lines: list[str] = []
    overall_ok = True
    for mod in DYNAMIC_TEST_MODULES:
        ok, summary = run_subprocess_module(mod, root)
        marker = "[OK]  " if ok else "[FAIL]"
        lines.append(f"{marker} {mod}  {summary}")
        overall_ok = overall_ok and ok
    return overall_ok, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check that the DraftMyVan foundation is internally consistent.",
    )
    parser.add_argument(
        "--include-dynamic", action="store_true",
        help="Also run the package report and every test module in "
             "subprocesses (slower; intended for local handoff sweeps).",
    )
    parser.add_argument(
        "--root", type=Path, default=DRAFTMYVAN_ROOT,
        help="Path to the DraftMyVan repository root (default: this script's project root).",
    )
    args = parser.parse_args(argv)

    overall_ok = True

    print("=== required files ===")
    ok, lines = check_required_files(args.root)
    overall_ok = overall_ok and ok
    for line in lines:
        print(line)

    print()
    print("=== no host-app references ===")
    ok, lines = check_no_host_app_references(args.root)
    overall_ok = overall_ok and ok
    for line in lines:
        print(line)

    if args.include_dynamic:
        print()
        print("=== package report ===")
        ok, lines = check_package_report(args.root)
        overall_ok = overall_ok and ok
        for line in lines:
            print(line)

        print()
        print("=== test modules ===")
        ok, lines = check_test_modules(args.root)
        overall_ok = overall_ok and ok
        for line in lines:
            print(line)
    else:
        print()
        print(
            "(skipping dynamic checks — package_report and test modules. "
            "Re-run with --include-dynamic before a handoff or release.)"
        )

    print()
    if overall_ok:
        print("RESULT: HANDOFF READY")
        return 0
    print("RESULT: HANDOFF NOT READY")
    return 1


if __name__ == "__main__":
    sys.exit(main())
