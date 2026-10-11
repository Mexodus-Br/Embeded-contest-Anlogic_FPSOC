from pathlib import Path
import re
for name in ['alps', 'hpfTool']:
    p = Path(r'D:\Anlogic\TD_Release_2026.1_SP2.200.067\bin') / (name + '.exe')
    strings = re.findall(rb'[\x20-\x7e]{5,}', p.read_bytes())
    print(name)
    for i, s in enumerate(strings):
        if s.startswith(b'-') and len(s) < 60 or b'Usage:' in s:
            print(s.decode()[:300])
