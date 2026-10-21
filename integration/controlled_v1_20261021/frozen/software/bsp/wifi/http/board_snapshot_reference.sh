#!/bin/sh
set -eu
python3 - <<'PY'
import base64
from pathlib import Path
body=Path('/srv/wifi-http/exports/network-snapshot.txt').read_bytes()
print('BOARD_SNAPSHOT_BYTES='+str(len(body)))
print('BOARD_SNAPSHOT_BASE64='+base64.b64encode(body).decode())
PY
