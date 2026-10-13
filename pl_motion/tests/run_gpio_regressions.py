"""Run affected regressions, retaining the original sealed evidence bytes."""
import argparse,concurrent.futures,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'pl_motion/build/gpio_regressions'
COMMANDS=['pl_interface/generate.py --check','pl_dma/generate_motion.py --check','pl_motion/generate_scope.py --check',
 'pl_interface/tests/test_interface.py','pl_interface/tests/check_verilog.py','pl_interface/tests/test_motion_v2.py',
 'pl_motion/tests/run_sim.py','pl_motion/tests/run_four_axis.py','pl_motion/tests/run_continuous.py',
 'golden_model/tests/test_regression.py','pl_dma/tests/run_components.py','pl_dma/tests/test_contract.py']
def run(cmd):
 p=OUT/(cmd.split()[0].replace('/','_')+('.shared' if '--shared' in cmd else '')+'.log')
 r=subprocess.run([sys.executable,*cmd.split()],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=900)
 p.write_text(r.stdout,encoding='utf-8')
 if r.returncode:raise RuntimeError(cmd+' failed; '+str(p)+'\n'+r.stdout[-2500:])
 print('PASS '+cmd,flush=True)
 return {'command':cmd,'status':'PASS','log':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--integrated-only',action='store_true');a=ap.parse_args()
 OUT.mkdir(parents=True,exist_ok=True)
 tracked=subprocess.check_output(['git','ls-files','pl_motion/*.json','pl_dma/*.json'],cwd=ROOT,text=True).splitlines()
 saved={ROOT/n:(ROOT/n).read_bytes() for n in tracked}
 results=[]
 try:
  if a.integrated_only:
   results=json.loads((OUT/'base-results.json').read_text())
   for row in results:assert hashlib.sha256((ROOT/row['log']).read_bytes()).hexdigest()==row['sha256']
  else:
   with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(run,COMMANDS))
   (OUT/'base-results.json').write_text(json.dumps(results,indent=2)+'\n')
  for cmd in ['pl_motion/tests/run_gp.py','pl_motion/tests/run_motion_integration.py','pl_dma/tests/run_sim.py','pl_dma/tests/run_sim.py --shared','pl_dma/tests/run_motion.py']:results.append(run(cmd))
 finally:
  for p,b in saved.items():
   if p.read_bytes()!=b:p.write_bytes(b)
 (ROOT/'pl_motion/scope_test/REGRESSION_RESULTS.json').write_text(json.dumps({'status':'PASS','tests':results,'original_tracked_json_evidence_preserved':True},indent=2)+'\n')
if __name__=='__main__':main()
