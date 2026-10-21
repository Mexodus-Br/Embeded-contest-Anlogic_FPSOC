"""Task VM transport. Password read from terminal or WIFI_VM_PASSWORD environment."""
import argparse,getpass,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'.host-python'))
import paramiko
p=argparse.ArgumentParser();p.add_argument('--host',default='192.168.43.135');p.add_argument('--cmd');p.add_argument('--put',nargs=2);p.add_argument('--get',nargs=2);a=p.parse_args()
c=paramiko.SSHClient();c.load_system_host_keys();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
 c.connect(a.host,username='uisrc',password=os.environ.get('WIFI_VM_PASSWORD') or getpass.getpass('VM password: '),allow_agent=False,look_for_keys=False,timeout=15)
 if a.put or a.get:
  with c.open_sftp() as s:
   if a.put:s.put(*a.put)
   else:Path(a.get[1]).parent.mkdir(parents=True,exist_ok=True);s.get(*a.get)
 if a.cmd:
  _,o,e=c.exec_command(a.cmd,get_pty=True)
  for line in iter(o.readline,''):print(line,end='',flush=True)
  sys.exit(o.channel.recv_exit_status())
finally:c.close()
