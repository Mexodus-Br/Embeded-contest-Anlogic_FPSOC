"""Extend the independent six-window ownership bench to all seven windows."""
import hashlib,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'pl_safety';sys.path[:0]=[str(R/'pl_motion'),str(D)]
from sim_tools import Simulator
from generate_top import expand_bus
b=D/'evidence'/sys.argv[1];b.mkdir(exist_ok=False)
original=R/'bsp/telemetry/tb_router.v'
s=expand_bus(original.read_text()).replace('axi_lite_six_way','safety_axi_lite_seven_way')
s=s.replace('i<6','i<7').replace('j<6','j<7').replace('=63','=127').replace('six-way','seven-way')
s=s.replace("transaction(33'h080a00000,1)","transaction(33'h080b00000,1);transaction(33'h180a00000,1)")
# Testbench signal names have no m_ prefix for these reg declarations.
s=s.replace('[5:0] m_','[6:0] m_').replace('[11:0] m_bresp,m_rresp','[13:0] m_bresp,m_rresp')
tb=b/'tb_router.v';tb.write_text(s)
sim=Simulator(b);sources=[tb,D/'generated/safety_axi_lite_seven_way.v']
result={'passed':False,'original_tb_sha256':hashlib.sha256(original.read_bytes()).hexdigest()}
try:
 log=sim.compile(sources,'tb_router',b/'test.vvp',includes=[R/'pl_interface',D/'generated']);(b/'compile.log').write_text(log)
 log=sim.simulate(b/'test.vvp');(b/'run.log').write_text(log);assert 'PASS seven-way' in log;result['passed']=True;print(log)
finally:
 result['source_sha256']={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
 (b/'result.json').write_text(json.dumps(result,indent=2)+'\n')
