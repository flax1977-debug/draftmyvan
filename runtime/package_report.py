"""Scan a directory of DraftMyVan module manifests and report package readiness.

A *package* in this sense is a directory of `*.json` manifest files (one per
module). The package is **ready** when every manifest loads cleanly into a
typed `Module` and every module's GLB exists on disk.

This is the next step up from `runtime.load_module`: that script answers
"can one runtime consume one manifest?"; this one answers "can a build /
release pipeline ingest the whole catalog?".

CLI:
    cd draftmyvan
    python -m runtime.package_report examples/

Exit codes:
    0  PACKAGE READY     — every manifest loaded; every GLB present.
    1  PACKAGE NOT READY — manifests loaded but at least one GLB is missing.
    2  ERROR             — at least one manifest is malformed, OR duplicate
                          ids / resolved asset paths were detected, OR the
                          directory contains no manifests at all.

Like `runtime.load_module`, this module does **not** re-run schema or
GLB-bbox validation. Those gates live under `tools/` and run before
manifests / GLBs are committed. The package report is the consumer's
view: "given that the gates passed, is the catalog ready to ship?"
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .module import Module
from .load_module import ConsumerError, load_module


@dataclass
class PackageReport:
    """Aggregated readiness data for a directory of manifests."""

    scanned_dir: Path
    manifest_paths: list[Path] = field(default_factory=list)
    modules: list[Module] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total_modules(self) -> int:
        return len(self.modules)

    @property
    def consumable_modules(self) -> int:
        return sum(1 for m in self.modules if m.consumable)

    @property
    def missing_assets(self) -> int:
        return sum(1 for m in self.modules if not m.asset_exists)

    @property
    def ok(self) -> bool:
        """True iff zero errors AND zero missing assets AND at least one module."""
        return (
            not self.errors
            and self.missing_assets == 0
            and self.total_modules > 0
        )

    def exit_code(self) -> int:
        if self.errors:
            return 2
        if self.missing_assets > 0:
            return 1
        if self.total_modules == 0:
            # Belt-and-braces: scan_package() already records this in errors,
            # so we should never reach here. Treat as ERROR if we do.
            return 2
        return 0


def scan_package(directory: Path) -> PackageReport:
    """Load every `*.json` manifest in `directory` (non-recursive).

    Returns a `PackageReport` with modules, errors, and counts populated.
    Recursive scanning is deliberately avoided so subdirectories like
    `examples/assets/` (which holds GLBs and explainer markdown) are not
    mistakenly read as manifests.
    """
    report = PackageReport(scanned_dir=directory)

    if not directory.exists():
        report.errors.append(f"directory not found: {directory}")
        return report
    if not directory.is_dir():
        report.errors.append(f"not a directory: {directory}")
        return report

    manifest_paths = sorted(p for p in directory.glob("*.json") if p.is_file())
    report.manifest_paths = manifest_paths

    if not manifest_paths:
        report.errors.append(
            f"no manifest files (*.json) found in {directory}"
        )
        return report

    ids_seen: dict[str, Path] = {}
    paths_seen: dict[Path, Path] = {}  # resolved_asset_path -> manifest_path

    for manifest_path in manifest_paths:
        try:
            module = load_module(manifest_path)
        except ConsumerError as e:
            report.errors.append(
                f"manifest {manifest_path}: {e}"
            )
            continue

        # Duplicate id check.
        prior_id = ids_seen.get(module.id)
        if prior_id is not None:
            report.errors.append(
                f"duplicate module id {module.id!r} in:\n"
                f"          - {prior_id}\n"
                f"          - {manifest_path}"
            )
        else:
            ids_seen[module.id] = manifest_path

        # Duplicate resolved-asset-path check.
        prior_path_manifest = paths_seen.get(module.resolved_asset_path)
        if prior_path_manifest is not None:
            report.errors.append(
                f"duplicate resolved asset path "
                f"{module.resolved_asset_path} in:\n"
                f"          - {prior_path_manifest}\n"
                f"          - {manifest_path}"
            )
        else:
            paths_seen[module.resolved_asset_path] = manifest_path

        report.modules.append(module)

    return report


def format_report(report: PackageReport) -> list[str]:
    """Render the `PackageReport` as the CLI-visible boring block."""
    lines: list[str] = []
    lines.append(f"Scanning: {report.scanned_dir}")
    lines.append("")
    lines.append(f"Found {len(report.manifest_paths)} manifest file(s):")
    for p in report.manifest_paths:
        lines.append(f"  {p}")
    lines.append("")

    if report.modules:
        lines.append(f"Modules loaded: {report.total_modules}")
        for m in report.modules:
            tag = "[OK]  " if m.asset_exists else "[WARN]"
            present = "present" if m.asset_exists else "MISSING"
            lines.append(
                f"  {tag} {m.id} → {m.resolved_asset_path} ({present})"
            )
        lines.append("")

    if report.errors:
        lines.append(f"Package errors: {len(report.errors)}")
        for err in report.errors:
            lines.append(f"  [ERROR] {err}")
        lines.append("")

    lines.append("Summary:")
    lines.append(f"  total modules:    {report.total_modules}")
    lines.append(f"  consumable:       {report.consumable_modules}")
    lines.append(f"  missing assets:   {report.missing_assets}")
    lines.append(f"  manifest errors:  {len(report.errors)}")
    lines.append("")

    code = report.exit_code()
    if code == 0:
        lines.append("RESULT: PACKAGE READY")
    elif code == 1:
        lines.append(
            "RESULT: PACKAGE NOT READY — "
            f"{report.missing_assets} module(s) have missing assets; "
            "export and validate before shipping."
        )
    else:
        lines.append("RESULT: ERROR — see package errors above")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan a directory of DraftMyVan manifests and report package readiness.",
    )
    parser.add_argument("directory", type=Path,
                        help="Directory containing *.json manifest files.")
    args = parser.parse_args(argv)

    report = scan_package(args.directory)
    for line in format_report(report):
        print(line)
    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
