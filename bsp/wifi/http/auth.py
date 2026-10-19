#!/usr/bin/python3
"""Local TTY only; independent HTTP password, salted verifier stored root:0600."""
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import warnings

def main():
    if os.geteuid() != 0 or not os.isatty(0):
        raise SystemExit('Use a local root TTY; no piped credentials')
    warnings.simplefilter('error',getpass.GetPassWarning)
    user = input('HTTP user (not root): ').strip()
    if not re.fullmatch('[A-Za-z0-9_-]{1,32}',user) or user == 'root':
        raise SystemExit('Invalid user')
    password = getpass.getpass('New independent HTTP password: ')
    if len(password) < 12 or len(password) > 128 or not password.isascii():
        raise SystemExit('Use 12..128 ASCII characters, independent of root/Wi-Fi passwords')
    if password != getpass.getpass('Repeat HTTP password: '):
        raise SystemExit('Passwords differ')
    os.umask(0o077)
    root = Path('/etc/wifi-http')
    root.mkdir(mode=0o700,exist_ok=True)
    if root.is_symlink() or root.stat().st_uid != 0:
        raise SystemExit('Unsafe configuration directory')
    root.chmod(0o700)
    salt = os.urandom(16)
    data = dict(user=user,salt=salt.hex(),iterations=120000,
                digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,120000).hex())
    fd,name = tempfile.mkstemp(dir=str(root),prefix='.auth-')
    try:
        with os.fdopen(fd,'w') as stream:
            json.dump(data,stream)
            stream.flush(); os.fsync(stream.fileno())
        os.replace(name,str(root/'auth.json'))
    finally:
        if os.path.exists(name): os.unlink(name)
    print('HTTP verifier saved root:0600. Restart wifi-http to apply.')

if __name__ == '__main__': main()
