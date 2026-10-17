"""Serial affected regressions; preserve all existing tracked JSON evidence."""
import argparse,hashlib,json,subprocess,sys,traceback
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'pl_safety'
COMMANDS=['pl_interface/generate.py --check','pl_safety/generate.py --check','pl_safety/generate_top.py --check',
 'pl_dma/generate_motion.py --check','pl_interface/tests/test_interface.py','pl_interface/tests/test_motion_v2.py','pl_interface/tests/check_verilog.py',
 'pl_motion/tests/run_sim.py','pl_motion/tests/run_four_axis.py','pl_motion/tests/run_continuous.py','golden_model/tests/test_regression.py',
 'pl_motion/tests/run_gp.py','pl_motion/tests/run_motion_integration.py','pl_dma/tests/test_contract.py','pl_dma/tests/run_components.py',
 'pl_dma/tests/run_sim.py','pl_dma/tests/run_sim.py --shared','pl_dma/tests/run_motion.py']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);a=ap.parse_args();out=D/'evidence'/a.tag;out.mkdir(exist_ok=False)
 paths=subprocess.check_output(['git','ls-files','pl_motion/*.json','pl_dma/*.json','pl_rs485/evidence/*.json'],cwd=R,text=True).splitlines()
 saved={R/n:(R/n).read_bytes() for n in paths}
 sources=[p for folder in ['pl_motion/rtl','pl_dma/rtl','pl_rs485/rtl'] for p in (R/folder).glob('*.v')]
 result={'passed':False,'tests':[],'source_sha256':{p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
 try:
  for i,c in enumerate(COMMANDS):
   p=subprocess.run([sys.executable,*c.split()],cwd=R,capture_output=True,text=True,timeout=900)
   log=out/f'{i:02}.log';log.write_text(p.stdout+p.stderr,encoding='utf-8')
   result['tests'].append({'command':c,'exit':p.returncode,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
   if p.returncode:raise RuntimeError('FAIL '+c+' '+(p.stdout+p.stderr)[-1500:])
   print('PASS '+c,flush=True)
  result['passed']=True
 except Exception:result['failure']=traceback.format_exc();raise
 finally:
  for p,data in saved.items():
   if p.read_bytes()!=data:p.write_bytes(data)
  result['old_evidence_restored']=True
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
