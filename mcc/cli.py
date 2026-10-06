import argparse
import json
import os
import secrets
from pathlib import Path
from .model import demo, decode_snapshot
from .fs import canonical, root_fd, read_at, write_at, initialize

def private_write(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(value)

def main():
    parser = argparse.ArgumentParser(description="M-command-center (MCC), local read-only viewer")
    parser.add_argument("--config-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init").add_argument("--demo", action="store_true")
    imp = sub.add_parser("import")
    imp.add_argument("--root", type=Path, required=True)
    imp.add_argument("--file", required=True)
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=8765)
    sub.add_parser("rotate-token")
    args = parser.parse_args()
    config, data = canonical(args.config_dir), canonical(args.data_dir)
    if config == data or config.is_relative_to(data) or data.is_relative_to(config):
        parser.error("Config and data directories must be separate")
    if args.command == "init":
        cfd, dfd = initialize(config), initialize(data)
        try:
            write_at(cfd,"auth-token",secrets.token_urlsafe(32)+"\n")
            write_at(dfd,"snapshot.json",json.dumps(demo() if args.demo else {"schema_version":1,"projects":[]},indent=2))
        finally:
            os.close(cfd);os.close(dfd)
        print("Initialized. Read the protected auth-token locally; do not paste it into URLs.")
    elif args.command == "import":
        cfd, dfd, ifd = root_fd(config), root_fd(data), root_fd(args.root)
        try:
            from .owner import reject_owner_root,locked
            with locked(data) as writer:
                reject_owner_root(writer)
                snapshot = decode_snapshot(read_at(ifd,args.file,2_000_000,private=False))
                write_at(writer,"snapshot.json",json.dumps(snapshot,indent=2))
        finally:
            for fd in (cfd,dfd,ifd):os.close(fd)
        print("Imported selected neutral snapshot only.")
    elif args.command == "rotate-token":
        cfd, dfd = root_fd(config), root_fd(data)
        try:write_at(cfd,"auth-token",secrets.token_urlsafe(32)+"\n")
        finally:
            os.close(cfd);os.close(dfd)
        print("Token rotated. Restart the viewer to revoke current sessions.")
    else:
        from .server import run
        run(config, data, args.port)
if __name__ == "__main__":
    main()
