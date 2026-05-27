"""Tests for candidate render evidence metadata validation."""

from __future__ import annotations

import copy
import io
import json
import shutil
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "assets"))

import validate_render_evidence as r  # noqa: E402

METADATA = (
    REPO_ROOT
    / "examples"
    / "assets"
    / "candidates"
    / "galley_1000_candidate_render_evidence.json"
)
CANDIDATE_GLB = REPO_ROOT / "examples" / "assets" / "candidates" / "galley_1000_candidate.glb"
VISUAL_AUDIT = (
    REPO_ROOT
    / "examples"
    / "assets"
    / "candidates"
    / "galley_1000_candidate_visual_audit.json"
)
RENDER_SCRIPT = REPO_ROOT / "tools" / "blender" / "render_candidate_views.py"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _temp_root(*, include_render_script: bool = True, include_visual_audit: bool = True) -> Path:
    root = Path(tempfile.mkdtemp(prefix="dmv_render_evidence_"))
    (root / "examples" / "assets" / "candidates").mkdir(parents=True)
    (root / "tools" / "blender").mkdir(parents=True)
    shutil.copy2(CANDIDATE_GLB, root / "examples" / "assets" / "candidates" / "galley_1000_candidate.glb")
    if include_visual_audit:
        shutil.copy2(VISUAL_AUDIT, root / "examples" / "assets" / "candidates" / "galley_1000_candidate_visual_audit.json")
    if include_render_script:
        shutil.copy2(RENDER_SCRIPT, root / "tools" / "blender" / "render_candidate_views.py")
    return root


def _write_metadata(root: Path, data: dict) -> Path:
    path = root / "examples" / "assets" / "candidates" / "galley_1000_candidate_render_evidence.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _validate_mutation(
    mutator,
    *,
    include_render_script: bool = True,
    include_visual_audit: bool = True,
) -> tuple[str, str]:
    root = _temp_root(
        include_render_script=include_render_script,
        include_visual_audit=include_visual_audit,
    )
    try:
        data = copy.deepcopy(_load_json(METADATA))
        mutator(data)
        metadata = _write_metadata(root, data)
        status, lines = r.validate_render_evidence(metadata, root)
        return status, "\n".join(lines)
    finally:
        shutil.rmtree(root)


def test_current_metadata_validates() -> None:
    status, lines = r.validate_render_evidence(METADATA, REPO_ROOT)
    joined = "\n".join(lines)
    assert status == r.STATUS_VALID, joined
    assert "RESULT: RENDER EVIDENCE VALID" in joined


def test_wrong_candidate_sha_fails() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("candidate_sha256", "0" * 64)
    )
    assert status == r.STATUS_INVALID
    assert "candidate_sha256 mismatch" in joined


def test_missing_render_script_fails() -> None:
    status, joined = _validate_mutation(lambda d: d, include_render_script=False)
    assert status == r.STATUS_INVALID
    assert "render script does not exist" in joined


def test_missing_visual_audit_metadata_fails() -> None:
    status, joined = _validate_mutation(lambda d: d, include_visual_audit=False)
    assert status == r.STATUS_INVALID
    assert "visual audit metadata does not exist" in joined


def test_missing_expected_view_fails() -> None:
    def mutate(data: dict) -> None:
        data["expected_views"] = ["front", "rear", "left", "right", "top"]

    status, joined = _validate_mutation(mutate)
    assert status == r.STATUS_INVALID
    assert "three_quarter" in joined


def test_committed_renders_true_fails_without_checked_images() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("committed_renders", True)
    )
    assert status == r.STATUS_INVALID
    assert "render_paths" in joined


def test_promotion_ready_true_fails() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("promotion_ready", True)
    )
    assert status == r.STATUS_INVALID
    assert "promotion_ready must be false" in joined


def test_production_art_true_fails() -> None:
    status, joined = _validate_mutation(
        lambda d: d.__setitem__("production_art", True)
    )
    assert status == r.STATUS_INVALID
    assert "production_art must be false" in joined


def test_cli_default_metadata_returns_0() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = r.main([])
    assert code == 0
    assert "RESULT: RENDER EVIDENCE VALID" in buf.getvalue()


def main() -> int:
    tests = [
        test_current_metadata_validates,
        test_wrong_candidate_sha_fails,
        test_missing_render_script_fails,
        test_missing_visual_audit_metadata_fails,
        test_missing_expected_view_fails,
        test_committed_renders_true_fails_without_checked_images,
        test_promotion_ready_true_fails,
        test_production_art_true_fails,
        test_cli_default_metadata_returns_0,
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
