"""Pure neutral accounting reference; no runtime capture or metric persistence."""
import argparse
import json
import math
import re
import sys

FIELDS = ("input", "cached_input", "output", "reasoning_output", "total")
LIMIT = 1_000_000


def label(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,80}", value):
        raise ValueError("Invalid neutral label")
    return value


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def aggregate(events):
    # Unknown contributions remain unknown, never silently become zero.
    return {f: None if any(e["usage"][f] is None for e in events)
            else sum(e["usage"][f] for e in events) for f in FIELDS}


def normalize(document, minimum_coverage=0.8):
    if type(minimum_coverage) not in (int, float) or not math.isfinite(minimum_coverage) or not 0 <= minimum_coverage <= 1:
        raise ValueError("Invalid coverage policy")
    if not isinstance(document, dict) or set(document) != {"schema_version", "source_complete", "events"}:
        raise ValueError("Invalid document")
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise ValueError("Unknown contract version")
    if type(document["source_complete"]) is not bool or not isinstance(document["events"], list) or len(document["events"]) > 1000:
        raise ValueError("Invalid source boundary")
    unique = {}
    for event in document["events"]:
        keys = {"origin", "run_type", "run_id", "turn_id", "provider", "requested_model", "selected_model", "response_model", "accounting", "usage", "binding"}
        if not isinstance(event, dict) or set(event) != keys:
            raise ValueError("Invalid event")
        for key in ("origin", "run_id", "turn_id", "provider"):
            label(event[key])
        if event["run_type"] not in ("openclaw-session", "codex-thread", "neutral-run") or event["accounting"] != "delta":
            raise ValueError("Unsupported identity/accounting type")
        for key in ("requested_model", "selected_model", "response_model"):
            if event[key] is not None:
                label(event[key])
        usage = event["usage"]
        if not isinstance(usage, dict) or set(usage) != set(FIELDS):
            raise ValueError("Invalid usage fields")
        for value in usage.values():
            if value is not None and (type(value) is not int or not 0 <= value <= 10**15):
                raise ValueError("Invalid token count")
        for subset, whole in (("cached_input", "input"), ("reasoning_output", "output")):
            if usage[subset] is not None and (usage[whole] is None or usage[subset] > usage[whole]):
                raise ValueError("Unproven subset")
        if all(usage[k] is not None for k in ("input", "output", "total")) and usage["total"] != usage["input"] + usage["output"]:
            raise ValueError("Total definition mismatch")
        binding = event["binding"]
        if not isinstance(binding, dict):
            raise ValueError("Invalid binding")
        if set(binding) == {"project", "task"}:
            label(binding["project"]); label(binding["task"])
        elif set(binding) == {"unresolved"}:
            label(binding["unresolved"])
        else:
            raise ValueError("Explicit binding or unresolved reason required")
        identity = tuple(event[k] for k in ("origin", "provider", "run_type", "run_id", "turn_id"))
        if identity in unique and unique[identity] != event:
            raise ValueError("Conflicting immutable source identity")
        unique[identity] = event
    events = list(unique.values())
    assigned = [e for e in events if "project" in e["binding"]]
    unresolved = [e for e in events if "unresolved" in e["binding"]]
    groups = {}
    for event in events:
        binding = event["binding"]
        key = (event["provider"], event["response_model"], binding.get("project"), binding.get("task"), binding.get("unresolved"))
        groups.setdefault(key, []).append(event)
    source = aggregate(events)
    attributed = aggregate(assigned)
    coverage = (attributed["total"] / source["total"]
                if source["total"] not in (None, 0) and attributed["total"] is not None else None)
    return {
        "schema_version": 1, "unique_turns": len(events), "duplicate_replays": len(document["events"]) - len(events),
        "source_complete": document["source_complete"], "source": source, "assigned": attributed,
        "unresolved": aggregate(unresolved), "coverage": coverage,
        "publication_eligible": document["source_complete"] and coverage is not None and coverage >= minimum_coverage,
        "minimum_coverage": minimum_coverage,
        "groups": [{"provider": k[0], "effective_model": k[1], "project": k[2], "task": k[3], "unresolved_reason": k[4], "usage": aggregate(v)} for k, v in groups.items()],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", help="Explicit neutral JSON file (no discovery)")
    parser.add_argument("--minimum-coverage", type=float, default=0.8)
    args = parser.parse_args()
    try:
        with open(args.file, "rb") as stream:
            raw = stream.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError("Neutral file exceeds byte budget")
        document = json.loads(raw, object_pairs_hook=strict_object)
        print(json.dumps(normalize(document, args.minimum_coverage), sort_keys=True, allow_nan=False))
    except (ValueError, OSError) as error:
        print("Accounting input rejected: " + str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
