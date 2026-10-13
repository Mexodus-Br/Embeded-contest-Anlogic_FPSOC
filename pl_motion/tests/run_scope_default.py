"""Verify zero default parameters without taking the real-IP simulator license."""
import json,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'pl_motion'))
from sim_tools import Simulator
def main():
 b=ROOT/'pl_motion/build/scope_default';sim=Simulator(b)
 sources=[ROOT/'pl_motion/rtl'/n for n in ['motion_fifo.v','motion_planner.v','motion_executor.v','continuous_motion.v','motion_stream_rx.v','motion_service.v']]
 tb=ROOT/'pl_motion/tests/tb_scope_default.v';o=b/'test.vvp'
 compile_log=sim.compile(sources+[tb],'tb_scope_default',o,includes=[ROOT/'pl_interface'])
 (b/'compile.log').write_text(compile_log,encoding='utf-8')
 log=sim.simulate(o);(b/'simulation.log').write_text(log,encoding='utf-8')
 assert 'PASS scope_default_zero' in log
 (ROOT/'pl_motion/scope_test/DEFAULT_RESULTS.json').write_text(json.dumps({'status':'PASS','result':log.strip(),'bench_sha256':hashlib.sha256(tb.read_bytes()).hexdigest()},indent=2)+'\n')
 print(log)
if __name__=='__main__':main()
