"""Affected baseline regressions; preserve original release metadata bytes."""
import argparse,concurrent.futures,hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'pl_motion/build/motion_regressions';OUT.mkdir(parents=True,exist_ok=True)
scripts=['pl_interface/generate.py --check','pl_interface/tests/test_interface.py','pl_interface/tests/check_verilog.py','pl_interface/tests/test_motion_v2.py',
 'pl_motion/tests/run_sim.py','pl_motion/tests/run_four_axis.py','pl_motion/tests/run_continuous.py','golden_model/tests/test_regression.py',
 'pl_dma/tests/run_components.py','pl_dma/tests/test_contract.py']
def execute(script):
 name=script.split()[0].replace('/','_');r=subprocess.run([sys.executable,*script.split()],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=600)
 p=OUT/(name+'.log');p.write_text(r.stdout,encoding='utf-8')
 if r.returncode:raise RuntimeError(script+'\n'+r.stdout[-3000:])
 return {'command':script,'status':'PASS','log':str(p.relative_to(ROOT)),'log_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--definitions-only',action='store_true');args=ap.parse_args()
 if args.definitions_only:
  path=ROOT/'pl_motion/MOTION_REGRESSION_RESULTS.json';result=json.loads(path.read_text());commands=scripts[:4]+['pl_dma/tests/test_contract.py']
  fresh=[execute(s) for s in commands];result['tests']=[x for x in result['tests'] if x['command'] not in commands]+fresh
  result['definition_sha256']=hashlib.sha256((ROOT/'pl_interface/generated/interface_defs.vh').read_bytes()).hexdigest();path.write_text(json.dumps(result,indent=2)+'\n')
  print('PASS final definitions and ABI checks');return
 results=[]
 preserved=[ROOT/'pl_motion/GP_SIM_RESULTS.json',ROOT/'pl_dma/SIM_RESULTS.json',ROOT/'pl_dma/SHARED_SIM_RESULTS.json',ROOT/'pl_dma/COMPONENT_RESULTS.json']
 saved={p:p.read_bytes() for p in preserved}
 try:
  with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
   for result in pool.map(execute,scripts):results.append(result);print('PASS '+result['command'],flush=True)
  for script in ['pl_motion/tests/run_gp.py','pl_dma/tests/run_sim.py','pl_dma/tests/run_sim.py --shared']:
   results.append(execute(script));print('PASS '+script,flush=True)
 finally:
  for p,data in saved.items():p.write_bytes(data)
 (ROOT/'pl_motion/MOTION_REGRESSION_RESULTS.json').write_text(json.dumps({'status':'PASS','tests':results,'definition_sha256':hashlib.sha256((ROOT/'pl_interface/generated/interface_defs.vh').read_bytes()).hexdigest()},indent=2)+'\n')
if __name__=='__main__':main()
