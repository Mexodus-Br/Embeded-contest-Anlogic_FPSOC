"""Verify and extract our release archive inside bsp/artifacts only."""
import hashlib
import json
from pathlib import Path
import tarfile

root = Path(__file__).resolve().parents[1]
archive = root/'artifacts/bsp-release.tar.gz'
expected = '43c4891b803110844350f64feef96cf6027bd5197975cc1fc901354693b17eac'
def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda: f.read(1 << 20), b''):
            h.update(data)
    return h.hexdigest()
assert sha(archive) == expected, 'Transfer checksum mismatch'
dest = root/'artifacts/bsp-release'
dest.mkdir(exist_ok=True)
with tarfile.open(archive,'r:gz') as t:
    for item in t.getmembers():
        path = (dest/item.name).resolve()
        assert path.is_relative_to(dest.resolve()), 'Unsafe path'
        assert item.isfile() or item.isdir(), 'Unexpected link or device'
    t.extractall(dest)
manifest = json.loads((dest/'release/manifest.json').read_text())
for name, meta in manifest['files'].items():
    path = dest/'release'/name
    assert path.stat().st_size == meta['bytes']
    assert sha(path) == meta['sha256'], 'Mismatch: '+name
print('Archive and',len(manifest['files']),'release files verified locally')
print('SD image SHA256',sha(dest/'release/sdcard.img'))
