# Structured owner records v2

MCC remains a separate Python application, not an OpenClaw plugin. The helper never executes project commands, launches sessions, changes OpenClaw settings or grants tool approval.

Use a NEW dedicated mode-0700 MCC data directory, separate from existing v1 data. Initialize the authenticated viewer normally, then invoke mcc-owner with that exact data directory and an explicitly selected private artifact root. First explicit owner creation initializes owner-root.json only on an empty root. Reconcile refuses uninitialized roots. Import/bridge writers serialize through the same owner lock and reject marked roots. Existing v1 imports/viewers remain supported in separate roots. Never enable owner projection on a populated imported snapshot: onboarding must create a dedicated empty root.

Each project-<stable-id>.json is canonical schema_version 2. Bounded directory membership is the registry (200 projects); no recursive discovery. Project revision increases per committed operation. One advisory flock serializes all helper writers and aggregate projections. Atomic no-follow temporary write, fsync, rename and directory fsync commit the record and its operation receipt together. Receipts bind exact request digest: replay returns the original revision and repairs projection, changed payload denies. Uncertain delivery is resolved by replaying the SAME key, not generating a new attempt.

Envelope: project_id, expected_revision, operation_key, operation, payload. CLI reads one bounded mode-0600 request through --request-root/--request-file. read requires exact --project-id. reconcile deterministically regenerates v1 display fields and revision/task sidecar. Failed projection never rolls back the canonical commit. Authenticated /api/owner-state shows stale revisions until reconciliation. Poll interval is two seconds; <=5s convergence is a target for a healthy responsive local server, not an offline/network guarantee.

Transitions: create (name/objective/roadmap), rename, checkpoint (next_step/blockers), pause/resume, propose (task_id/scope/criteria/artifact_paths), edit (scope, invalidating authorization), authorize, start (attempt_id), evidence (criterion/path/method/passed), finish/fail/interrupt, accept/reject (exact evidence_digest; reject also requires a bounded reason). Every task operation after proposal includes task_id/task_revision. Attempt operations also require attempt_id. Success only becomes awaiting_review. Task acceptance never completes a project. No project-complete interface in this slice.

Owner creation, resume, authorize, accept/reject require owner-observed manual --human use. This is a PROCEDURAL interface, NOT independently authenticated identity. A same-UID agent with unrestricted exec can forge this flag or directly replace files. Do not supply reviewer tokens to an agent or claim enforced independent acceptance. Existing OpenClaw policy and owner supervision must separate reviewer operations. Scope controls RECORD transitions and allowed evidence references, NOT a sandbox for stock tools. Untrusted objective/scope/roadmap text never constitutes authority. Evidence digests bind bytes/attempt/criterion/task revision, but helper-reported passed=true does not independently prove the criterion; the human must check the artifact and verification method.

Recovery: read the exact record after new session; running means outcome unknown, not success. Explicit interrupt records interruption; authorize a retry only after owner direction. Reconcile never redispatches or guesses an attempt outcome. Pause forbids new start transitions but does not cancel external tools. To retry rejected/failed/interrupted work: fresh owner authorization, new attempt ID, new evidence. Prior attempts and decisions remain.

Back up all canonical project records under the same writer lock, plus artifacts and separately protected viewer configuration. Restore while writers/viewer are stopped into a NEW private root, verify identities/digests, then reconcile. Do not restore selected projects over an active registry. Uninstall only the selected MCC environment and manually reviewed instruction additions, preserving owner records, backups and OpenClaw settings. No automatic global instruction edit.

Limitations: POSIX only; bounded history fails closed at 2MB/project and aggregate history and projection output are preflighted against 2MB before record commit; no history compaction or server mutation routes; no technically enforced reviewer separation; no model/channel adherence proof. No automatic transcript/credential collection or telemetry. Owner-supplied text/artifacts can contain secrets; there is no content-level secret filter. Never submit sensitive data for display. No private engine or policy data was copied into this candidate.

## Accounting and result scope

Before executing, include permitted result-artifact writes in the reviewed task scope. See [token accounting](token-accounting.md) for separate reference-only usage normalization and attribution; this owner ledger does not automatically capture runtime tokens.

## Explicit intake and review commands

Initialize a new viewer/data root without demo content. Separately create owner-controlled artifact and mode-0700 request directories. Prepare mode-0600 reviewed JSON envelopes; never include credentials or sensitive text. Substitute only selected paths:

```sh
mcc --config-dir /your/new/config --data-dir /your/new/data init
mcc-owner --data-dir /your/new/data --artifact-root /your/artifacts apply --request-root /your/requests --request-file create.json --human
mcc-owner --data-dir /your/new/data --artifact-root /your/artifacts apply --request-root /your/requests --request-file propose.json
mcc-owner --data-dir /your/new/data --artifact-root /your/artifacts apply --request-root /your/requests --request-file authorize.json --human
mcc-owner --data-dir /your/new/data --artifact-root /your/artifacts apply --request-root /your/requests --request-file checkpoint.json
mcc-owner --data-dir /your/new/data --artifact-root /your/artifacts read --project-id reading-plan
mcc-owner --data-dir /your/new/data --artifact-root /your/artifacts reconcile
```

Example create.json:

```json
{"project_id":"reading-plan","expected_revision":0,"operation_key":"create-reading-plan","operation":"create","payload":{"name":"Reading plan","objective":"Prepare an outline","roadmap":["Plan","Write","Review"]}}
```

Read the returned revision before each next envelope. Proposal selects task_id/scope/criteria/artifact_paths; authorization selects exact task_id/task_revision. Start/evidence/finish also select a fresh attempt_id. Checkpoints record next_step/blockers. Finish means awaiting_review. Independently inspect artifacts and criterion methods before manual accept/reject using exact task/attempt revisions and evidence_digest; rejection also requires reason. After rejection, fresh authorization and a new attempt preserve prior history. Apply resume with empty payload and --human for paused projects; unknown running attempts need explicit interruption, not redispatch. Never give agents reviewer authority.

Serve the same owner data root and unlock locally. Expand Canonical task history and the nested task to inspect scope, criteria, authorization, attempts/evidence and review decisions. Canonical history can differ from stale projected summaries; new projects absent from the old snapshot appear after reconciliation. Registry history is capped at 2,000,000 encoded bytes and fails closed; no compaction. Polling runs every two seconds; one small synthetic fixture observed 112 ms, not a capacity guarantee.
