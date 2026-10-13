"""Preserve UART evidence and extract exact JSON arrays for ARM comparison."""
import argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('log',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
text=a.log.read_bytes().replace(b'\r',b'').decode('ascii')
a.out.mkdir(parents=True,exist_ok=True)
for name,marker in [('model','ARM_MODEL_JSON'),('oracle','ARM_ORACLE_JSON')]:
 section=text.split(marker+'_BEGIN\n',1)[1].split(marker+'_END',1)[0]
 assert all(x.startswith('{') for x in section.splitlines()),'UART insertion/partial JSON; inspect raw, do not silently repair'
 (a.out/(name+'.jsonl')).write_text(section,encoding='utf-8')
print('Extracted exact ARM JSON; raw log untouched')
