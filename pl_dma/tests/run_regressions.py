"""Run existing baseline tests; preserve prior GP board-cohort metadata."""
import concurrent.futures,hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'pl_dma/build/regressions';OUT.mkdir(parents=True,exist_ok=True)
scripts=['pl_interface/generate.py --check','pl_interface/tests/test_interface.py','pl_interface/tests/check_verilog.py',
         'pl_motion/tests/run_sim.py','pl_motion/tests/run_four_axis.py','pl_motion/tests/run_continuous.py',
         'golden_model/tests/test_regression.py']
def execute(script):
 name=script.split()[0].replace('/','_');r=subprocess.run([sys.executable,*script.split()],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=600)
 (OUT/(name+'.log')).write_text(r.stdout,encoding='utf-8')
 if r.returncode:raise RuntimeError(script+'\n'+r.stdout[-2000:])
 return {'command':script,'status':'PASS','log':str(OUT/(name+'.log')),'log_sha256':hashlib.sha256(r.stdout.encode()).hexdigest()}
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for result in pool.map(execute,scripts):results.append(result);print('PASS '+result['command'],flush=True)
gp=ROOT/'pl_motion/GP_SIM_RESULTS.json';saved=gp.read_bytes()
try:results.append(execute('pl_motion/tests/run_gp.py'))
finally:gp.write_bytes(saved)
(ROOT/'pl_dma/REGRESSION_RESULTS.json').write_text(json.dumps({'status':'PASS','tests':results},indent=2)+'\n')
print('PASS original GP regressions; original GP_SIM_RESULTS.json bytes preserved',flush=True)
