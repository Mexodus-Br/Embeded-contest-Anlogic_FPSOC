"""POSIX offline HTTP/containment tests; loopback is NOT board LAN acceptance."""
import base64
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import HTTPServer

HERE=Path(__file__).resolve().parent
def module(name):
    spec=importlib.util.spec_from_file_location(name,str(HERE/(name+'.py')))
    value=importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value
server=module('server'); export=module('export')

class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        (self.root/'public').mkdir(); (self.root/'exports').mkdir()
        (self.root/'exports/test.bin').write_bytes(bytes(range(256))*1024)
        export.publish(self.root,dict(kernel='offline-fixture',source='OFFLINE_TEST_FIXTURE'))
        salt=bytes(range(16))
        auth=dict(user='tester',salt=salt.hex(),iterations=1000,digest=hashlib.pbkdf2_hmac('sha256',b'unit-test-only-password',salt,1000).hex())
        self.app=server.Application(self.root,auth)
        self.http=HTTPServer(('127.0.0.1',0),server.Handler); self.http.app=self.app
        self.thread=threading.Thread(target=self.http.serve_forever); self.thread.start()
        self.auth='Basic '+base64.b64encode(b'tester:unit-test-only-password').decode()
    def tearDown(self):
        self.http.shutdown(); self.thread.join(); self.http.server_close(); self.app.close(); self.temp.cleanup()
    def request(self,path,method='GET',auth=True):
        connection=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=5)
        connection.request(method,path,headers={'Authorization':self.auth} if auth else {})
        response=connection.getresponse(); result=(response.status,dict(response.getheaders()),response.read()); connection.close(); return result
    def test_auth_home_binary_snapshot_and_repeated_download(self):
        self.assertEqual(self.request('/',auth=False)[0],401)
        self.assertEqual(self.request('/')[0],200)
        for _ in range(3):
            code,headers,body=self.request('/files/test.bin')
            self.assertEqual(code,200); self.assertEqual(body,bytes(range(256))*1024)
            self.assertEqual(int(headers['Content-Length']),len(body))
            self.assertIn('test.bin',headers['Content-Disposition'])
        body=self.request('/files/network-snapshot.txt')[2]
        self.assertEqual(json.loads(body)['source'],'OFFLINE_TEST_FIXTURE')
        self.assertEqual(body,(self.root/'exports/network-snapshot.txt').read_bytes())
    def test_mutating_methods_unknown_and_traversal(self):
        for method in ('POST','PUT','DELETE','PATCH','CONNECT','TRACE','HEAD','OPTIONS'):
            self.assertEqual(self.request('/files/test.bin',method)[0],405)
        self.assertEqual(self.request('/files/missing.bin')[0],404)
        for path in ('/../etc/passwd','/files/%2e%2e/etc/shadow','/files/test.bin?x=1','/files/..\\auth.json','//etc/passwd','/etc/wifi/wpa_supplicant.conf'):
            self.assertIn(self.request(path)[0],(403,404))
    def test_symlink_hardlink_fifo_and_atomic_snapshot(self):
        file=self.root/'exports/test.bin'; file.unlink()
        secret=self.root/'secret'; secret.write_bytes(b'not public')
        file.symlink_to(secret); self.assertEqual(self.request('/files/test.bin')[0],403)
        file.unlink(); os.link(str(secret),str(file)); self.assertEqual(self.request('/files/test.bin')[0],403)
        file.unlink(); os.mkfifo(str(file)); self.assertEqual(self.request('/files/test.bin')[0],403)
        previous=(self.root/'exports/network-snapshot.txt').read_bytes()
        with self.assertRaises(KeyError): export.publish(self.root,dict(source='incomplete'))
        self.assertEqual((self.root/'exports/network-snapshot.txt').read_bytes(),previous)
        self.assertEqual(self.request('/files/network-snapshot.txt')[2],previous)
    def test_malformed_auth_is_rejected(self):
        for header in ('Basic !bad','Bearer token','Basic '+base64.b64encode('非ascii:x'.encode()).decode()):
            self.assertFalse(self.app.authorized(header))

if __name__=='__main__': unittest.main()
