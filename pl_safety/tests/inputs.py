import hashlib,json,sys,traceback
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'pl_motion'))
from sim_tools import Simulator
b=R/'pl_safety/evidence'/sys.argv[1];b.mkdir(exist_ok=False);s=Simulator(b)
sources=[R/'pl_safety/rtl/safety_inputs.v',R/'pl_safety/tests/tb_inputs.v']
result={'passed':False,'source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
try:
 log=s.compile(sources,'tb_inputs',b/'test.vvp');(b/'compile.log').write_text(log)
 log=s.simulate(b/'test.vvp');(b/'run.log').write_text(log);assert 'PASS safety_inputs' in log;result['passed']=True;print(log)
except Exception:result['failure']=traceback.format_exc();raise
finally:(b/'result.json').write_text(json.dumps(result,indent=2)+'\n')
