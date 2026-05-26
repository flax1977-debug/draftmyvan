# Extracting DraftMyVan to its own repository

Step-by-step checklist. Read `HANDOFF.md` first.

## Pre-flight (do this in PaperAI before extracting)

- [ ] **Confirm green CI on `main`.** `Validate manifests & run tests` must be
      passing on the latest `main` commit before you cut anything loose.
- [ ] **Run the handoff gate locally.** From the PaperAI checkout:
      ```bash
      cd draftmyvan
      python tools/handoff/check_handoff_ready.py
      python tools/handoff/check_handoff_ready.py --include-dynamic
      ```
      Both should exit 0 with `RESULT: HANDOFF READY`. The `--include-dynamic`
      mode re-runs every test suite + the package report in subprocesses, so
      it is slower but proves the suite passes end-to-end before extraction.
- [ ] **Decide on PR #7.** Either merge `claude/draftmyvan-export-procedure`
      into PaperAI's `main` first (so it travels with the extraction), or
      explicitly note that it will be reopened against the new repo.

## Create the new repository

- [ ] Create a new GitHub repo. Recommended name: **`draftmyvan`** (lowercase,
      matches the folder name). Public or private as you choose. Empty —
      no README, no LICENSE, no .gitignore from GitHub's templates (we'll
      copy our own).
- [ ] Choose a license. Pick before any external contributor PR. MIT or
      Apache-2.0 are reasonable defaults. Add `LICENSE` at the new repo root.

## Decide on history preservation

There are two ways to move the folder. Pick one before copying anything.

### Option A — Filtered history (recommended for projects you'll want to debug long-term)

Preserves every commit that touched `draftmyvan/**` or
`.github/workflows/draftmyvan.yml`, rewritten so the paths look like a
top-level project.

```bash
# In a fresh scratch directory, NOT in PaperAI:
git clone --no-local /path/to/PaperAi draftmyvan-extract
cd draftmyvan-extract

# git-filter-repo is the modern tool; install with `pipx install git-filter-repo`
git filter-repo \
    --path draftmyvan/ \
    --path .github/workflows/draftmyvan.yml \
    --path-rename draftmyvan/: \
    --path-rename .github/workflows/draftmyvan.yml:.github/workflows/ci.yml \
    --force

git remote add origin git@github.com:<owner>/draftmyvan.git
git push -u origin main
```

Caveats:
- Hash IDs change. Any links to PaperAI commits referencing DraftMyVan files
  remain valid in PaperAI but will not exist in the new repo.
- PR numbers do not transfer. The new repo starts at PR #1.

### Option B — Clean copy (simpler; good when history isn't important)

```bash
# In a fresh scratch directory:
mkdir draftmyvan-extract && cd draftmyvan-extract
git init -b main

cp -r /path/to/PaperAi/draftmyvan/. .
mkdir -p .github/workflows
cp /path/to/PaperAi/.github/workflows/draftmyvan.yml .github/workflows/ci.yml

git add -A
git commit -m "Initial import from PaperAI incubation (see HANDOFF.md)"
git remote add origin git@github.com:<owner>/draftmyvan.git
git push -u origin main
```

## Adjust the workflow for the new root

The PaperAI workflow uses `working-directory: draftmyvan` because the
project is nested. At the new repo root, drop that prefix:

```yaml
# .github/workflows/ci.yml — diff vs the old workflow
- name: Validate every example manifest
-  working-directory: draftmyvan
   run: python tools/validate_manifest.py --all
```

And drop the `paths:` filter (the whole repo is in scope now):

```yaml
on:
  push:
-    branches: ["**"]
-    paths:
-      - "draftmyvan/**"
-      - ".github/workflows/draftmyvan.yml"
  pull_request:
-    paths:
-      - "draftmyvan/**"
-      - ".github/workflows/draftmyvan.yml"
```

Rename the workflow's `name:` from `DraftMyVan manifest` to whatever
fits the new repo's conventions (e.g. `CI`).

## Verify the extraction

In the new repo's clone:

- [ ] `python tools/validate_manifest.py --all` → `1/1 valid`.
- [ ] `python -m tests.test_validator` → all green.
- [ ] `python -m tests.test_blender_manifest_contract` → all green.
- [ ] `python -m tests.test_galley_fixture` → all green.
- [ ] `python -m tests.test_runtime_consumer` → all green.
- [ ] `python -m tests.test_package_report` → all green.
- [ ] `python -m tests.test_handoff_ready` → all green.
- [ ] `python tools/handoff/check_handoff_ready.py` → `RESULT: HANDOFF READY`.
- [ ] `python -m runtime.package_report examples/` → `RESULT: PACKAGE READY`,
      exit 0.
- [ ] Push to GitHub; confirm the CI workflow runs and is green.

## Keep PaperAI clean

After the extraction is confirmed working in the new repo:

- [ ] **Do not delete `draftmyvan/` from PaperAI in the same PR as the
      extraction.** Keep both in sync for a deprecation window (one or
      two weeks). This protects against extraction bugs.
- [ ] When you do remove it from PaperAI, send a single deletion PR:
      ```
      git rm -r draftmyvan/
      git rm .github/workflows/draftmyvan.yml
      ```
      The PR description should link the new repo and the
      tag / commit that proves the extraction passed CI.
- [ ] Remove the brief "DraftMyVan is incubating here" pointer from
      PaperAI's top-level `README.md`.

## Do not move

- ❌ `lib/` — Flutter app, belongs to PaperAI.
- ❌ `pubspec.yaml`, `analysis_options.yaml` — Flutter config.
- ❌ `.devcontainer/` — PaperAI's devcontainer.
- ❌ Top-level `README.md` — describes PaperAI, not DraftMyVan.
      (DraftMyVan's own `README.md` lives under `draftmyvan/`.)
- ❌ Any PaperAI CI workflows (none exist today; if any are added
      later, they stay).

If you accidentally move any of the above, the new repo's
`check_handoff_ready.py` will fail because of the `lib/` /
`flutter` / `pubspec` static reference checks.

## After extraction

- Reopen PR #7 (Blender export procedure) against the new repo as the
  first follow-up PR. It is the on-ramp for real cabinet art.
- Update any external links / docs / dashboards that pointed at
  `flax1977-debug/PaperAi` to the new repository URL.
- Archive this `EXTRACT_TO_REAL_REPO.md` in the new repo's `docs/`
  directory as project history, or move its content into the new
  repo's main README.
