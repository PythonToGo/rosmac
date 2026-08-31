# Contributing to rosmac

Thanks for your interest. rosmac is a small, single-maintainer project with a
tight scope, so please read this before opening a large PR — a quick issue first
saves everyone time.

## What rosmac is (and isn't)

rosmac makes ROS 2 **Humble** development work on **Apple Silicon** Macs by
splitting the stack: native RoboStack on the Mac, a Tier‑1 Ubuntu VM (Lima) for
the heavy parts, one zenoh bridge (TCP) between them.

Out of scope (see [PLAN.md](PLAN.md) and the non-goals in
[docs/plan/phase5-productionize.md](docs/plan/phase5-productionize.md)):

- Linux / Windows hosts, Intel Macs
- ROS 2 distributions other than Humble (Jazzy etc. are a v0.2+ backlog item)
- Telemetry / usage analytics (deliberately never collected)

The architecture (layer split, RMW pinning, the bridge boundary) is settled in
the decision log in `PLAN.md`. If you want to change one of those, open an issue
to discuss first — don't send a PR that reverses a decision.

## Reporting bugs

Open a bug issue and **attach a `rosmac report` bundle**
(`rosmac report` → `rosmac-report-<date>.tar.gz`). It collects only from
`~/.rosmac` (diagnostics, versions, recent logs) and masks the robot host. The
issue template asks for this — bugs without it are hard to act on.

## Contributing a pitfall

The field-measured pitfall database is the core of this project. If you hit a
new macOS/ROS failure mode and work out the fix:

1. Add a user-facing entry to [docs/troubleshooting.md](docs/troubleshooting.md)
   in the house format: **symptom (verbatim error string) → cause (one line) →
   fix (exact command)**. The verbatim error string matters — that's how the
   next person finds it.
2. If `rosmac doctor` could detect it, say so in the issue/PR so a check can be
   added.

## Development setup

Requires Python 3.11+ (3.12 recommended) on Apple Silicon macOS.

```bash
git clone https://github.com/PythonToGo/rosmac && cd rosmac
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

The `dev` extra pins `ruff` and `mypy` **exactly** — a tool bump silently shifts
the lint/format/type baseline and drifts CI apart from local checkouts. Don't
loosen those pins in a PR without a reason.

## Before you push

CI runs exactly these four checks (ubuntu 3.11/3.12 + macos-14 3.12). Run them
locally first:

```bash
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/mypy
.venv/bin/pytest tests/unit -q
```

Plus the CLI smoke that CI does: `rosmac --version` and `rosmac --help`.

### End-to-end tests (local only)

E2E needs a real Lima VM, which GitHub's macOS runners can't boot (nested
virtualization is unsupported — measured, see
[tests/e2e/README.md](tests/e2e/README.md)). Run them on your Mac after
`rosmac init`:

```bash
bash tests/e2e/test_smoke.sh      # up → topic round-trip → down (~1 min)
bash tests/e2e/test_phase2.sh     # sim preset → health → viz
bash tests/e2e/test_phase4.sh     # external workspace: deps → build → ps → push
```

Run these before tagging a release and after any change to the VM template or a
version pin (bridge, RoboStack channel, Lima floor).

## Pull requests

- One logical change per PR. Keep the diff focused.
- Commit messages: imperative mood, reference the issue
  (`Fix bridge orphan sweep on cold daemon (#42)`).
- Update `CHANGELOG.md` under `[Unreleased]` for any user-visible change.
- User-facing strings (CLI help, error panels, docs) are **English only** (D11).
  Code comments and internal planning docs under `docs/plan/` stay as they are.
- New behavior needs a unit test in `tests/unit/`. Behavior that needs a VM goes
  in `tests/e2e/` behind the `e2e` marker.

## License

By contributing you agree that your contributions are licensed under the
project's [MIT License](LICENSE). There is no CLA.
