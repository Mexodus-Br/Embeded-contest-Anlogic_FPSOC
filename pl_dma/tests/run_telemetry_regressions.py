"""Affected baselines; preserve their original release JSON, keep new logs."""
import argparse,concurrent.futures,hashlib,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);a=ap.parse_args();e=R/'pl_dma/reports'/('telemetry_regression_'+a.tag);e.mkdir(exist_ok=False)
scripts=['pl_interface/generate.py --check','pl_interface/tests/test_interface.py','pl_interface/tests/check_verilog.py','pl_interface/tests/test_motion_v2.py',
 'pl_motion/tests/run_sim.py','pl_motion/tests/run_four_axis.py','pl_motion/tests/run_continuous.py',
 'pl_motion/tests/run_gp.py','pl_motion/tests/run_motion_integration.py','golden_model/tests/test_regression.py',
 'pl_dma/tests/test_contract.py','pl_dma/tests/run_components.py','pl_dma/tests/run_sim.py','pl_dma/tests/run_sim.py --shared','pl_dma/tests/run_motion.py']
saved={p:p.read_bytes() for d in ['pl_dma','pl_motion'] for p in (R/d).glob('*RESULTS*.json')}
def execute(command):
 name=command.replace('/','_').replace(' ','_').replace('--','');p=subprocess.run([sys.executable,*command.split()],cwd=R,capture_output=True,text=True,timeout=900)
 out=p.stdout+p.stderr;(e/(name+'.log')).write_text('EXIT '+str(p.returncode)+'\n'+out,encoding='utf-8')
 if p.returncode:raise RuntimeError('regression failed '+command+' '+out[-1800:])
 return {'command':command,'status':'PASS','log_sha256':hashlib.sha256((e/(name+'.log')).read_bytes()).hexdigest()}
results=[]
try:
 # Shared build paths are not run concurrently with one another.
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  for x in pool.map(execute,scripts[:7]+[scripts[9],scripts[10]]):results.append(x);print('PASS '+x['command'],flush=True)
 for command in scripts[7:9]+scripts[11:]:results.append(execute(command));print('PASS '+command,flush=True)
finally:
 for p,data in saved.items():p.write_bytes(data)
 (e/'result.json').write_text(json.dumps({'passed':len(results)==len(scripts),'tests':results,'baseline_metadata_restored':True},indent=2)+'\n')
