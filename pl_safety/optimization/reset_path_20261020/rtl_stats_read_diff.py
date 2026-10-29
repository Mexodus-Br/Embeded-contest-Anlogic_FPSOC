"""GP frozen-statistics validity versus the original fully-zeroed input oracle."""
import argparse,json,re,shutil,subprocess
from pathlib import Path
from equivalence import outputs
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);p.add_argument('--private-payload',action='store_true');a=p.parse_args()
 c=Path(a.candidate).resolve();out=E/a.tag;out.mkdir(exist_ok=False)
 old=(R/'pl_rs485/rtl/rs485_gp_regs.v').read_text();(out/'reference.v').write_text(old.replace('module rs485_gp_regs','module ref_rs485_gp_regs',1))
 tb=(R/'pl_rs485/tests/tb_gp_regs.v').read_text();start=tb.index(' rs485_gp_regs dut(');end=tb.index(');',start)+2
 inst=tb[start:end];clone=inst.replace('rs485_gp_regs dut(','ref_rs485_gp_regs golden(').replace('.observe_tasks(tasks)',".observe_tasks(stats_ready ? tasks:8000'd0)")
 decl=[];checks=[]
 for port,expr in re.findall(r'\.(\w+)\((\w+)\)',inst):
  if port not in outputs(old):continue
  decl.append('wire '+outputs(old)[port]+' ref_'+expr+';');clone=clone.replace(f'.{port}({expr})',f'.{port}(ref_{expr})')
  qualifier='dut.cfg_valid && ' if a.private_payload and port in ['cfg_period_us','cfg_mask'] else ''
  checks.append(f'if({qualifier}{expr} !== ref_{expr})$fatal(1,"GP frozen validity mismatch {port}");')
 newinst=inst.replace('rs485_gp_regs dut(','rs485_gp_regs #(.STATS_VALID_SUPPORT(1)) dut(.observe_stats_ready(stats_ready),')
 observe='\nreg stats_ready=1;integer epoch,word_number,miter_cycles=0;\n'+'\n'.join(decl)+'\n'+clone+'\nalways @(posedge clk)begin #1;miter_cycles=miter_cycles+1;\n'+'\n'.join(checks)+'\nend\n'
 tb=tb[:start]+newinst+observe+tb[end:]
 tb=re.sub(r'force dut\.(\w+)=(.*?);',lambda m:m[0]+f'force golden.{m[1]}={m[2]};',tb)
 tb=re.sub(r'release dut\.(\w+);',lambda m:m[0]+f'release golden.{m[1]};',tb)
 extra='''
 // Capture validity and data together; later changes must not rewrite it.
 for(epoch=0;epoch<8;epoch=epoch+1)begin
  @(negedge clk);stats_ready=epoch[0];
  tasks[7999:64]={248{32'hb5adf00d}};
  wr(`RG_REG_SNAP_REQ_ID,3+epoch,15,0);wr(`RG_REG_SNAP_SUBMIT,1,15,0);
  @(negedge clk);stats_ready=!stats_ready;
  for(word_number=0;word_number<`RG_SNAPSHOT_WORDS;word_number=word_number+1)
   rd(`RG_SNAPSHOT_BASE+word_number*4,0,v);
 end
 $display("PASS frozen statistics valid/data/reset oracle epochs=8 cycles=%0d",miter_cycles);
'''
 tb=tb.replace('  $display("PASS GP regs',extra+'  $display("PASS GP regs');(out/'test.v').write_text(tb)
 result={'passed':False,'hashes_computed':False}
 try:
  sources=[c/'rs485_gp_regs.v',R/'pl_rs485/rtl/record_fifo.v',out/'reference.v',out/'test.v']
  for phase,cmd in [('compile',[shutil.which('iverilog'),'-g2005','-I',str(R/'pl_rs485/generated'),'-I',str(R/'pl_rs485/tests'),'-s','tb_gp_regs','-o',str(out/'test.vvp'),*map(str,sources)]),('simulation',[shutil.which('vvp'),str(out/'test.vvp')])]:
   with (out/f'{phase}.log').open('w') as log:proc=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=120)
   assert proc.returncode==0,phase
  log=(out/'simulation.log').read_text();assert 'PASS frozen statistics' in log;result.update(passed=True,output=log);print(log)
 finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
