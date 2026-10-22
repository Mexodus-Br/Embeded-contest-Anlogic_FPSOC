"""Original FIFO scoreboard with speculative storage; public controls unchanged."""
import argparse,json,re,shutil,subprocess,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--source',required=True);a=p.parse_args()
 assert re.fullmatch('[A-Za-z0-9_-]+',a.tag)
 out=HERE/a.tag;out.mkdir(exist_ok=False)
 original=(ROOT/'pl_motion/tests/tb_motion_fifo.v').read_text()
 result={'passed':False,'hashes_computed':False,'cases':[]}
 try:
  for spare in [0,1]:
   tb=original.replace('motion_fifo #(.DEPTH(DEPTH))',f'motion_fifo #(.DEPTH(DEPTH),.SPARE_SLOT({spare}),.SPECULATIVE_STORAGE(1))')
   assert tb!=original
   bench=out/f'tb{spare}.v';bench.write_text(tb)
   for depth in [2,3,7,8,64,65]:
    exe=out/f'fifo{spare}_{depth}.vvp';label=f'{spare}_{depth}'
    for phase,cmd in [('compile',[shutil.which('iverilog'),'-g2005','-s','tb_motion_fifo',f'-Ptb_motion_fifo.DEPTH={depth}','-o',str(exe),str(Path(a.source).resolve()),str(bench)]),('simulation',[shutil.which('vvp'),str(exe)])]:
     with (out/(label+'_'+phase+'.log')).open('w') as log:proc=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=60)
     assert proc.returncode==0,(spare,depth,phase)
    log=(out/(label+'_simulation.log')).read_text();assert 'PASS FIFO' in log
    result['cases'].append({'spare':spare,'depth':depth,'passed':True,'output':log.strip()})
  result['passed']=True;print('PASS speculative FIFO',len(result['cases']),'capacity/flush/backpressure matrices')
 except Exception:result['failure']=traceback.format_exc();raise
 finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
