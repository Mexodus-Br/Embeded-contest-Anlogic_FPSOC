"""Make an explicitly selected UART evidence copy without MACs or pointer values. No hashes."""
import argparse
from pathlib import Path
import re
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('destination',type=Path);a=p.parse_args()
assert a.source.resolve()!=a.destination.resolve()
text=a.source.read_bytes().decode(errors='replace').replace('\x00','').replace('\r\r\n','\n').replace('\r\n','\n')
text=re.sub(r'(?i)(?<![0-9a-f])(?:[0-9a-f]{2}[:,]){5}[0-9a-f]{2}(?![0-9a-f])','[MAC_REDACTED]',text)
text=re.sub(r'(?im)(get macaddr:)[^\n]*',r'\1[MAC_REDACTED]',text)
text=re.sub(r'(?i)\b(?:0x)?[0-9a-f]{16}\b','[POINTER_REDACTED]',text)
with a.destination.open('x',encoding='utf-8') as out:out.write(text)
print('Sanitized explicitly selected evidence; original preserved; no hash generated')
