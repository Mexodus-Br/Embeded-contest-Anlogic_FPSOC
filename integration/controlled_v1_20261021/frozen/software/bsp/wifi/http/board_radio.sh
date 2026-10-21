#!/bin/sh
set -eu
echo WIFI_RADIO_CHECK
wpa_cli -p /run/wifi-sta/control -i wlan0 status | sed -n '/^wpa_state=/p;/^key_mgmt=/p;/^ip_address=/p'
iw reg get
python3 - <<'PY'
from pathlib import Path
import subprocess,re
text=Path('/etc/wifi/wpa_supplicant.conf').read_text()
country=re.search(r'^country=([A-Z]{2})$',text,re.M)
print('configured_country='+ (country.group(1) if country else 'absent'))
m=re.search(r'\bssid=([0-9a-fA-F]+)',text)
if not m:
 print('configured_ssid_match=unsupported_format')
else:
 output=subprocess.run(['iw','dev','wlan0','scan'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
 lines=output.stdout.decode(errors='replace').splitlines()
 def ssid_bytes(value):
  pieces=re.split(r'(\\x[0-9a-fA-F]{2})',value)
  return b''.join(bytes.fromhex(piece[2:]) if re.fullmatch(r'\\x[0-9a-fA-F]{2}',piece) else piece.encode('utf-8') for piece in pieces)
 ssids=[ssid_bytes(s.split('SSID: ',1)[1] if 'SSID: ' in s else '') for s in lines if 'SSID:' in s]
 freqs=sorted(set(int(v.group(1)) for line in lines for v in [re.search(r'freq: ([0-9]+)',line)] if v))
 print('scan_frequencies_mhz='+str(freqs))
 print('scan_exit='+str(output.returncode))
 print('visible_network_count='+str(len(ssids)))
 print('configured_ssid_visible='+str(bytes.fromhex(m.group(1)) in ssids))
 print('scan_error='+output.stderr.decode(errors='replace').strip())
PY
echo WIFI_RADIO_CHECK_END
