"""Password stays in memory; controlled command/upload/download on build VM."""
import argparse,getpass,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'.host-python'))
import paramiko
p=argparse.ArgumentParser();p.add_argument('--host',default='192.168.43.134');p.add_argument('--cmd');p.add_argument('--put',nargs=2);p.add_argument('--get',nargs=2);a=p.parse_args()
client=paramiko.SSHClient();client.load_system_host_keys();client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
password=getpass.getpass('Build VM password: ')
client.connect(a.host,username='uisrc',password=password,allow_agent=False,look_for_keys=False,timeout=15)
password=None
try:
 if a.put or a.get:
  s=client.open_sftp()
  if a.put:s.put(*a.put)
  else:Path(a.get[1]).parent.mkdir(parents=True,exist_ok=True);s.get(*a.get)
  s.close()
 if a.cmd:
  _,out,err=client.exec_command(a.cmd,get_pty=True)
  for line in iter(out.readline,''):print(line,end='',flush=True)
  sys.exit(out.channel.recv_exit_status())
finally:client.close()
