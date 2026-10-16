"""No retry/skip: independent self-checking safety modes, immutable run tags."""
import argparse,hashlib,json,sys,traceback
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'pl_safety'
sys.path.insert(0,str(R/'pl_motion'))
from sim_tools import Simulator
def main():
 p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--mode',type=int,action='append');p.add_argument('--offset',type=int,default=0);p.add_argument('--sweep',action='store_true');a=p.parse_args()
 assert a.tag.replace('_','').replace('-','').isalnum()
 out=D/'evidence'/a.tag;out.mkdir(exist_ok=False)
 sim=Simulator(out)
 (out/'tb_safety.v').write_bytes((D/'tests/tb_safety.v').read_bytes())
 sources=sorted((D/'rtl').glob('*.v'))+[R/'pl_motion/rtl'/n for n in ['motion_service.v','continuous_motion.v','motion_executor.v','motion_planner.v','motion_fifo.v','motion_stream_rx.v']]+[D/'tests/tb_safety.v']
 result={'passed':False,'cases':[],'source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'fixture_only':True,'synthetic_time_injection_modes':[16,17,18]}
 try:
  for m,o in [(m,o) for m in (a.mode if a.mode is not None else range(32)) for o in (range(24) if a.sweep else [a.offset])]:
   target=out/f'mode{m}_offset{o}.vvp'
   log=sim.compile(sources,'tb_safety',target,includes=[R/'pl_interface',D/'generated'],extra=[f'-Ptb_safety.MODE={m}',f'-Ptb_safety.OFFSET={o}'])
   (out/f'compile{m}_offset{o}.log').write_text(log,encoding='utf-8')
   log=sim.simulate(target,timeout=60);(out/f'mode{m}_offset{o}.log').write_text(log,encoding='utf-8')
   assert 'PASS safety' in log;result['cases'].append({'mode':m,'offset':o,'output':log});print(log,flush=True)
  result['passed']=True
 except Exception:
  result['failure']=traceback.format_exc();(out/'failure.log').write_text(result['failure'],encoding='utf-8');raise
 finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
