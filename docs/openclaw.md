# OpenClaw onboarding: project awareness, not a Gateway plugin

MCC 0.3 provides an optional **file/CLI workflow**. OpenClaw reads owner-approved instructions via its workspace AGENTS.md, reads a canonical neutral snapshot before work, updates approved project records after verification, and uses mcc-bridge to refresh the local viewer. The UI remains read-only. No Gateway pairing, token scopes, internal databases, private Work Engine or config mutation is implemented.

## 1. Try MCC first

Follow the README demo quickstart. Keep its demo config/data separate from real projects. Confirm loopback unlock works; token handling is unchanged. Then choose your existing agent workspace explicitly (verify its configured path locally). Do not clone this public repository over your private workspace.

## 2. Choose canonical records

Use one owner-controlled directory within the chosen private workspace, e.g. a dedicated mcc-projects directory (0700), containing projects.json (0600) in contracts/v1/snapshot.schema.json format. examples/openclaw-projects.json is **synthetic only**. Copy it for a disposable demo, or author/review your own neutral records. If a canonical source already exists, maintain an explicit reviewed projection; do not create competing authority. No recursive discovery, raw tracker conversion, registry or SQLite access occurs.

Keep all projects you want visible in this canonical snapshot. IDs are stable exact identities, not names. Evidence metadata uses dated verification references/digests in roadmap text; next_step is the resume point. Do not include credentials or private content in GitHub. Shape validation does not redact sensitive text.

## 3. Adopt instructions deliberately

Review onboarding/MCC-INSTRUCTIONS.md, copy it to a selected maintained file in the private workspace (0600), then inspect/back up your existing AGENTS.md. **Merge only** onboarding/AGENTS.snippet.md; preserve existing instructions and SOUL/USER/MEMORY. Replace every placeholder with an exact locally verified absolute path:

| Placeholder | Owner-selected value |
| --- | --- |
| INSTRUCTIONS_FILE | maintained MCC-INSTRUCTIONS.md |
| PROJECT_ROOT | canonical 0700 snapshot directory |
| DATA_ROOT | existing MCC 0700 data directory |
| MCC_CLI | dedicated virtualenv's mcc executable |
| BRIDGE_CLI | dedicated virtualenv's mcc-bridge executable |

Do not run unresolved templates. Paths are data, not shell expansions; quote each CLI argument. Verify the linked instruction file and canonical record can actually be read by this agent's permitted file tools. Workspace is a default working directory, **not a sandbox**. Instructions do not grant file/exec access; existing tool policy and approval requirements remain.

Optional: after owner review copy onboarding/skills/mcc-project-context into the existing workspace skills directory, preserving any existing skill of that name. This repo-owned skill routes to the maintained instructions; it is not required, not installed automatically, and has no Gateway tool dispatch. No Workshop or plugin installation is needed. A new session/skill refresh may be needed; ask the agent to read back its AGENTS MCC section and exact project ID, then demonstrate one approved update. Instruction injection/discovery is not proof of adherence.

## 4. Validate, review, refresh

These shell variables are examples: set them to your reviewed local paths, not these placeholders. The guide assumes MCC is already initialized. The CLI writes only MCC's dedicated data root; canonical edits use your already permitted file tools.

```sh
MCC_CLI="/your/reviewed/venv/bin/mcc"
BRIDGE_CLI="/your/reviewed/venv/bin/mcc-bridge"
PROJECT_ROOT="/your/private/workspace/mcc-projects"
MCC_CONFIG="/your/mcc/config"
MCC_DATA="/your/mcc/data"
"$BRIDGE_CLI" --root "$PROJECT_ROOT" --file projects.json
```

First validate without a destination. For initial project creation, separately approve IDs/content, back up the old MCC snapshot, then use the existing explicit import:

```sh
"$MCC_CLI" --config-dir "$MCC_CONFIG" --data-dir "$MCC_DATA" import --root "$PROJECT_ROOT" --file projects.json
```

For ordinary updates, stop competing import/file writers and review the canonical diff and privacy, then dry-run and apply:

```sh
"$BRIDGE_CLI" --root "$PROJECT_ROOT" --file projects.json --data-dir "$MCC_DATA"
# Set these variables to the exact digests from the reviewed dry-run.
"$BRIDGE_CLI" --root "$PROJECT_ROOT" --file projects.json --data-dir "$MCC_DATA" \
  --expected-current "$REVIEWED_CURRENT_SHA256" --expected-source "$REVIEWED_SOURCE_SHA256" --apply
```

Dry-run prints project IDs, changed, source_sha256 and current_sha256, not project text. --apply requires both reviewed digests, rejects identity changes, and creates a 0600 digest-named backup in the data directory before atomic replacement. A repeated identical apply is a no-op. This is a cooperative lock, not protection against another same-owner process writing directly; keep other writers stopped. A crashed bridge may leave bridge.lock: inspect first, then remove only that stale lock after confirming no writer is active. Never bypass a stale digest failure.

Restore: stop competing writers; validate the selected digest-named backup with mcc-bridge --root "$MCC_DATA" --file "$BACKUP_NAME"; explicitly import it with mcc --root "$MCC_DATA" --file "$BACKUP_NAME" and the same config/data flags. Verify content/digest and read back the UI. Restore canonical records separately from their owner-protected backup. Token files and current session policy are untouched by snapshot refresh/restore.

## Configuration: normally none

No OpenClaw configuration change is necessary if the existing agent workspace is suitable. Adopting the merged AGENTS snippet is the awareness change; maintained instructions and neutral files provide persistence. Do not overwrite persona/memory files, patch full config, restart the Gateway, change models, grant broad tools/scopes or copy provider credentials.

Only if the existing workspace is inappropriate should an owner separately approve changing the intended agent's workspace. Inspect the installed version's help, current config and schema first; use its documented path-specific setting and preserve unrelated values. This package supplies no automatic config writer or guessed multi-agent schema. Read-only config/schema CLI or Gateway schema tools, when exposed, are inspection aids—not integration dependencies.

## Compatibility and proof boundaries

Documentation baseline: stock OpenClaw **2026.9.8**, not a private fork. References: [workspace](https://github.com/openclaw/openclaw/blob/v2026.9.8/docs/concepts/agent-workspace.md), [skills](https://github.com/openclaw/openclaw/blob/v2026.9.8/docs/tools/skills.md), [config CLI](https://github.com/openclaw/openclaw/blob/v2026.9.8/docs/cli/config.md), [system prompt](https://github.com/openclaw/openclaw/blob/v2026.9.8/docs/concepts/system-prompt.md). Newer live docs may differ: inspect the installed release instead of copying config examples blindly.

MCC's deterministic bridge is independently usable without OpenClaw. Validation, path rejection, backup/restore and atomic refresh are automated tests. Stock CLI/version/schema/bootstrap checks, where reported, demonstrate mechanics only. No authenticated model run, live channels, real project mutation or agent adherence is claimed; owners must perform the read-back/approved-update acceptance step with their own permitted agent. No live installation changes were made for this release.
