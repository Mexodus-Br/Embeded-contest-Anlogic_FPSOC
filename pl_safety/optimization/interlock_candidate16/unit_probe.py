"""Current-context miter and actual next-control source checks; no hashes."""
import json,shutil,subprocess,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
SRC=HERE/'sources_r1';OUT=HERE/'unit_r1'
def change(s,a,b):
 assert s.count(a)==1,a
 return s.replace(a,b)
def run(name,top,files):
 commands=[[shutil.which('iverilog'),'-g2005',*sum((['-I',str(ROOT/p)] for p in
 ['pl_interface','pl_safety/generated','pl_rs485/generated','pl_rs485/tests']),[]),
 '-s',top,'-o',str(OUT/(name+'.vvp')),*map(str,files)], [shutil.which('vvp'),str(OUT/(name+'.vvp'))]]
 for stage,args in zip(['compile','simulation'],commands):
  with (OUT/(name+'_'+stage+'.log')).open('w') as log:p=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=240)
  assert p.returncode==0,(name,stage)
 text=(OUT/(name+'_simulation.log')).read_text();assert 'PASS' in text
 print(text.strip().splitlines()[-3:],flush=True)
 return {'passed':True,'output':text.strip()}
def main():
 OUT.mkdir(exist_ok=False);result={'passed':False,'hashes_computed':False,'production_modified':False}
 try:
  old=ROOT/'pl_safety/optimization/interlock_candidate15/unit_r2'
  shutil.copyfile(old/'reference.v',OUT/'reference.v')
  core=(SRC/'pl_safety/rtl/safety_interlock.v').read_text().replace('module safety_interlock #','module safety_interlock16 #')
  (OUT/'core.v').write_text(core)
  tb=(old/'tb_core.v').read_text()
  tb=change(tb,'reg [31:0] generation=', 'reg next_collector_reset=0,next_config_change=0,next_config_apply=0;\nreg [31:0] generation=')
  tb=change(tb,'if(!rst_n)begin generation<=0;revision<=0;end', 'if(!rst_n)begin generation<=0;revision<=0;collector_reset<=0;config_change<=0;config_apply<=0;end')
  tb=change(tb,'else begin generation<=next_generation;revision<=next_revision;end', 'else begin generation<=next_generation;revision<=next_revision;collector_reset<=next_collector_reset;config_change<=next_config_change;config_apply<=next_config_apply;end')
  tb=change(tb,'collector_reset=i%127==0;config_change=i%61==0;config_apply=i%83==0;', 'next_collector_reset=i%127==0;next_config_change=i%61==0;next_config_apply=i%83==0;')
  tb=change(tb,'safety_interlock15 #(.LOOKAHEAD_EPOCH(1),.FEEDBACK_PREDECODE(1)) cached(',
   'safety_interlock16 #(.LOOKAHEAD_EPOCH(1),.FEEDBACK_PREDECODE(1),.LOOKAHEAD_CONTEXT(1)) cached(.next_collector_reset(next_collector_reset),.next_config_change(next_config_change),.next_config_apply(next_config_apply),')
  tb=change(tb,'task compare;begin', '''task compare;begin
 if(reference.monitoring!==cached.monitoring)$fatal(1,"current monitoring context mismatch");
 if(cached.off_context_q!==((generation==cached.round_generation) &&
   (revision==cached.round_revision) && !collector_reset))$fatal(1,"off context not current");
 if(cached.active_context_q!==((generation==cached.round_generation) &&
   (revision==cached.round_revision) && reference.previous_run && !collector_reset &&
   !config_change && !config_apply))$fatal(1,"active context not current");''')
  (OUT/'tb_core.v').write_text(tb)
  result['core']=run('core','tb_epoch_cache',[OUT/'reference.v',OUT/'core.v',ROOT/'pl_rs485/rtl/rs485_light_parse.v',OUT/'tb_core.v'])
  tb=(ROOT/'pl_rs485/tests/tb_gp_e2e.v').read_text()
  observer=r'''
integer prediction_checks=0;reg [31:0] next_g,next_r;reg next_reset,next_change;
always @(posedge clk)if(rst_n)begin
 next_g=dut.next_generation;next_r=dut.next_revision;
 next_reset=dut.next_reset;next_change=dut.next_config_change;
 #1;if(rst_n)begin
  prediction_checks=prediction_checks+1;
  if({dut.completed_generation,dut.revision,dut.interlock_reset,dut.interlock_config_change}!==
     {next_g,next_r,next_reset,next_change})$fatal(1,"actual source control next-value mismatch");
 end
end
'''
  tb=change(tb,'endmodule',observer+'\nendmodule').replace('$finish;','$display("PREDICTION_CHECKS %0d",prediction_checks);$finish;')
  (OUT/'tb_sources.v').write_text(tb)
  files=[SRC/'pl_rs485/rtl'/p.name if (SRC/'pl_rs485/rtl'/p.name).exists() else p for p in (ROOT/'pl_rs485/rtl').glob('*.v')]
  result['sources']=run('sources','tb_gp_e2e',files+[OUT/'tb_sources.v'])
  tb=(ROOT/'pl_safety/tests/tb_interlock_regs.v').read_text()
  observer=r'''
integer prediction_checks=0;reg next_apply;
always @(posedge clk)if(rst_n)begin
 next_apply=ext.next_config_apply;
 #1;if(rst_n)begin
  prediction_checks=prediction_checks+1;
  if(apply!==next_apply)$fatal(1,"configuration apply next-value mismatch");
 end
end
'''
  tb=change(tb,'endmodule',observer+'\nendmodule').replace('$finish;','$display("PREDICTION_CHECKS %0d",prediction_checks);$finish;')
  (OUT/'tb_regs.v').write_text(tb)
  result['registers']=run('regs','tb_interlock_regs',[ROOT/'pl_safety/rtl/safety_regs.v',SRC/'pl_safety/rtl/safety_interlock_regs.v',OUT/'tb_regs.v'])
  result['passed']=True
 except Exception:
  result['failure']=traceback.format_exc();raise
 finally:(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
