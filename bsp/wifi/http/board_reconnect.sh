#!/bin/sh
set -eu
echo WIFI_CONNECT_BEGIN
python3 - <<'PY'
import os, stat
for name in ('/etc/wifi/wpa_supplicant.conf', '/etc/wifi-http/auth.json'):
    info = os.stat(name)
    print(name, 'uid=%d mode=%o' % (info.st_uid, stat.S_IMODE(info.st_mode)))
    assert info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o600
PY
printf 'HTTP_PID_BEFORE_RECONNECT='; cat /run/wifi-http/server.pid
wifi-sta reconnect
ready=0
for attempt in $(seq 1 45); do
 if wpa_cli -p /run/wifi-sta/control -i wlan0 status | grep -qx 'wpa_state=COMPLETED' && ip -4 addr show dev wlan0 | grep -q 'inet '; then ready=1; break; fi
 sleep 1
done
wifi-sta status
test "$ready" = 1 || { echo WIFI_AUTH_DHCP_NOT_READY; exit 1; }
iw reg get
wifi-http-export
wifi-http start
wifi-http status
printf 'HTTP_PID_AFTER_RECONNECT='; cat /run/wifi-http/server.pid
python3 - <<'PY'
from pathlib import Path
assert Path('/srv/wifi-http/exports/test.bin').read_bytes()==bytes(range(256))*1024
print('BOARD_BINARY_REFERENCE_BYTE_COMPARE=PASS')
PY
echo WIFI_CONNECT_END
