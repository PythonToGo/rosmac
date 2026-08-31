<!-- Keep PRs to one logical change. For anything non-trivial, open an issue first. -->

## What this changes

<!-- One or two sentences. Link the issue: Fixes #NN -->

## Why

<!-- The problem this solves. If it touches an architecture decision in PLAN.md,
     link the discussion where that was agreed. -->

## How it was tested

- [ ] `ruff check src tests`
- [ ] `ruff format --check src tests`
- [ ] `mypy`
- [ ] `pytest tests/unit -q`
- [ ] `rosmac --version` / `rosmac --help`
- [ ] E2E (local, if relevant): `bash tests/e2e/test_smoke.sh` — result:

## Checklist

- [ ] `CHANGELOG.md` updated under `[Unreleased]` (for user-visible changes)
- [ ] New behavior has a unit test
- [ ] User-facing strings are English (D11)
- [ ] No new external download without a pinned version + SHA-256
- [ ] If this fixes a macOS/ROS pitfall: added to `docs/troubleshooting.md` in
      the symptom → cause → fix format
