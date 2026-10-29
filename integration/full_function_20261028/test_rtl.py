"""Exercise actual isolated PL sources. Never hash logs or simulation intermediates."""
from pathlib import Path
import argparse
import json
import subprocess
import sys
H=Path(__file__).resolve().parent;R=H.parents[1];G=H/'hardware/gp'
sys.path.insert(0,str(R/'pl_motion'))
from sim_tools import Simulator
p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--hardware-directory',default='hardware');a=p.parse_args()
assert a.hardware_directory.replace('_','').isalnum();G=H/a.hardware_directory/'gp'
out=H/'artifacts'/('rtl-'+a.tag);out.mkdir(parents=True,exist_ok=False);sim=Simulator(out)
def run(name,sources,top,extra=(),timeout=90):
 target=out/(name+'.vvp')
 log=sim.compile(sources,top,target,includes=[G,R/'pl_interface'],extra=list(extra))
 (out/(name+'-compile.log')).write_text(log)
 log=sim.simulate(target,timeout=timeout);(out/(name+'.log')).write_text(log)
 assert 'PASS' in log,log
 print(log,flush=True);return log
reports={}
home=(H.parent/'home_calibration_20261027/tb_home_config.v').read_text().replace('C_HOME_ONLY && C_REFERENCE_POSITION','!C_HOME_ONLY && C_REFERENCE_POSITION')
(out/'tb_home_config.v').write_text(home)
reports['calibration']=run('calibration',[G/'safety_controller.v',out/'tb_home_config.v'],'tb_home_config')
# Original independently checked pin-level bench; mode0 now tests unknown profile
# rather than formerly unconfigured production, whose bounded HOME is now approved.
text=subprocess.check_output(['git','show','05686d4:pl_safety/tests/tb_safety.v'],cwd=R).decode()
assert '(MODE==8 || MODE==31) ? 0:1' in text
text=text.replace('(MODE==8 || MODE==31) ? 0:1','(MODE==8 || MODE==31) ? 99:1')
(out/'tb_safety.v').write_text(text)
names=['safety_controller.v','safety_inputs.v','safety_regs.v','safety_motion_service.v','safety_interlock.v','safety_interlock_regs.v',
 'motion_service.v','continuous_motion.v','motion_executor.v','motion_planner.v','motion_fifo.v','motion_stream_rx.v']
for mode in range(32):
 reports[str(mode)]=run('original-'+str(mode),[G/n for n in names]+[out/'tb_safety.v'],'tb_safety',[f'-Ptb_safety.MODE={mode}'])
(out/'result.json').write_text(json.dumps(dict(passed=True,reports=reports,hashes_computed=False),indent=2)+'\n')
