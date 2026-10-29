from pathlib import Path
import sys
H=Path(__file__).resolve().parent;R=H.parents[1];directory=sys.argv[2] if len(sys.argv)>2 else 'hardware';assert directory.replace('_','').isalnum();G=H/directory/'gp'
sys.path.insert(0,str(R/'pl_motion'))
from sim_tools import Simulator
out=H/'artifacts'/('timing-'+sys.argv[1]);out.mkdir(exist_ok=False)
sim=Simulator(out);exe=out/'test.vvp'
(out/'compile.log').write_text(sim.compile([G/'safety_inputs.v',G/'motion_executor.v',H.parent/'home_calibration_20261027/tb_physical_timing.v'],'tb_physical_timing',exe))
try:log=sim.simulate(exe,timeout=600)
except Exception as e:
 (out/'failure.log').write_text(str(e));raise
(out/'run.log').write_text(log)
assert 'PASS' in log
print(log)
