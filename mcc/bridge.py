"""Explicit owner-reviewed file bridge; no OpenClaw or Gateway dependency."""
import argparse
import hashlib
import json
import os
from .fs import root_fd, read_at, write_at
from .model import decode_snapshot


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    p = argparse.ArgumentParser(description="Validate/review/publish one neutral snapshot")
    p.add_argument("--root", required=True)
    p.add_argument("--file", required=True)
    p.add_argument("--data-dir")
    p.add_argument("--expected-current", help="SHA-256 returned by dry-run; required to apply")
    p.add_argument("--expected-source", help="SHA-256 of the reviewed selected source")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    source_fd = root_fd(args.root)
    try:
        source = read_at(source_fd, args.file, 2_000_000)
        snapshot = decode_snapshot(source)
    finally:
        os.close(source_fd)
    if args.apply and not args.data_dir:
        p.error("--apply requires --data-dir")
    if not args.data_dir:
        print(json.dumps({"valid": True, "source_sha256": digest(source),
                          "project_ids": [x["id"] for x in snapshot["projects"]]}))
        return
    from .owner import locked as owner_locked
    owner_context=owner_locked(args.data_dir)
    fd=owner_context.__enter__()
    locked = False
    try:
        from .owner import reject_owner_root
        reject_owner_root(fd)
        # Cooperative writer lock. Existing import remains an owner-only operation;
        # stop concurrent import/file writers while reviewing or publishing.
        if args.apply:
            lock = os.open("bridge.lock", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                           0o600, dir_fd=fd)
            os.close(lock)
            locked = True
        current = read_at(fd, "snapshot.json", 2_000_000)
        previous = decode_snapshot(current)
        current_hash = digest(current)
        if {x["id"] for x in snapshot["projects"]} != {x["id"] for x in previous["projects"]}:
            raise ValueError("Identity set changed: creation/removal requires separate owner review and import")
        encoded = json.dumps(snapshot, indent=2)
        changed = snapshot != previous
        if args.apply:
            if args.expected_source != digest(source):
                raise ValueError("Source changed or absent review digest; review again")
            if args.expected_current != current_hash:
                raise ValueError("Stale or absent review digest; dry-run again")
            if changed:
                backup = "snapshot-" + current_hash + ".backup.json"
                try:
                    existing = read_at(fd, backup, 2_000_000)
                except FileNotFoundError:
                    write_at(fd, backup, current.decode("utf-8"))
                else:
                    if existing != current:
                        raise ValueError("Backup digest collision or corrupted backup")
                os.fsync(fd)  # Commit backup directory entry before replacing live state.
                write_at(fd, "snapshot.json", encoded)
                os.fsync(fd)
        print(json.dumps({"valid": True, "changed": changed, "applied": args.apply,
                          "current_sha256": current_hash, "source_sha256": digest(source),
                          "project_ids": [x["id"] for x in snapshot["projects"]]}))
    finally:
        if locked:
            os.unlink("bridge.lock", dir_fd=fd)
        owner_context.__exit__(None,None,None)

if __name__ == "__main__":
    main()
