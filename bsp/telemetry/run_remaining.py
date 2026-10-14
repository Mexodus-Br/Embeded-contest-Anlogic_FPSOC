"""Resume same regressions with a longer HOST wall-time budget, no RTL edits."""
import hashlib,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];E=R/'bsp/evidence/telemetry-regression-20261014b';E.mkdir(exist_ok=False)
sys.path.insert(0,str(R/'pl_rs485/tests'))
import run_multirate
def extended(args,cwd,env,log,timeout=180):
 with Path(log).open('w',encoding='utf-8') as f:r=subprocess.run(args,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=max(timeout,900))
 out=Path(log).read_text(encoding='utf-8');assert r.returncode==0,out[-2000:];return out
run_multirate.run=extended
saved={}
for name in ('pl_motion/GPIO_RELEASE.json','pl_rs485/evidence/identity_telemetry.json'):
 m=json.loads((R/name).read_text(encoding='utf-8'))
 for n in m['evidence_sha256']:p=R/n;saved[p]=p.read_bytes()
for d in ('pl_motion','pl_dma'):
 for p in (R/d).glob('*RESULTS*.json'):saved[p]=p.read_bytes()
results=[]
try:
 sys.argv=['run_multirate','--tag','bsp20261014b','--seed','20261013']
 run_multirate.main();results.append({'test':'same multirate vectors/markers','status':'PASS','host_timeout_seconds':900})
 for i,cmd in enumerate(['pl_rs485/tests/run_sim.py --tag bsp20261014b --seed 20261013','pl_dma/tests/run_telemetry_regressions.py --tag bsp20261014b']):
  with (E/(str(i)+'.log')).open('w',encoding='utf-8') as f:r=subprocess.run([sys.executable,*cmd.split()],cwd=R,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
  results.append({'test':cmd,'exit':r.returncode});print(('PASS ' if not r.returncode else 'FAIL ')+cmd,flush=True)
  if r.returncode:break
finally:
 for p,b in saved.items():
  if p.read_bytes()!=b:p.write_bytes(b)
 (E/'result.json').write_text(json.dumps({'tests':results,'sealed_raw_evidence_restored':True,'prior_180s_timeout':'retained; host runtime budget only changed'},indent=2)+'\n',encoding='utf-8')
if len(results)!=3 or any(x.get('exit',0) for x in results):sys.exit(1)
