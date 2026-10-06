"""Loopback-only authenticated HTTP viewer; no execution or project mutation routes."""
import hashlib
import hmac
import json
import secrets
import stat
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from .model import decode_snapshot
from .fs import root_fd, read_at
import os

def make_server(config, data, port=8765):
    cfd, dfd = root_fd(config), root_fd(data)
    try:token = read_at(cfd,"auth-token",256).decode("utf-8").strip()
    finally:os.close(cfd)
    if len(token) < 32:
        raise ValueError("Token is too short")
    sessions, attempts = {}, {}
    lock = threading.Lock()
    static = Path(__file__).parent / "static"
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)
            self.deadline_timer=threading.Timer(10, self.expire_request)
            self.deadline_timer.daemon=True
            self.deadline_timer.start()
        def expire_request(self):
            try:self.connection.shutdown(2)
            except OSError:pass
        def finish(self):
            self.deadline_timer.cancel()
            super().finish()
        def log_message(self, *args):
            pass  # Never log credentials, request bodies or paths.
        def send(self, code, body=b"", kind="text/plain; charset=utf-8", cookie=None):
            self.close_connection = True
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'none'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if cookie:
                self.send_header("Set-Cookie", cookie)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def boundary(self):
            expected = "127.0.0.1:" + str(self.server.server_port)
            try:u = urlsplit(self.path)
            except ValueError:
                self.send(400, b"Malformed request target");return False
            if self.headers.get_all("Host") != [expected] or u.query or u.scheme or u.netloc or u.fragment:
                self.send(400, b"Invalid request boundary")
                return False
            if self.headers.get("Origin") not in (None, "http://" + expected):
                self.send(403, b"Origin denied")
                return False
            return True
        def sid(self):
            try:
                cookie = SimpleCookie(self.headers.get("Cookie", ""))
                return cookie["mcc_session"].value if "mcc_session" in cookie else ""
            except Exception:
                return ""
        def authorized(self):
            with lock:
                expiry = sessions.get(self.sid(), 0)
                return expiry > time.monotonic()
        def do_GET(self):
            if not self.boundary():
                return
            if self.path in ("/", "/app.js", "/style.css"):
                name, kind = {"/":("index.html","text/html; charset=utf-8"), "/app.js":("app.js","text/javascript; charset=utf-8"), "/style.css":("style.css","text/css; charset=utf-8")}[self.path]
                self.send(200, (static / name).read_bytes(), kind)
            elif self.path in ("/api/projects", "/api/owner-state"):
                if not self.authorized():
                    self.send(401, b"Authentication required")
                    return
                try:
                    if self.path == "/api/owner-state":
                        from .owner import freshness,locked
                        with locked(data) as coherent:
                            body = json.dumps(freshness(coherent)).encode()
                    else:
                        body = json.dumps(decode_snapshot(read_at(dfd,"snapshot.json",2_000_000))).encode()
                    self.send(200, body, "application/json")
                except (ValueError, OSError):
                    self.send(503, b"Snapshot unavailable or invalid")
            else:
                self.send(404, b"Not found")
        def do_POST(self):
            if not self.boundary():
                return
            if self.headers.get("Origin") != "http://127.0.0.1:" + str(self.server.server_port):
                self.send(403, b"Origin required")
                return
            if self.headers.get("Transfer-Encoding") or len(self.headers.get_all("Content-Length", [])) > 1 or len(self.headers.get_all("Content-Type", [])) > 1:
                self.send(400);return
            if self.path == "/logout":
                with lock:
                    sessions.pop(self.sid(), None)
                self.send(204, cookie="mcc_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
                return
            if self.path != "/login":
                self.send(405, b"Read-only viewer")
                return
            if self.headers.get("Content-Type") != "application/json" or self.headers.get("Transfer-Encoding"):
                self.send(400)
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 1024:
                    raise ValueError()
                with lock:
                    now = time.monotonic()
                    recent = [x for x in attempts.get("local", []) if x > now - 60]
                    attempts["local"] = (recent + [now])[-10:]
                if len(recent) >= 10:
                    self.send(429, b"Try again later")
                    return
                supplied = json.loads(self.rfile.read(size)).get("token", "")
                if not isinstance(supplied, str) or not hmac.compare_digest(hashlib.sha256(supplied.encode()).digest(), hashlib.sha256(token.encode()).digest()):
                    self.send(401, b"Authentication failed")
                    return
            except (ValueError, AttributeError, RecursionError, UnicodeError):
                self.send(400)
                return
            sid = secrets.token_urlsafe(32)
            with lock:
                sessions.clear()  # Single local operator; bounded session state.
                sessions[sid] = time.monotonic() + 3600
            self.send(204, cookie="mcc_session=" + sid + "; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600")
        def do_PUT(self):
            self.send(405, b"Read-only viewer")
        do_DELETE = do_PATCH = do_PUT
    class BoundedServer(ThreadingHTTPServer):
        def __init__(self,*args):
            self.slots=threading.BoundedSemaphore(16)
            super().__init__(*args)
        def process_request(self,request,address):
            if not self.slots.acquire(blocking=False):
                self.shutdown_request(request);return
            super().process_request(request,address)
        def process_request_thread(self,request,address):
            try:super().process_request_thread(request,address)
            finally:self.slots.release()
        def server_close(self):
            super().server_close();os.close(dfd)
    server = BoundedServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.timeout = 5
    return server

def run(config, data, port):
    server = make_server(config, data, port)
    print("MCC local viewer: http://127.0.0.1:" + str(server.server_port))
    try:
        server.serve_forever()
    finally:
        server.server_close()
