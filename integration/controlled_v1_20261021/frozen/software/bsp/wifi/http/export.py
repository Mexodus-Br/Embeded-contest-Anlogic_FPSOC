#!/usr/bin/python3
"""Local controlled snapshot publication. Never called by an HTTP request."""
import datetime
import html
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path('/srv/wifi-http')

def atomic(directory,name,body):
    fd,temporary = tempfile.mkstemp(dir=str(directory),prefix='.publishing-')
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(body); stream.flush(); os.fsync(stream.fileno())
            os.fchmod(stream.fileno(),0o644)
        os.replace(temporary,str(directory/name))
    finally:
        if os.path.exists(temporary): os.unlink(temporary)

def collect(interface):
    def command(args):
        return subprocess.check_output(args,stderr=subprocess.DEVNULL,timeout=3,universal_newlines=True)
    kernel = command(['uname','-r']).strip()
    addresses = json.loads(command(['ip','-j','-4','addr','show','dev',interface]))
    ips = [{'ip':a['local'],'prefixlen':a['prefixlen']} for item in addresses for a in item.get('addr_info',[]) if a.get('family')=='inet']
    routes = json.loads(command(['ip','-j','-4','route','show','dev',interface]))
    state = command(['wpa_cli','-p','/run/wifi-sta/control','-i',interface,'status'])
    state = next((line.split('=',1)[1] for line in state.splitlines() if line.startswith('wpa_state=')),'UNKNOWN')
    if state != 'COMPLETED' or not ips:
        raise RuntimeError('Wi-Fi authentication/DHCP not complete; previous snapshot retained')
    match = re.search(r'(?:^| )root=PARTUUID=([0-9a-fA-F-]+)(?: |$)',Path('/proc/cmdline').read_text())
    usb = []
    for dev in Path('/sys/bus/usb/devices').iterdir():
        if (dev/'idVendor').exists():
            usb.append({'port':dev.name,'vid':(dev/'idVendor').read_text().strip(),'pid':(dev/'idProduct').read_text().strip()})
    return dict(format='wifi-diagnostics-v1',source='BOARD_LOCAL_COLLECTION',
                collected_utc=datetime.datetime.utcnow().isoformat()+'Z',kernel=kernel,
                root_partuuid=match.group(1) if match else 'unknown',
                uptime_seconds=Path('/proc/uptime').read_text().split()[0],
                interface=interface,wpa_state=state,ipv4=ips,
                routes=[{k:r[k] for k in ('dst','gateway','dev','prefsrc','metric') if k in r} for r in routes],usb=usb)

def publish(root,data):
    # All collection/validation succeeds before replacing a public stable file.
    payload=(json.dumps(data,indent=2,ensure_ascii=True)+'\n').encode()
    page=('''<!doctype html><html lang="en"><meta charset="utf-8"><title>Wi-Fi diagnostics</title>
<h1>Wi-Fi read-only diagnostics</h1><p>HTTP service: running; authenticated GET only.</p>
<p>Kernel: %s</p><p>Snapshot source: %s</p>
<p><a href="/files/test.bin">Binary test (262144 bytes)</a></p>
<p><a href="/files/network-snapshot.txt">Sanitized network / boot snapshot (%d bytes)</a></p>
<p><a href="/files/integration-snapshot.json">Locally collected SAF2 / DMA diagnostics</a></p>
<p>Production HOME and mechanical motion are not approved.</p>
<p>No motion commands, uploads, directory listing or remote collection.</p></html>''' %
          (html.escape(data['kernel']),html.escape(data['source']),len(payload))).encode()
    atomic(root/'exports','network-snapshot.txt',payload)
    atomic(root/'public','index.html',page)

def main():
    if os.geteuid()!=0: raise SystemExit('root local collector required')
    interface=Path('/etc/wifi/interface').read_text().strip() if Path('/etc/wifi/interface').exists() else 'wlan0'
    if not re.fullmatch('[A-Za-z0-9_.-]{1,15}',interface) or not Path('/sys/class/net',interface,'wireless').is_dir():
        raise SystemExit('Wireless interface absent')
    try: publish(ROOT,collect(interface))
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
        raise SystemExit('Snapshot collection failed; stable previous file retained') from error
    print('Published sanitized network-snapshot.txt (no hash generated)')

if __name__=='__main__': main()
