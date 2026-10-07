import http.client
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from mcc.model import demo, validate, selected_file
from mcc.cli import private_write
from mcc.server import make_server
class ModelTests(unittest.TestCase):
    def test_demo_and_empty(self):
        self.assertEqual(len(validate(demo())["projects"]),3)
        validate({"schema_version":1,"projects":[]})
    def test_extra_fields_and_duplicate(self):
        d=demo();d["projects"][0]["private_data"]="not allowed"
        with self.assertRaises(ValueError):validate(d)
        d=demo();d["projects"].append(d["projects"][0])
        with self.assertRaises(ValueError):validate(d)
    def test_malformed_status(self):
        d=demo();d["projects"][0]["status"]=[]
        with self.assertRaises(ValueError):validate(d)
    def test_strict_version(self):
        for v in (True,1.0):
            d=demo();d["schema_version"]=v
            with self.assertRaises(ValueError):validate(d)
    def test_descriptor_files(self):
        from mcc.fs import root_fd,read_at,canonical
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);fd=root_fd(p)
            try:
                (p/'link').symlink_to('/etc/passwd')
                with self.assertRaises(OSError):read_at(fd,'link',100)
                os.mkfifo(p/'fifo')
                with self.assertRaises(ValueError):read_at(fd,'fifo',100)
                with self.assertRaises(ValueError):canonical(p/'link')
            finally:os.close(fd)
    def test_ancestry_init_and_descriptor_replacement(self):
        from mcc.fs import root_fd,initialize,write_at,read_at
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);unsafe=p/'unsafe';unsafe.mkdir(mode=0o777);os.chmod(unsafe,0o777)
            with self.assertRaises(ValueError):initialize(unsafe/'config')
            safe=p/'safe';fd=initialize(safe/'config')
            (safe/'config').rename(safe/'held')
            (safe/'config').symlink_to(p)
            write_at(fd,'auth-token','synthetic')
            self.assertFalse((p/'auth-token').exists())
            self.assertEqual((safe/'held/auth-token').read_text(),'synthetic')
            os.close(fd)
    def test_nested_descriptor_and_bounded_json(self):
        from mcc.fs import root_fd,read_at
        from mcc.model import decode_snapshot
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'nested').mkdir();(p/'nested/good.json').write_text(json.dumps(demo()))
            fd=root_fd(p)
            self.assertEqual(len(decode_snapshot(read_at(fd,'nested/good.json',2_000_000,False))['projects']),3)
            (p/'nested/link').symlink_to('/etc')
            with self.assertRaises(OSError):read_at(fd,'nested/link/passwd',200,False)
            (p/'large').write_bytes(b'x'*101)
            with self.assertRaises(ValueError):read_at(fd,'large',100,False)
            os.close(fd)
        with self.assertRaises(ValueError):decode_snapshot('['*2000+'0'+']'*2000)
    def test_paths(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/"good.json").write_text("{}")
            self.assertEqual(selected_file(p,"good.json"),p/"good.json")
            for x in ["../good.json",str(p/"good.json")]:
                with self.assertRaises(ValueError):selected_file(p,x)
            (p/"link").symlink_to(p/"good.json")
            with self.assertRaises(ValueError):selected_file(p,"link")
    def test_write_at_fsyncs_directory_after_replace(self):
        from unittest.mock import patch
        from mcc.fs import root_fd, write_at
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);fd=root_fd(p)
            try:
                with patch("mcc.fs.os.fsync") as fsync:
                    write_at(fd,"state.json","durable")
                    self.assertGreaterEqual(fsync.call_count,2)
                    self.assertEqual(fsync.call_args_list[-1].args[0],fd)
                self.assertEqual((p/"state.json").read_text(),"durable")
            finally:os.close(fd)
class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();p=Path(self.tmp.name)
        self.config=p/"config";self.data=p/"data";self.config.mkdir(mode=0o700);self.data.mkdir(mode=0o700)
        self.token="t"*48;private_write(self.config/"auth-token",self.token)
        private_write(self.data/"snapshot.json",json.dumps(demo()))
        self.server=make_server(self.config,self.data,0);self.port=self.server.server_port
        self.thread=threading.Thread(target=self.server.serve_forever);self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.thread.join();self.server.server_close();self.tmp.cleanup()
    def req(self,path,method="GET",body=None,headers=None):
        c=http.client.HTTPConnection("127.0.0.1",self.port,timeout=3)
        c.request(method,path,body,headers or {});r=c.getresponse();result=(r.status,dict(r.getheaders()),r.read());c.close();return result
    def login(self):
        return self.req("/login","POST",json.dumps({"token":self.token}),{"Origin":f"http://127.0.0.1:{self.port}","Content-Type":"application/json"})
    def test_auth_logout_and_mutation(self):
        self.assertEqual(self.req("/api/projects")[0],401)
        status,headers,_=self.login();self.assertEqual(status,204)
        cookie=headers["Set-Cookie"];self.assertIn("HttpOnly",cookie);self.assertIn("SameSite=Strict",cookie)
        h={"Cookie":cookie};self.assertEqual(self.req("/api/projects",headers=h)[0],200)
        self.assertEqual(self.req("/api/projects","DELETE",headers=h)[0],405)
        h["Origin"]=f"http://127.0.0.1:{self.port}"
        self.assertEqual(self.req("/logout","POST",headers=h)[0],204)
        self.assertEqual(self.req("/api/projects",headers=h)[0],401)
    def test_boundaries(self):
        self.assertEqual(self.req("/?token=x")[0],400)
        self.assertEqual(self.req("/",headers={"Host":"evil.example"})[0],400)
        self.assertEqual(self.req("/",headers={"Origin":"https://evil.example"})[0],403)
        self.assertEqual(self.req("/login","POST","{}")[0],403)
        self.assertEqual(self.req("/../../auth-token")[0],404)
        self.assertIn("frame-ancestors 'none'",self.req("/")[1]["Content-Security-Policy"])
    def test_fail_closed_bad_snapshot(self):
        _,headers,_=self.login();(self.data/"snapshot.json").write_text("{}")
        self.assertEqual(self.req("/api/projects",headers={"Cookie":headers["Set-Cookie"]})[0],503)
    def test_rate_limit_and_wrong_token(self):
        h={"Origin":f"http://127.0.0.1:{self.port}","Content-Type":"application/json"}
        for _ in range(10):
            self.assertEqual(self.req("/login","POST",'{"token":"wrong"}',h)[0],401)
        self.assertEqual(self.req("/login","POST",'{"token":"wrong"}',h)[0],429)
    def test_malformed_url_and_duplicate_framing(self):
        import socket
        with socket.create_connection(('127.0.0.1',self.port),timeout=3) as raw:
            raw.sendall(f'GET http://[broken HTTP/1.0\r\nHost: 127.0.0.1:{self.port}\r\n\r\n'.encode())
            self.assertIn(b' 400 ',raw.recv(1024))
        c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=3)
        c.putrequest('POST','/login');c.putheader('Origin',f'http://127.0.0.1:{self.port}');c.putheader('Content-Length','2');c.putheader('Content-Length','3');c.putheader('Content-Type','application/json');c.endheaders(b'{}')
        self.assertEqual(c.getresponse().status,400);c.close()
    def test_request_concurrency_and_deadline(self):
        import socket,time
        sockets=[]
        try:
            for _ in range(16):
                s=socket.create_connection(('127.0.0.1',self.port),timeout=2);s.sendall(b'GET / HTTP/1.0');sockets.append(s)
            time.sleep(.2)
            extra=socket.create_connection(('127.0.0.1',self.port),timeout=2);extra.sendall(b'GET / HTTP/1.0');self.assertEqual(extra.recv(10),b'');extra.close()
            # Total deadline closes a slowly arriving request even with activity.
            slow=sockets[0];start=time.monotonic();closed=False
            while time.monotonic()-start<12:
                try:slow.sendall(b' ')
                except OSError:closed=True;break
                time.sleep(.5)
            self.assertTrue(closed)
        finally:
            for s in sockets:s.close()
    def test_token_permissions(self):
        os.chmod(self.config/"auth-token",0o644)
        with self.assertRaises(ValueError):make_server(self.config,self.data,0)
if __name__=="__main__":unittest.main()
