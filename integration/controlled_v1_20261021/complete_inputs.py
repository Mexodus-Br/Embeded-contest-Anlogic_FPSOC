"""Explicit generator/DT dependencies discovered during offline verification."""
from pathlib import Path
import json
import subprocess
H=Path(__file__).resolve().parent
R=H.parents[1]
m=json.loads((H/'sources.json').read_text())
names=subprocess.check_output(['git','ls-tree','-r','--name-only',m['baseline_commit']],cwd=R,text=True).splitlines()
for name in names:
    if ((name.startswith('pl_rs485/tools/generate') and name.endswith('.py')) or
        name in ['pl_safety/generate.py','pl_safety/generate_interlock.py','bsp/configs/kernel.dts','pl_rs485/rate_design.json','pl_rs485/schema.json'] or
        ('/generated/' in name and name.endswith('.md') and name.startswith(('pl_interface/','pl_rs485/','pl_safety/'))) or
        name.startswith('pl_safety/config/') and name.endswith('.json')):
        dest=H/'frozen/software'/name
        data=subprocess.check_output(['git','show',m['baseline_commit']+':'+name],cwd=R)
        if dest.exists():
            assert dest.read_bytes()==data,dest
            continue
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        m['files'].append({'path':dest.relative_to(H).as_posix(),'source':m['baseline_commit']+':'+name,'source_bytes':len(data)})
(H/'sources.json').write_text(json.dumps(m,indent=2)+'\n')
