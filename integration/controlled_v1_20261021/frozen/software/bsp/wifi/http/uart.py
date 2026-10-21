"""COM4 capture/commands without log hashes, reset, DTR or RTS changes."""
import argparse
import json
from pathlib import Path
import re
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'.host-python'))
import serial
p=argparse.ArgumentParser(); p.add_argument('--capture',action='store_true');p.add_argument('--script',type=Path);p.add_argument('--log',type=Path,required=True);p.add_argument('--stop-file',type=Path);p.add_argument('--seconds',type=float,default=300);a=p.parse_args()
s=serial.Serial(port=None,baudrate=115200,bytesize=8,parity='N',stopbits=1,timeout=.2,xonxoff=False,rtscts=False,dsrdtr=False);s.dtr=False;s.rts=False
data=bytearray();count=0;status=0
with a.log.open('xb') as output:
    def receive(pattern,seconds):
        end=time.monotonic()+seconds; current=bytearray()
        while time.monotonic()<end:
            if a.capture and a.stop_file and a.stop_file.exists(): return
            chunk=s.read(65536)
            if chunk:
                output.write(chunk);output.flush();data.extend(chunk);current.extend(chunk)
                if pattern:
                    match=re.search(pattern,bytes(current).replace(b'\r',b''))
                    if match:return match
        if pattern:raise TimeoutError('Console marker not found')
    try:
        s.port='COM4';s.open()
        print('COM4_READY_DTR_RTS_FALSE',flush=True)
        if a.capture: receive(None,a.seconds)
        else:
            s.write(b'\r');s.flush();m=receive(rb'login:|(?:^|\n)# ',15)
            if m[0]==b'login:':
                s.write(b'root\r');receive(rb'Password:',10);s.write(b'root\r');receive(rb'(?:^|\n)# ',10)
            s.write(b"stty -echo; printf '\\nWIFI_ECHO_OFF\\n'\r");s.flush()
            receive(rb'\nWIFI_ECHO_OFF\n',10)
            script=a.script.read_text().replace('\r\n','\n')
            command="sh <<'WIFI_REVIEWED_EOF'\n"+script+"\nWIFI_REVIEWED_EOF\nrc=$?; stty echo; printf '\\nWIFI_EXIT=%s\\n' \"$rc\"\n"
            raw=command.encode('ascii').replace(b'\n',b'\r')
            for index in range(0,len(raw),128):s.write(raw[index:index+128]);s.flush();time.sleep(.03)
            result=receive(rb'\nWIFI_EXIT=(\d+)\n',a.seconds)
            status=int(result[1])
            print('WIFI_SCRIPT_EXIT='+result[1].decode())
        print(bytes(data)[-16000:].decode(errors='replace'))
    finally:
        s.close()
        a.log.with_suffix(a.log.suffix+'.json').write_text(json.dumps(dict(port='COM4',baud=115200,dtr=False,rts=False,received_bytes=len(data),log_hashed=False),indent=2)+'\n')
raise SystemExit(status)
