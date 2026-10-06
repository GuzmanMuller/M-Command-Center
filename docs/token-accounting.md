# Token accounting: reference-only workflow

Public v0.3 has structured task history, **not connected automatic runtime token capture**. This guide and the new standalone pure module are a reference accounting-only workflow. They do not install an OpenClaw plugin, collect transcripts, query databases, call APIs, update owner metrics or implement a scheduler. No full token-support claim is made. All fixture labels and numbers are invented; model labels beginning with example- are not runtime model identifiers.

## Try the synthetic reference

From a reviewed checkout on Linux / Python 3.12 (CI):

```sh
python3 -m mcc.accounting examples/accounting.json
python3 -m mcc.accounting examples/accounting.json --minimum-coverage 0.99
python3 -m unittest discover -s tests -p test_accounting.py -v
```

The fixture has four observations, three unique turns, one identical replay, two proven effective models and one unknown effective model with a named missing binding. Unique total is 210; assigned total is 200; unresolved total is 10. The stricter policy rejects publication eligibility without rejecting the diagnostic report. These are synthetic examples, not account usage.

The optional neutral-file API is normalize(document, minimum_coverage=0.8) in mcc.accounting. CLI reads only the named JSON file (1 MB maximum, 1,000 observations); prints JSON to stdout; exit 2 rejects malformed inputs/conflicts. Exit 0 means a parsed report, NOT permission to publish: inspect publication_eligible. No persistence or last-good metric writer is included. Do not pipe private reports into public logs. Neutral validation is not a privacy redactor. Select only trusted regular files; this simple CLI does not enforce owner-root permissions, no-follow selection or a FIFO timeout.

## Neutral v1 contract

See examples/accounting.json for exact required keys; unknown keys and versions fail closed. Each event has origin, provider, run_type, run_id, turn_id, requested_model, selected_model, response_model, accounting, usage and binding. Labels are bounded neutral strings. A binding is exactly project + task, or a named unresolved reason. The module trusts this supplied binding; it cannot validate an external project/task registry or prove source completeness. Those are caller responsibilities.

- Usage fields: input, cached_input, output, reasoning_output, total. Integers are nonnegative; null means unknown, zero means measured zero. Cached input is a subset of input; reasoning output is a subset of output. Neither subset is an extra addend. This contract defines total = input + output when all are known; adapt incompatible provider definitions explicitly, never pretend they match.
- Unknown field contributions keep the corresponding aggregate null. A known subset with an unknown parent is rejected because its containment cannot be checked. Empty sums are zero but empty/unknown total denominators have null coverage and cannot pass the gate.
- Requested configuration, selected turn configuration and proven effective response identity are different. Only explicit source responseModel-equivalent metadata establishes response_model. Otherwise effective_model is null even when requested/selected are known. Normalize per TURN; a session can change models/providers/tasks.
- Stable identity is origin + provider + typed run ID + turn ID. origin is the SOURCE, not a mirror session owner. Identical replays count once; any different immutable event under that identity fails closed. Do not silently accept conflicting counters or bindings. Mirrored observations must remove mirror-specific decoration before this neutral contract; retain private provenance separately. Late corrections require an explicit new audited epoch, not mutation hidden behind replay.
- Only delta accounting is accepted. Cumulative sources must be converted with documented reset boundaries and ordered snapshots; do not sum cumulative observations. A latest session snapshot may be appropriate for a session-total report, but cannot reconstruct per-turn models without turn evidence. Unknown baselines, resets and counter decreases remain unresolved. The reference deliberately ships no cumulative adapter.

## Binding and reconciliation checklist

1. Choose canonical project IDs from the owner registry; verify global uniqueness. Verify each task actually belongs to the selected project. Do not create tasks just to make coverage look better.
2. Bind dedicated runs/tasks explicitly at intake. For mixed chats, bind source-proven turn ranges/segments, never retroassign the entire conversation from its title, paths, latest owner or prose. Disagreeing hints become ambiguous/invalid_binding, not an arbitrary winner.
3. Keep OpenClaw session IDs and Codex native thread IDs structurally typed. Resolve source-native IDs through supported metadata with structural provenance. An environment variable such as CODEX_SESSION_ID is not universal proof of current identity or available in all runtimes. Do not substitute the newest thread or a mirror conversation ID.
4. Normalize and deduplicate before attribution. Every unique unit enters exactly one assigned project/task or one named unresolved category. Reconcile source = assigned + named unresolved for EVERY known field, including provider/effective-model strata. If a field is null, reconciliation is explicitly unproven for that field, not equality of zeroes. Report unknown counts/fields alongside known totals.
5. Define coverage against the same nonoverlapping source window and total definition. An example 80% policy is configurable local policy, **not a universal OpenClaw requirement**. Even passing coverage leaves unresolved usage visible. Unknown/missing sources and incomplete reads cannot claim complete coverage.
6. Before any production publisher: require identity, reconciliation, completeness and local coverage gates. On failure, preserve last-good derived metrics and surface the new partial report's timestamp, window, confidence and withheld reason separately. Do not overwrite a valid historical ledger with a deceptively complete partial one. Atomically update only authorized derived fields; preserve objectives, roadmap, state and review history; read back and reconcile. This module only returns eligibility; that publisher is not implemented here.

## Repair prospectively before considering backfill

Earlier attribution gaps are not mandatory cleanup. Establish a new cutover epoch with explicit bindings; keep legacy unknowns intact. A fresh incremental interval and rolling historical coverage have different denominators and cannot be plotted as like-for-like improvement. Label method, observation boundary, epoch and window; compare only same-method cohorts.

A future lightweight read-only collector should pin the supported source snapshot, capture indexed sequence frontiers, and read only changed per-session ranges under strict row/byte/time/session budgets. Persist source identity, snapshot version, high-water marks and digest-bound processed ranges atomically with accounting state. Crash resume must replay deterministically; source rewrites, identity changes or lost baselines fail closed. Unseen sessions need their own snapshot-pinned starting frontier. Budget exhaustion means partial diagnostic output, not completeness. A fully parsed report is not proof that all sources were available.

Use a **documented supported source interface**, check capabilities and version, and export minimal accounting metadata only: counters, proven response identity, typed source IDs and approved bindings. Exclude conversation text, credentials, personal records and scheduler/host/account state. If supported exports use compression, decode with version-aware bounded expansion and declared-length validation. No internal SQLite table queries, raw database adapter or claimed public decoder API are shipped here. If the runtime has no supported accounting export, state unavailable and use manually reviewed neutral fixtures; do not invent an endpoint.

Full backfill is a separate owner-authorized detached job on a capable host, not a default full scan on a small orchestration machine. If an authorized source snapshot is needed, use documented WAL-consistent backup semantics and protected transport/storage; do not force a live checkpoint. Never delete embeddings/caches, mutate Gateway/config or install a recurring model-powered accounting job as a repair shortcut. Deterministic incremental collection should use no daily model tokens; model interpretation is optional.

## Task lifecycle pitfalls (not an upstream bug claim)

Define intake authority and execution/result-artifact write scopes BEFORE execution. Read-only verification may still require a permitted result write. Use only the public owner-record transitions documented in [owner-records.md](owner-records.md) for this repository; the public helper records work and does not manage runtime execution. Include criteria, exact artifact paths, checkpoints and owner review. Scope is not a stock-tool sandbox; normal tool approvals still apply.

For a separate system with supported run/review contracts, external evidence attachment is valid only for actual registered runs under that system's rules. Never fabricate a run/reviewer, reuse an immutable grant with changed content, patch lifecycle databases or bypass a denied scope. If refinement/import is unsupported, report the mismatch and seek its supported resolution; do not claim a private implementation gap is a public MCC or OpenClaw defect. Real execution evidence and accepted lifecycle state are distinct.

## Optional future cost estimates

Tokens are usage, not invoices. Dated provider/model pricing, currency, cache/reasoning billing rules and effective identity would be needed for cost estimates. Keep estimates separate from measured usage and reconcile bills independently. Subscription/SaaS usage may have unknown marginal cost; unknown is not free or zero. No price fetcher or billing logic is included.

## Privacy and adoption

Keep production exports and checkpoints protected and outside Git. Publish only reviewed synthetic examples. Review exact changed files, paths, workflow strings and provenance independently before publication; shape validation alone does not catch secrets. This reference was written anew rather than transplanting a private runtime implementation. MIT covers code/docs, not the separately retained artwork rights. No automatic adoption, live collector, database access, runtime capture, metrics UI or integration certification is supplied.
