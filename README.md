# M-command-center · MCC

![Red-and-cyan robot command center concept art with project planning displays](assets/readme-command-center.jpg)

*Owner-supplied concept art, not an application screenshot. Artwork rights retained; repository use authorized. See PROVENANCE.md.*

An authenticated, local, **read-only** command center for recovering project context: objectives, next steps, roadmaps, blockers, search and status filters. Synthetic demo works offline without a Gateway. No execution engine, analytics, hardware, cloud, token ledger or upstream database access.

## Quickstart (verified Linux / Python 3.12)

From a reviewed source checkout:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/mcc --config-dir "$HOME/.config/m-command-center" --data-dir "$HOME/.local/share/m-command-center" init --demo
.venv/bin/mcc --config-dir "$HOME/.config/m-command-center" --data-dir "$HOME/.local/share/m-command-center" serve
```

Open **http://127.0.0.1:8765** (not localhost). Read the protected `auth-token` file locally and enter it into the unlock form; never put it in URLs or share it. Config and data directories are explicit, separate, created only by `init`, and must not already exist. Existing roots must be owner-controlled mode 0700; symlink aliases and traversal are rejected. Nothing starts at install or import. Stop with Ctrl-C. Build tooling versions are pinned in pyproject; runtime has no third-party dependencies.

## Selected neutral import

Use an owner-controlled mode-0700 selection directory. Prepare a snapshot following `contracts/v1/snapshot.schema.json`; use `examples/blank.json`. Only that exact neutral format is accepted—this is **not** a raw legacy tracker importer. Review and sanitize the selected file yourself before import. No automatic discovery, registry walking or preservation of unknown fields.

```sh
.venv/bin/mcc --config-dir "$HOME/.config/m-command-center" --data-dir "$HOME/.local/share/m-command-center" import --root /your/reviewed/snapshots --file selected.json
```

Import atomically replaces only MCC's own snapshot. Absolute selections, traversal and symlinks are denied. Text can still contain your sensitive information: shape validation is not a privacy redactor.

## Security and privacy

Loopback IPv4 only; exact Host and same-Origin checks; POST login with an owner-only random token; HttpOnly, SameSite=Strict one-hour in-memory sessions; no query strings; strict CSP; text-only DOM rendering; no access logs, telemetry, browser token storage or external assets. Lock session to revoke it. `rotate-token` requires a viewer restart to revoke all old sessions. Only one operator session is retained. Local HTTP has no Secure cookie because it is loopback HTTP: **do not proxy or expose this viewer remotely**. No trusted-proxy authentication is implemented. See SECURITY.md for boundaries.

## Storage, backup and restore

There is no database or retained legacy Work Engine store. Own state is `snapshot.json` under your configured data directory; credentials are separate. Stop the viewer, copy the snapshot into an owner-protected backup directory, record its SHA-256, and restore only an independently validated schema-v1 snapshot via the import command. Back up credentials separately if needed; otherwise reinitialize or rotate. Unknown contract versions fail closed. Future major versions require explicit conversion; no silent migration.

## Uninstall

Stop the viewer, then `.venv/bin/python -m pip uninstall m-command-center`; remove only your dedicated virtualenv if desired. Keep configured data/config/backups by default. For deliberate removal, move those exact directories into an owner-protected archive first. MCC creates no services, Gateway pairing, OpenClaw configuration, scheduler or global installation.

## Architecture and compatibility

CLI owns explicit initialization/import. Strict model validates neutral schema. Loopback server reads only its own snapshot and serves bundled original UI. Gateway integration is **not implemented or tested**; an optional future adapter must use documented scoped read APIs and an independently reviewed contract, never raw internal databases or owner-token dispatch. See docs/adapter.md.

Verified: Linux x86_64 (WSL), Python 3.12.3, and Chromium desktop/mobile emulation. Package metadata permits Python 3.11+, but other Python versions, arm64, native Windows, macOS, WebKit and physical Safari are untested. This is not portable certification or Gateway integration.

## Licensing

Code and documentation: MIT, copyright 2026 GuzmanMuller. See LICENSE and THIRD_PARTY_NOTICES.md. The owner-supplied concept artwork is excluded from the code/documentation MIT grant: rights retained, repository use authorized; no general artwork reuse license is granted. See PROVENANCE.md.
