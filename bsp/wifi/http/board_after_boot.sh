#!/bin/sh
set -eu
echo WIFI_POST_BOOT_BEGIN
uname -r
python3 - <<'PY'
from pathlib import Path
import re
line=Path('/proc/cmdline').read_text()
match=re.search(r'root=PARTUUID=([0-9a-fA-F-]+)',line)
print('root_partuuid='+match.group(1))
assert match.group(1)=='70d791a8-02'
for path in ('/etc/wifi/driver-approved','/etc/wifi/autostart','/etc/wifi-http/autostart'):
 assert Path(path).is_file(),path
print('LOCAL_AUTO_APPROVAL_FILES_PRESENT')
PY
ready=0
for attempt in $(seq 1 60); do
 if wpa_cli -p /run/wifi-sta/control -i wlan0 status 2>/dev/null | grep -qx 'wpa_state=COMPLETED' && ip -4 addr show dev wlan0 | grep -q 'inet '; then ready=1; break; fi
 sleep 1
done
test "$ready" = 1
wifi-sta status
for attempt in $(seq 1 15); do
 if [ -f /run/wifi-http/server.pid ] && kill -0 "$(cat /run/wifi-http/server.pid)" 2>/dev/null; then break; fi
 sleep 1
done
wifi-http status
python3 - <<'PY'
from pathlib import Path
import json
s=json.loads(Path('/srv/wifi-http/exports/network-snapshot.txt').read_text())
print('AUTO_SNAPSHOT_SOURCE='+s['source'])
print('AUTO_SNAPSHOT_UPTIME_SECONDS='+s['uptime_seconds'])
assert s['wpa_state']=='COMPLETED'
assert float(s['uptime_seconds']) <= float(Path('/proc/uptime').read_text().split()[0])
pid=Path('/run/wifi-http/server.pid').read_text().strip()
assert '/usr/lib/wifi-http/server.py' in Path('/proc',pid,'cmdline').read_text()
assert any(line.startswith('Uid:') and line.split()[1:] == ['498']*4 for line in Path('/proc',pid,'status').read_text().splitlines())
print('AUTO_HTTP_RUNNING_UID498')
assert Path('/srv/wifi-http/exports/test.bin').read_bytes()==bytes(range(256))*1024
print('BINARY_REFERENCE_BYTE_COMPARE=PASS')
loaded=Path('/proc/modules').read_text()
assert not any(name in loaded for name in ('bsp_motion','bsp_gp','anlogic_dma'))
print('MOTION_MODULES_ABSENT')
PY
wifi-usb
ping -I wlan0 -c 4 -W 1 192.168.2.1
echo WIFI_POST_BOOT_END
