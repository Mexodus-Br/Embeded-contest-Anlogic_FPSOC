"""Run one reviewed BSP script through UART; preserve raw bytes and metadata."""
import argparse,hashlib,json,re,sys,time
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'.host-python'))
import serial
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--script',type=Path,required=True)
p.add_argument('--arg',action='append',default=[])
p.add_argument('--log',type=Path,required=True)
p.add_argument('--seconds',type=float,default=300)
a=p.parse_args()
root=Path(__file__).resolve().parent
assert a.script.resolve().parent==root,'Use a reviewed script directly in bsp/scripts'
assert all(re.fullmatch(r'[a-zA-Z0-9/._-]+',v) for v in a.arg)
password=sys.stdin.readline().rstrip('\r\n').encode()
script=a.script.read_text(encoding='utf-8').replace('\r\n','\n')
s=serial.Serial(port=None,baudrate=115200,bytesize=8,parity='N',stopbits=1,timeout=.2,xonxoff=False,rtscts=False,dsrdtr=False)
s.dtr=False;s.rts=False
received=bytearray();sent=0;start=datetime.now(timezone.utc).isoformat();exit_code=None
def send(b):
 global sent
 sent+=s.write(b);s.flush()
def read_until(pattern,seconds):
 end=time.monotonic()+seconds;part=bytearray()
 while time.monotonic()<end:
  b=s.read(65536)
  if b:
   output.write(b);output.flush();received.extend(b);part.extend(b)
   m=re.search(pattern,bytes(part).replace(b'\r',b''))
   if m:return m
 raise TimeoutError('Expected console marker absent; raw evidence retained')
with a.log.open('xb') as output:
 try:
  s.port='COM4';s.open();send(b'\r')
  prompt=read_until(rb'login:|(?:^|\n)# ',15)
  if prompt[0]==b'login:':
   send(b'root\r');read_until(rb'Password:',10);send(password+b'\r');read_until(rb'(?:^|\n)# ',10)
  command="stty -echo\nsh -s -- "+' '.join(a.arg)+" <<'BSP_REVIEWED_SCRIPT_EOF'\n"+script+"\nBSP_REVIEWED_SCRIPT_EOF\nresult=$?; stty echo; printf '\\nBSP_SERIAL_EXIT=%s\\n' \"$result\"\n"
  data=command.encode('ascii').replace(b'\n',b'\r')
  for i in range(0,len(data),128):send(data[i:i+128]);time.sleep(.03)
  result=read_until(rb'\nBSP_SERIAL_EXIT=(\d+)\n',a.seconds);exit_code=int(result[1])
  print('UART_SCRIPT_EXIT='+str(exit_code),flush=True)
  print(bytes(received)[-5000:].decode('utf-8',errors='replace'),flush=True)
 finally:
  s.close()
  meta={'start_utc':start,'end_utc':datetime.now(timezone.utc).isoformat(),'port':'COM4','baud':115200,'format':'8N1','dtr':False,'rts':False,'sent_bytes':sent,'received_bytes':len(received),'sha256':hashlib.sha256(received).hexdigest(),'script':a.script.as_posix(),'script_sha256':hashlib.sha256(a.script.read_bytes()).hexdigest(),'arguments':a.arg,'script_exit':exit_code}
  a.log.with_suffix(a.log.suffix+'.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
sys.exit(exit_code if exit_code is not None else 1)
