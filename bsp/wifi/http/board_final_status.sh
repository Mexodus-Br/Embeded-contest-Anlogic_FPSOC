#!/bin/sh
set -eu
echo WIFI_FINAL_STATE_BEGIN
wifi-sta status
wifi-http status
python3 - <<'PY'
from pathlib import Path
import base64,re,subprocess
for line in subprocess.check_output(['iw','dev','wlan0','link']).decode(errors='replace').splitlines():
 if re.match(r'\s*(freq|signal|tx bitrate|rx bitrate):',line):print(line.strip())
for name in ('wifi-sta/worker.pid','wifi-sta/wpa.pid','wifi-sta/dhcp.pid','wifi-http/server.pid'):
 p=Path('/run',name)
 if p.exists():
  pid=p.read_text().strip()
  print(name+'='+pid+' live='+str(Path('/proc',pid,'cmdline').exists()))
print('LOADED_MODULE_NAMES='+','.join(line.split()[0] for line in Path('/proc/modules').read_text().splitlines()))
body=Path('/srv/wifi-http/exports/network-snapshot.txt').read_bytes()
print('BOARD_SNAPSHOT_BASE64='+base64.b64encode(body).decode())
for line in Path('/proc/mounts').read_text().splitlines():
 if line.split()[1]=='/': print('ROOT_MOUNT='+line)
PY
echo WIFI_FINAL_STATE_END
