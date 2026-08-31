# Security Policy

## Supported versions

rosmac is pre-1.0. Only the latest released version on PyPI receives fixes.
While on `0.y.z`, minor versions may contain breaking changes (SemVer, D12).

| Version | Supported |
|---|---|
| latest `0.y.z` | ✅ |
| anything older | ❌ |

## Reporting a vulnerability

**Do not open a public issue for a security problem.**

Preferred: use GitHub's private vulnerability reporting —
**Security → Report a vulnerability** on
<https://github.com/PythonToGo/rosmac/security/advisories>.

Alternatively, email **pythontogoplease@gmail.com** with:

- what the issue is and where (file / command / config path)
- how to reproduce it
- the impact you see (what an attacker on your LAN / on your machine could do)
- rosmac version (`rosmac --version`) and macOS version

You can expect an acknowledgement within about a week. This is a single-
maintainer project, so please allow reasonable time for a fix before any public
disclosure — 90 days is a good default.

Please **do not** include a working exploit or a step-by-step extraction path in
the initial report; describe the class of problem and we'll follow up.

## Threat model — what rosmac assumes

rosmac orchestrates local processes and a local VM. A few things are trusted by
design, not by oversight:

- **The zenoh bridge boundary (TCP 7447) is plaintext, unauthenticated.** On a
  single Mac + its Lima VM this never leaves `localhost`. Nothing to attack
  remotely in the default setup.
- **The real-robot link (beta) is plaintext TCP over your LAN**, no auth, no
  TLS. It is explicitly documented as **trusted-LAN only**
  ([docs/robot-setup.md](docs/robot-setup.md)). Do not expose port 7447 to an
  untrusted network or the internet.
- **`rosmac` runs `micromamba`, `limactl`, `brew`, `curl` and shell provisioning
  scripts** as your user. It never asks for `sudo` and never disables SIP.
  Downloaded binaries (the zenoh bridge) are **pinned by version and verified by
  SHA-256** against `src/rosmac/config.py`; a weekly CI job re-checks the pins
  against upstream.
- **`rosmac report` bundles** collect only from `~/.rosmac` and mask the
  configured robot host. Review a bundle before attaching it to a public issue —
  it contains local paths, log tails, and your version matrix.

Reports about any of the above being weaker than described are in scope.
