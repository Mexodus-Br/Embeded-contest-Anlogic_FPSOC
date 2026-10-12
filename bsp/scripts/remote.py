"""SSH helper; password is read from stdin and never saved. Uses known_hosts."""
import argparse
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / '.host-python'))
import paramiko

p = argparse.ArgumentParser()
p.add_argument('--host', default='192.168.43.133')
p.add_argument('--user', default='uisrc')
p.add_argument('--command')
p.add_argument('--command-file')
p.add_argument('--put', nargs=2)
p.add_argument('--get', nargs=2)
a = p.parse_args()
c = paramiko.SSHClient()
c.load_host_keys(str(pathlib.Path.home() / '.ssh' / 'known_hosts'))
c.set_missing_host_key_policy(paramiko.RejectPolicy())
c.connect(a.host, username=a.user, password=sys.stdin.readline().rstrip('\r\n'),
          allow_agent=False, look_for_keys=False, timeout=15)
try:
    if a.put or a.get:
        s = c.open_sftp()
        if a.put:
            s.put(*a.put)
        if a.get:
            s.get(*a.get)
        s.close()
    if a.command or a.command_file:
        cmd = a.command or pathlib.Path(a.command_file).read_text(encoding='utf-8')
        _, out, err = c.exec_command(cmd)
        # Commands used for long builds redirect logs and return a PID.
        sys.stdout.buffer.write(out.read())
        sys.stderr.buffer.write(err.read())
        sys.exit(out.channel.recv_exit_status())
finally:
    c.close()
