"""Serial affected regressions; preserve all sealed raw evidence/metadata."""
import hashlib,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];E=R/'bsp/evidence/telemetry-regression-20261014a'
E.mkdir(exist_ok=False)
commands=[
 'pl_rs485/tests/run_telemetry.py --tag bsp20261014a',
 'pl_rs485/tests/run_telem_parse.py --tag bsp20261014a',
 'pl_rs485/tests/run_telem_results.py --tag bsp20261014a',
 'pl_rs485/tests/run_telem_irq.py --tag bsp20261014a',
 'pl_rs485/tests/run_telem_software.py --vectors pl_rs485/evidence/telemetry_bsp20261014a/frames.hex --tag bsp20261014a',
 'pl_rs485/tests/run_gp_software.py --tag bsp20261014a',
 'pl_rs485/tests/run_gp.py --tag bsp20261014a --seed 20261014',
 'pl_rs485/tests/run_multirate.py --tag bsp20261014a --seed 20261013',
 'pl_rs485/tests/run_sim.py --tag bsp20261014a --seed 20261013',
 'pl_dma/tests/run_telemetry_regressions.py --tag bsp20261014a']
saved={}
for manifest in ('pl_motion/GPIO_RELEASE.json','pl_rs485/evidence/identity_telemetry.json'):
 m=json.loads((R/manifest).read_text(encoding='utf-8'))
 for name in m['evidence_sha256']:
  p=R/name;saved[p]=p.read_bytes()
for folder in ('pl_motion','pl_dma'):
 for p in (R/folder).glob('*RESULTS*.json'):saved[p]=p.read_bytes()
results=[]
try:
 for i,cmd in enumerate(commands):
  log=E/(str(i)+'.log')
  with log.open('w',encoding='utf-8') as f:
   result=subprocess.run([sys.executable,*cmd.split()],cwd=R,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
  results.append({'command':cmd,'exit':result.returncode,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
  print(('PASS ' if result.returncode==0 else 'FAIL ')+cmd,flush=True)
  if result.returncode:break
finally:
 for p,b in saved.items():
  if p.read_bytes()!=b:p.write_bytes(b)
 (E/'result.json').write_text(json.dumps({'passed':len(results)==len(commands) and all(x['exit']==0 for x in results),'tests':results,'sealed_raw_evidence_restored':True},indent=2)+'\n',encoding='utf-8')
if len(results)!=len(commands) or any(x['exit'] for x in results):sys.exit(1)
