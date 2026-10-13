"""Prompt without echo, then run the reviewed existing COM4 executor."""
import getpass,subprocess,sys
from pathlib import Path
password=getpass.getpass('Board password: ')
result=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/serial_exec.py'),*sys.argv[1:]],input=password+'\n',text=True)
password=None
sys.exit(result.returncode)
