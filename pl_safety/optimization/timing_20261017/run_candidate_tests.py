"""Immutable-tag serial functional stages; Questa license is never parallelized."""
import argparse,json,subprocess,sys,hashlib
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[2]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--prefix',required=True);ap.add_argument('--stage',choices=['units','system'],required=True);a=ap.parse_args();o=E/(a.prefix+'_'+a.stage);o.mkdir(exist_ok=False);p=a.prefix
 units=[['pl_safety/tests/run.py','--tag',p+'_units1'],['pl_safety/tests/run.py','--tag',p+'_phases1','--sweep']+sum((['--mode',str(x)] for x in [2,3,11,12,13,14,15]),[]),['pl_safety/tests/overflow.py',p+'_overflow1'],['pl_safety/tests/resource_fixture.py',p+'_resource1']]
 system=[['pl_safety/tests/real_system.py','--tag',p+'_real1'],['pl_safety/tests/regressions.py','--tag',p+'_regress1']]
 commands=units if a.stage=='units' else system;results=[]
 for i,args in enumerate(commands):
  with (o/(str(i)+'.log')).open('w',encoding='utf-8') as f:r=subprocess.run([sys.executable]+args,cwd=R,stdout=f,stderr=subprocess.STDOUT)
  results.append({'command':args,'exit':r.returncode,'log_sha256':hashlib.sha256((o/(str(i)+'.log')).read_bytes()).hexdigest()})
  (o/'result.json').write_text(json.dumps({'passed':all(x['exit']==0 for x in results) and len(results)==len(commands),'tests':results},indent=2)+'\n');print(i,r.returncode,flush=True)
  if r.returncode:raise SystemExit(r.returncode)
if __name__=='__main__':main()
