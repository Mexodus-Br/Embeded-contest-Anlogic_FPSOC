"""PC-side real LAN acceptance; credentials stay in memory, diagnostics never hashed."""
import argparse
import base64
import datetime
import getpass
import http.client
import ipaddress
import json
from pathlib import Path
import subprocess
import time

p=argparse.ArgumentParser();p.add_argument('--board',required=True);p.add_argument('--source',required=True);p.add_argument('--user');p.add_argument('--credentials',type=Path);p.add_argument('--seconds',type=int,default=0);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
for value in (a.board,a.source): ipaddress.IPv4Address(value)
if a.credentials:
    credentials=json.loads(a.credentials.read_text());user=credentials['user'];password=credentials['password']
else:
    user=a.user or input('HTTP user: ');password=getpass.getpass('HTTP password (hidden): ')
authorization='Basic '+base64.b64encode((user+':'+password).encode()).decode()
password=None
a.output.mkdir(parents=True,exist_ok=True)
def request(path,authorized=True,method='GET'):
    connection=http.client.HTTPConnection(a.board,8080,timeout=5,source_address=(a.source,0))
    try:
        connection.request(method,path,headers={'Authorization':authorization} if authorized else {})
        response=connection.getresponse();headers=dict(response.getheaders());body=response.read(8*1024*1024+1)
        return response.status,headers,body
    finally: connection.close()
events=[]
def check():
    code,headers,body=request('/')
    assert code==200 and b'Wi-Fi read-only diagnostics' in body,'homepage'
    code,headers,body=request('/files/test.bin')
    assert code==200 and len(body)==262144 and int(headers['Content-Length'])==len(body),'binary length'
    assert body==bytes(range(256))*1024,'byte-for-byte binary comparison'
    assert 'test.bin' in headers['Content-Disposition']
    (a.output/'test.bin').write_bytes(body)
    code,headers,body=request('/files/network-snapshot.txt')
    assert code==200 and int(headers['Content-Length'])==len(body),'snapshot download'
    snapshot=json.loads(body)
    assert snapshot['source']=='BOARD_LOCAL_COLLECTION' and snapshot['wpa_state']=='COMPLETED'
    assert any(item['ip']==a.board for item in snapshot['ipv4'])
    (a.output/'network-snapshot.txt').write_bytes(body) # No digest for diagnostic data.
    assert request('/files/network-snapshot.txt')[2]==body,'stable snapshot reconnect download'
    return len(body)
assert request('/',False)[0]==401
assert request('/files/network-snapshot.txt',False)[0]==401
assert request('/files/missing.bin')[0]==404
for path in ('/../etc/passwd','/files/%2e%2e/etc/shadow','/etc/wifi/wpa_supplicant.conf'):
    assert request(path)[0] in (403,404)
for method in ('PUT','DELETE','POST'):
    assert request('/files/test.bin',method=method)[0]==405
start=time.monotonic();failures=0;attempts=0
while True:
    attempts+=1
    event={'utc':datetime.datetime.utcnow().isoformat()+'Z','attempt':attempts}
    try:
        event['snapshot_bytes']=check();event['http']='PASS'
        ping=subprocess.run(['ping','-n','1','-w','1000','-S',a.source,a.board],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        event['ping_exit']=ping.returncode
        with (a.output/'ping.txt').open('ab') as stream:stream.write(ping.stdout)
        if ping.returncode:failures+=1
    except (OSError,ValueError,AssertionError,http.client.HTTPException) as error:
        failures+=1;event['http']='FAIL';event['reason']=type(error).__name__+': '+str(error)
    events.append(event)
    print(json.dumps(event),flush=True)
    (a.output/'results.json').write_text(json.dumps(dict(board=a.board,pc_source=a.source,elapsed_seconds=time.monotonic()-start,attempts=attempts,failed_rounds=failures,events=events),indent=2)+'\n')
    if time.monotonic()-start>=a.seconds:break
    time.sleep(5)
raise SystemExit(1 if failures else 0)
