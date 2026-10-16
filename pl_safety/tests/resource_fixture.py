"""Repeat independent pin oracle with actual full-top 500-cycle timing fixture."""
import hashlib,json,sys,traceback
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'pl_safety';sys.path.insert(0,str(R/'pl_motion'))
from sim_tools import Simulator
out=D/'evidence'/sys.argv[1];out.mkdir(exist_ok=False);sim=Simulator(out)
original=D/'tests/tb_safety.v';tb=original.read_text()
replacements={
 ' ? 0:1)':' ? 0:2)', 'cycle>30000':'cycle>300000',
 "{4{64'd3}}":"{4{64'd500}}", "{4{64'd2}}":"{4{64'd500}}", "{4{64'd4}}":"{4{64'd500}}",
 "{4{64'd7}}":"{4{64'd500}}", "{4{64'd5}}":"{4{64'd500}}", "{4{64'd10000000}}":"{4{64'd100000}}",
 '>=7,"DIR hold"':'>=500,"DIR hold"',
 '>=2 && cycle-dir_change[a]>=4 && cycle-enable_cycle[a]>=5':'>=500 && cycle-dir_change[a]>=500 && cycle-enable_cycle[a]>=500',
 '==3,"no truncated high pulse"':'==500,"no truncated high pulse"',
 '>=7+3,"EN closes':'>=500+500,"EN closes',
 '=-100;':'=-1000000;', 'rst_n=1;repeat(15)':'rst_n=1;repeat(650)'}
for old,new in replacements.items():assert old in tb,old;tb=tb.replace(old,new)
(out/'tb.v').write_text(tb)
sources=sorted((D/'rtl').glob('*.v'))+[R/'pl_motion/rtl'/n for n in ['motion_service.v','continuous_motion.v','motion_executor.v','motion_planner.v','motion_fifo.v','motion_stream_rx.v']]+[out/'tb.v']
result={'passed':False,'resource_fixture_only':True,'oracle_origin_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
try:
 for mode in [0,1]:
  exe=out/f'mode{mode}.vvp';log=sim.compile(sources,'tb_safety',exe,includes=[R/'pl_interface',D/'generated'],extra=[f'-Ptb_safety.MODE={mode}'])
  (out/f'compile{mode}.log').write_text(log);log=sim.simulate(exe,timeout=120);(out/f'mode{mode}.log').write_text(log);assert 'PASS safety' in log;print(log)
 result['passed']=True
except Exception:result['failure']=traceback.format_exc();raise
finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
