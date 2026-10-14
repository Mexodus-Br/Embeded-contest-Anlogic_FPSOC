"""Serial real-IP tests; new tags; restore all preexisting frozen evidence bytes."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'pl_rs485/optimization'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);ap.add_argument('--start-at',type=int,default=0);a=ap.parse_args();tag=a.tag
 E=O/('regression_'+tag);E.mkdir(exist_ok=False)
 commands=[
 f'pl_rs485/tests/run_telemetry.py --tag {tag}',
 f'pl_rs485/tests/run_telem_parse.py --tag {tag}',
 f'pl_rs485/tests/run_telem_results.py --tag {tag}',
 f'pl_rs485/tests/run_telem_irq.py --tag {tag}',
 f'pl_rs485/tests/run_telem_software.py --vectors pl_rs485/evidence/telemetry_{tag}/frames.hex --tag {tag}',
 f'pl_rs485/tests/run_gp_software.py --tag {tag}',
 f'pl_rs485/tests/run_gp.py --tag {tag}gp --seed 20261014',
 f'pl_rs485/tests/run_sim.py --tag {tag} --seed 20261013',
 f'pl_dma/tests/run_telemetry.py --tag {tag}',
 f'pl_dma/tests/run_telemetry_system.py --tag {tag}',
 f'pl_dma/tests/run_telemetry_regressions.py --tag {tag}']
 saved={}
 for name in ('pl_motion/GPIO_RELEASE.json','pl_rs485/evidence/identity_telemetry.json'):
  m=json.loads((R/name).read_text(encoding='utf-8'))
  for n in m['evidence_sha256']:
   p=R/n;saved[p]=p.read_bytes()
 for d in ('pl_motion','pl_dma'):
  for p in (R/d).glob('*RESULTS*.json'):saved[p]=p.read_bytes()
 results=[]
 try:
  for i,cmd in enumerate(commands):
   if i<a.start_at:continue
   with (E/(str(i)+'.log')).open('w',encoding='utf-8') as f:
    p=subprocess.run([sys.executable,*cmd.split()],cwd=R,stdout=f,stderr=subprocess.STDOUT,timeout=3600)
   results.append({'command':cmd,'exit':p.returncode,'log_sha256':hashlib.sha256((E/(str(i)+'.log')).read_bytes()).hexdigest()})
   print(('PASS ' if p.returncode==0 else 'FAIL ')+cmd,flush=True)
   if p.returncode:raise RuntimeError(cmd)
  # Same vectors/seed and completion markers, only the HOST timeout is extended.
  sys.path.insert(0,str(R/'pl_rs485/tests'));import run_multirate
  def extended(args,cwd,env,log,timeout=180):
   with Path(log).open('w',encoding='utf-8') as f:p=subprocess.run(args,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=max(timeout,900))
   out=Path(log).read_text(encoding='utf-8');assert p.returncode==0,out[-2000:];return out
  run_multirate.run=extended;sys.argv=['run_multirate','--tag',tag,'--seed','20261013'];run_multirate.main()
  results.append({'command':'run_multirate original vectors','exit':0,'host_timeout_seconds':900});print('PASS multirate original vectors',flush=True)
 finally:
  restored=[]
  for p,b in saved.items():
   if p.read_bytes()!=b:p.write_bytes(b);restored.append(p.relative_to(R).as_posix())
  (E/'result.json').write_text(json.dumps({'passed':len(results)==len(commands)-a.start_at+1 and all(x['exit']==0 for x in results),'start_at':a.start_at,'tests':results,'sealed_evidence_preserved':True,'restored_preexisting_test_outputs':restored},indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
