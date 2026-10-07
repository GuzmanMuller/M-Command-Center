# Changelog

## Unreleased

- Fsync the containing directory after atomic v1 writes so the basic snapshot/token path follows the durability discipline already used by owner records.
- Search project IDs, next steps, blockers, roadmaps and canonical task metadata in addition to name/objective.
- Run the regression suite across the declared Python 3.11-3.13 support range.
- Align v0.3 public documentation and distinguish interactive verification from CI coverage.

## 0.3.0

- Optional canonical v2 owner-managed project/task ledger with revision checks, scoped transitions, idempotent receipts, digest-bound evidence and procedural review/retry history.
- Authenticated expandable task history, automatic two-second freshness polling and stale projection/recovery display.
- Separate dedicated owner roots and backup/reconcile guidance; v1 neutral snapshots remain supported.
- Synthetic regression, process-exit recovery, clean package and browser checks. Real model/session/channel adherence, enforced reviewer identity and capacity/power-loss certification are not claimed.

MIT code/documentation and artwork exclusion remain unchanged.
