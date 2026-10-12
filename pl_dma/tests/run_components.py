"""Independent elastic FIFO self-check; no DMA behavioral substitute."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'pl_motion'))
from sim_tools import Simulator
sim=Simulator(ROOT/'build/components');results=[]
for depth in [2,3,16]:
 image=ROOT/f'build/components/fifo{depth}.vvp'
 sim.compile([ROOT/'rtl/axis_loop_fifo.v',ROOT/'tb/tb_fifo.v'],'tb_fifo',image,extra=[f'-Ptb_fifo.DEPTH={depth}'])
 log=sim.simulate(image)
 if 'PASS fifo' not in log:raise RuntimeError(log)
 results.append(log.strip());print(log.strip())
(ROOT/'COMPONENT_RESULTS.json').write_text(json.dumps({'status':'PASS','results':results,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'rtl/axis_loop_fifo.v',ROOT/'tb/tb_fifo.v']}},indent=2)+'\n')
