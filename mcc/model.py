"""Strict neutral snapshot contract. No private tracker parsing."""
import json
import re
from pathlib import Path
STATUSES = {"active", "paused", "blocked", "completed"}
FIELDS = {"id", "name", "objective", "status", "next_step", "blockers", "roadmap", "updated"}
def validate(data):
    if not isinstance(data, dict) or set(data) != {"schema_version", "projects"} or type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("Expected neutral snapshot schema v1")
    projects = data["projects"]
    if not isinstance(projects, list) or len(projects) > 200:
        raise ValueError("Invalid project collection")
    seen = set()
    for p in projects:
        if not isinstance(p, dict) or set(p) != FIELDS:
            raise ValueError("Only explicit neutral fields are accepted")
        if not isinstance(p["id"], str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", p["id"]) or p["id"] in seen:
            raise ValueError("Invalid or duplicate identity")
        seen.add(p["id"])
        if not isinstance(p["status"], str) or p["status"] not in STATUSES:
            raise ValueError("Invalid status")
        for key in ("name", "objective", "next_step", "updated"):
            if not isinstance(p[key], str) or len(p[key]) > 4000:
                raise ValueError("Invalid text")
        for key in ("blockers", "roadmap"):
            if not isinstance(p[key], list) or len(p[key]) > 100 or any(not isinstance(x, str) or len(x) > 2000 for x in p[key]):
                raise ValueError("Invalid list")
    return data

def decode_snapshot(value):
    try:
        return validate(json.loads(value))
    except (RecursionError, UnicodeError, TypeError) as e:
        raise ValueError("Invalid snapshot encoding or nesting") from e

def read_snapshot(path):
    from .fs import root_fd, read_at
    import os
    fd=root_fd(path.parent)
    try:return decode_snapshot(read_at(fd,path.name,2_000_000))
    finally:os.close(fd)

def selected_file(root, relative):
    root = Path(root).resolve(strict=True)
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("Select a relative contained path")
    source = root / rel
    for component in [source, *source.parents]:
        if component == root:
            break
        if component.is_symlink():
            raise ValueError("Symlinks are not permitted")
    source = source.resolve(strict=True)
    if not source.is_relative_to(root) or not source.is_file():
        raise ValueError("Selection escapes root")
    return source

def demo():
    rows = [("garden", "Community garden", "Plan a shared planting calendar", "active", "Review the spring beds", [], ["Map beds", "Choose seeds", "Review calendar"]), ("archive", "Field archive", "Organize synthetic research notes", "blocked", "Resolve file naming", ["Naming convention needs review"], ["Agree names", "Index notes"]), ("reading", "Reading room", "A quiet place for project recovery", "paused", "Resume when the reading list is ready", [], ["Draft reading list"])]
    return {"schema_version": 1, "projects": [dict(id=i, name=n, objective=o, status=s, next_step=x, blockers=b, roadmap=r, updated="2026-01-01") for i,n,o,s,x,b,r in rows]}
