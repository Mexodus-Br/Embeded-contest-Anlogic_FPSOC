#!/usr/bin/python3
"""Fixed-route, authenticated read-only HTTP. No CGI, directory listing or commands."""
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import pwd
import socket
import stat
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = Path('/srv/wifi-http')
CONFIG = Path('/etc/wifi-http')
PORT = 8080

class Application:
    def __init__(self, root, auth):
        self.auth = auth
        self.cache = None
        self.fds = {}
        for name in ('public', 'exports'):
            self.fds[name] = os.open(str(root/name), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)

    def close(self):
        for fd in self.fds.values():
            os.close(fd)

    def authorized(self, header):
        if not header or len(header) > 1024 or not header.startswith('Basic '):
            return False
        if self.cache is not None and hmac.compare_digest(header, self.cache):
            return True
        try:
            user, password = base64.b64decode(header[6:], validate=True).decode('utf-8').split(':', 1)
            digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(self.auth['salt']), self.auth['iterations']).hex()
            valid = hmac.compare_digest(user, self.auth['user']) & hmac.compare_digest(digest, self.auth['digest'])
            if valid:
                self.cache = header
            return bool(valid)
        except (ValueError, UnicodeError, TypeError):
            return False

class Handler(BaseHTTPRequestHandler):
    server_version = 'WifiReadOnly/1'
    sys_version = ''
    protocol_version = 'HTTP/1.0'

    def setup(self):
        self.request.settimeout(5)
        super().setup()

    def log_message(self, *args):
        pass  # No URLs, Authorization headers, client identifiers or credentials in logs.

    def reply(self, code, body=b'', content_type='text/plain; charset=utf-8', filename=None):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'")
        self.send_header('Connection', 'close')
        if code == 401:
            self.send_header('WWW-Authenticate', 'Basic realm="wifi-diagnostics", charset="UTF-8"')
        if filename:
            self.send_header('Content-Disposition', 'attachment; filename="'+filename+'"')
        self.end_headers()
        try:
            if self.command != 'HEAD':
                self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            pass

    def do_GET(self):
        if not self.server.app.authorized(self.headers.get('Authorization')):
            self.reply(401, b'Authentication required\n')
            return
        routes = {'/':('public','index.html','text/html; charset=utf-8'),
                  '/index.html':('public','index.html','text/html; charset=utf-8'),
                  '/files/test.bin':('exports','test.bin','application/octet-stream'),
                  '/files/network-snapshot.txt':('exports','network-snapshot.txt','text/plain; charset=utf-8'),
                  '/files/integration-snapshot.json':('exports','integration-snapshot.json','application/json')}
        if any(token in self.path for token in ('%', '..', '\\', '?', '#')):
            self.reply(403, b'Path refused\n')
            return
        if self.path not in routes:
            self.reply(404, b'Not found\n')
            return
        directory, name, mime = routes[self.path]
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.server.app.fds[directory])
            with os.fdopen(fd, 'rb') as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 8*1024*1024:
                    self.reply(403, b'File refused\n')
                    return
                body = stream.read()
                if len(body) != info.st_size:
                    self.reply(503, b'File unavailable\n')
                    return
            self.reply(200, body, mime, name if directory == 'exports' else None)
        except FileNotFoundError:
            self.reply(404, b'Not found\n')
        except OSError:
            self.reply(403, b'File refused\n')

    def refused(self):
        self.reply(405, b'Only GET is supported\n')
    do_HEAD = do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_CONNECT = do_TRACE = refused

def main():
    if os.geteuid() != 0:
        raise SystemExit('Root launcher required to bind the wireless device and drop privileges')
    fd = os.open(str(CONFIG/'auth.json'), os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600:
            raise SystemExit('Authentication configuration must be root:0600')
        auth = json.load(stream)
    interface = (Path('/etc/wifi/interface').read_text().strip() if Path('/etc/wifi/interface').exists() else 'wlan0')
    if not interface or len(interface) > 15 or not all(c.isalnum() or c in '_.-' for c in interface):
        raise SystemExit('Invalid wireless interface')
    if not Path('/sys/class/net', interface, 'wireless').is_dir():
        raise SystemExit('Wireless interface absent')
    app = Application(ROOT, auth)
    account = pwd.getpwnam('wifihttp')
    http = HTTPServer(('0.0.0.0',PORT),Handler,bind_and_activate=False)
    http.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, interface.encode()+b'\0')
    http.server_bind()
    http.server_activate()
    http.app = app
    os.setgroups([])
    os.setgid(account.pw_gid)
    os.setuid(account.pw_uid)
    if os.geteuid() == 0:
        raise SystemExit('Privilege drop failed')
    try:
        http.serve_forever()
    finally:
        http.server_close()
        app.close()

if __name__ == '__main__':
    main()
