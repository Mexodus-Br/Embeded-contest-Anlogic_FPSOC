import hashlib,json,sys,traceback
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'pl_motion'))
from sim_tools import Simulator
b=R/'pl_safety/evidence'/sys.argv[1];b.mkdir(exist_ok=False);s=Simulator(b)
src=[R/'pl_motion/rtl/motion_executor.v',R/'pl_safety/tests/tb_home_overflow.v']
r={'passed':False,'source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in src}}
try:
 log=s.compile(src,'tb_home_overflow',b/'test.vvp');(b/'compile.log').write_text(log)
 log=s.simulate(b/'test.vvp');(b/'run.log').write_text(log);assert 'PASS home overflow' in log;r['passed']=True;print(log)
except Exception:r['failure']=traceback.format_exc();raise
finally:(b/'result.json').write_text(json.dumps(r,indent=2)+'\n')
