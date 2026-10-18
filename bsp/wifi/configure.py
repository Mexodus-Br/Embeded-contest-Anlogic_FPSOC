#!/usr/bin/python3
"""Board-local WPA2-PSK provisioner. Never pass credentials on argv or print them."""
import getpass
import hashlib
import os
import re
import sys
import tempfile
import warnings
from pathlib import Path

def render(ssid, password, country):
    raw = ssid.encode('utf-8')
    if not 1 <= len(raw) <= 32:
        raise ValueError('SSID must contain 1..32 UTF-8 bytes')
    if not re.fullmatch('[A-Z]{2}', country):
        raise ValueError('Use the actual installation country code (two uppercase letters)')
    if re.fullmatch('[0-9a-fA-F]{64}', password):
        psk = password.lower()
    elif 8 <= len(password) <= 63 and all(32 <= ord(c) <= 126 for c in password):
        psk = hashlib.pbkdf2_hmac('sha1', password.encode('ascii'), raw, 4096, 32).hex()
    else:
        raise ValueError('Use an 8..63 ASCII passphrase or 64 hex PSK')
    return ('ctrl_interface=DIR=/run/wifi-sta/control GROUP=0\n'
            'update_config=0\ncountry='+country+'\nnetwork={\n'
            '    ssid='+raw.hex()+'\n    psk='+psk+'\n'
            '    key_mgmt=WPA-PSK\n    proto=RSN\n    pairwise=CCMP\n}\n')

def main():
    if os.geteuid() != 0:
        raise SystemExit('root required')
    if not sys.stdin.isatty():
        raise SystemExit('Use a local board TTY; piped credential input is refused')
    warnings.simplefilter('error', getpass.GetPassWarning)
    os.umask(0o077)
    path = Path('/etc/wifi')
    path.mkdir(mode=0o700, exist_ok=True)
    if path.is_symlink() or path.stat().st_uid != 0:
        raise SystemExit('unsafe configuration directory')
    path.chmod(0o700)
    # Hide both SSID and secret from serial transcripts.
    ssid = getpass.getpass('SSID (hidden): ')
    password = getpass.getpass('WPA2 passphrase / hex PSK (hidden): ')
    country = input('Installation country code: ').strip().upper()
    content = render(ssid, password, country)
    # Revoke the previous qualification before replacing the network profile.
    (path/'autostart').unlink(missing_ok=True)
    fd, name = tempfile.mkstemp(prefix='.provision-', dir=str(path))
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path/'wpa_supplicant.conf')
        directory_fd = os.open(str(path), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    print('Local configuration saved (0600). Run wifi-sta start manually.')

if __name__ == '__main__':
    main()
