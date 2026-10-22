"""Unchanged independent FIFO scoreboard for the new private prepared FIFO."""
import argparse,json,re,shutil,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);a=p.parse_args()
 c=Path(a.candidate).resolve();out=E/a.tag;out.mkdir(exist_ok=False)
 tb=(R/'pl_motion/tests/tb_motion_fifo.v').read_text()
 original='motion_fifo #(.DEPTH(DEPTH)) dut(clk,rst_n,flush,in_valid,in_ready,in_data,out_valid,out_ready,out_data,level);'
 assert tb.count(original)==1
 tb=tb.replace(original,'wire storage_valid;\n    motion_plan_fifo #(.WIDTH(16),.DEPTH(DEPTH)) dut(clk,rst_n,flush,in_valid,in_ready,in_data,out_valid,out_ready,out_data,level,out_ready,storage_valid);')
 # Exercise immediate replacement data after consecutive invalidation edges;
 # all queue contents are still judged by the original independent scoreboard.
 extra='''
        for(i=0;i<256;i=i+1)begin
            flush=1;in_valid=1;out_ready=1;in_data=i;tick;@(negedge clk);
            if(i%3==0)begin tick;@(negedge clk);end
            flush=0;in_valid=1;out_ready=0;in_data=16'h8000+i;tick;@(negedge clk);
            in_valid=1;out_ready=1;in_data=16'hf000+i;tick;@(negedge clk);
            in_valid=0;tick;@(negedge clk);
        end
'''
 tb=tb.replace('        flush=0;in_valid=0;out_ready=1;repeat(DEPTH+2)',extra+'        flush=0;in_valid=0;out_ready=1;repeat(DEPTH+2)')
 (out/'tb.v').write_text(tb);result={'passed':False,'hashes_computed':False,'cases':[]}
 try:
  for depth in [2,3,7,8,64,65]:
   for phase,cmd in [('compile',[shutil.which('iverilog'),'-g2005','-s','tb_motion_fifo',f'-Ptb_motion_fifo.DEPTH={depth}','-o',str(out/f'd{depth}.vvp'),str(c/'motion_fifo.v'),str(out/'tb.v')]),('simulation',[shutil.which('vvp'),str(out/f'd{depth}.vvp')])]:
    with (out/f'd{depth}_{phase}.log').open('w') as log:proc=subprocess.run(cmd,cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    assert proc.returncode==0,(depth,phase)
   log=(out/f'd{depth}_simulation.log').read_text();assert 'PASS FIFO' in log;result['cases'].append({'depth':depth,'passed':True,'output':log});print(log.strip())
  result['passed']=True
 finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
