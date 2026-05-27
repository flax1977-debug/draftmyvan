#!/usr/bin/env python3
"""Local advisory check for Autodesk Fusion 360 availability.

This helper is intentionally not a CI prerequisite for Fusion execution. It
only checks common local macOS application locations and reports whether a
Fusion app bundle appears to exist.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable


APP_NAMES: tuple[str, ...] = (
    "Autodesk Fusion.app",
    "Fusion 360.app",
    "Autodesk Fusion 360.app",
)


def default_search_roots(home: Path | None = None) -> tuple[Path, ...]:
    """Return common local macOS roots where Fusion may be installed."""
    home = home or Path.home()
    return (
        Path("/Applications"),
        home / "Applications",
        home / "Library" / "Application Support" / "Autodesk",
    )


def candidate_app_paths(search_roots: Iterable[Path]) -> list[Path]:
    """Return deterministic candidate app bundle paths under `search_roots`."""
    candidates: list[Path] = []
    for root in search_roots:
        root = Path(root)
        for app_name in APP_NAMES:
            candidates.append(root / app_name)
            candidates.append(root / "Autodesk" / app_name)
    return sorted(dict.fromkeys(candidates))


def find_fusion_apps(search_roots: Iterable[Path] | None = None) -> list[Path]:
    """Return existing Fusion app bundle paths from known candidate paths."""
    roots = tuple(search_roots) if search_roots is not None else default_search_roots()
    return [path for path in candidate_app_paths(roots) if path.is_dir()]


def format_report(found: list[Path], searched: list[Path]) -> str:
    """Format a human-readable local availability report."""
    lines: list[str] = []
    if found:
        lines.append("[OK] Fusion app bundle candidate found")
        lines.extend(f"found: {path}" for path in found)
        lines.append("RESULT: FUSION LOCAL AVAILABLE")
    else:
        lines.append("[FAIL] Fusion app bundle not found in known local paths")
        lines.append("searched:")
        lines.extend(f"- {path}" for path in searched)
        lines.append("RESULT: FUSION LOCAL NOT FOUND")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check common local macOS paths for Autodesk Fusion 360.",
    )
    parser.add_argument(
        "--search-root",
        action="append",
        type=Path,
        help="Override/add a root to search. Repeat for multiple roots.",
    )
    args = parser.parse_args(argv)

    roots = tuple(args.search_root) if args.search_root else default_search_roots()
    searched = candidate_app_paths(roots)
    found = [path for path in searched if path.is_dir()]
    print(format_report(found, searched))
    return 0 if found else 1


if __name__ == "__main__":
    sys.exit(main())
