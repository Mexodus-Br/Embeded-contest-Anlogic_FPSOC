#!/bin/sh
set -eu
python3 - <<'PY'
import json,re,subprocess,time
start=time.monotonic()
boot_start=float(open('/proc/uptime').read().split()[0])
print('BOARD_STABILITY_START='+str(boot_start),flush=True)
rounds=[]
def command(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=5)
 return p.returncode,p.stdout.decode(errors='replace')
while True:
 elapsed=time.monotonic()-start
 state=command(['wpa_cli','-p','/run/wifi-sta/control','-i','wlan0','status'])[1]
 allowed=dict(line.split('=',1) for line in state.splitlines() if line.startswith(('wpa_state=','ip_address=','key_mgmt=')))
 gateway=command(['ping','-I','wlan0','-c','1','-W','1','192.168.2.1'])[0]
 event=dict(elapsed_seconds=round(elapsed,2),gateway_ping_exit=gateway,**allowed)
 rounds.append(event);print(json.dumps(event),flush=True)
 if elapsed>=600:break
 time.sleep(10)
lines=command(['dmesg'])[1].splitlines()
usb=[]
for line in lines:
 m=re.match(r'\[\s*([0-9.]+)\]',line)
 if m and float(m.group(1))>=boot_start and re.search(r'usb.*(reset|disconnect|error)|firmware.*(fail|error)',line,re.I):usb.append(line)
print('BOARD_STABILITY_END='+json.dumps(dict(elapsed_seconds=round(time.monotonic()-start,2),rounds=len(rounds),not_completed=sum(r.get('wpa_state')!='COMPLETED' for r in rounds),gateway_failed=sum(r['gateway_ping_exit']!=0 for r in rounds),usb_or_firmware_events=usb)),flush=True)
PY
