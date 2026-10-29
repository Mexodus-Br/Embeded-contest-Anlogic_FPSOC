"""Independent source-predictor preparation; production files stay untouched.

Retain original generation/revision update branches. Share only their existing
+1 arithmetic, expose complete next values and check them against actual source
registers after every edge, including collector asynchronous local reset.
"""
import importlib.util,json,re,shutil,subprocess,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent/'counter_probe_r1'

def replace(source,old,new,count=1):
 assert source.count(old)==count,old
 return source.replace(old,new)

def main():
 OUT.mkdir(exist_ok=False)
 result={'passed':False,'hashes_computed':False,'scope':'source predictor prototypes only; production RTL unchanged','tests':[]}
 try:
  gp=(ROOT/'pl_rs485/rtl/rs485_gp_regs.v').read_text()
  gp=replace(gp,'interlock_config_change,interlock_stop_commit);',
   'interlock_config_change,interlock_stop_commit,output wire [31:0] next_generation,output wire reset_commit);')
  gp=replace(gp,'reg aw_snapshot,aw_run,w_run_clear;', 'reg aw_snapshot,aw_run,w_run_clear,aw_reset,w_reset;')
  gp=replace(gp,"generation+1'b1",'generation_increment',3)
  gp=replace(gp,' wire [31:0] effective_run_write=', ''' wire [31:0] generation_increment=generation+1'b1;
 assign reset_commit=write_fire && aw_reset && w_reset &&
   (!INTERLOCK_SUPPORT || interlock_idle_off) && !run && !busy && !config_pending && !cfg_valid &&
   cfg_ready && reset_count==0 && !cfg_applied && !cfg_rejected && generation!=32'hffffffff;
 assign next_generation=!rst_n ? 32'd0:reset_commit ? generation_increment:generation;
 wire [31:0] effective_run_write=''')
  gp=replace(gp,'aw_snapshot<=0;aw_run<=0;w_run_clear<=0;',
   'aw_snapshot<=0;aw_run<=0;w_run_clear<=0;aw_reset<=0;w_reset<=0;')
  gp=replace(gp,'aw_run<=s_awaddr==BASE+`RG_REG_RUN;',
   'aw_run<=s_awaddr==BASE+`RG_REG_RUN;aw_reset<=s_awaddr==BASE+`RG_REG_LOCAL_RESET;')
  gp=replace(gp,'wh<=1;wd<=s_wdata;ws<=s_wstrb;',
   "wh<=1;wd<=s_wdata;ws<=s_wstrb;w_reset<=s_wstrb==4'hf && s_wdata==1;")
  (OUT/'rs485_gp_regs.v').write_text(gp)
  multi=(ROOT/'pl_rs485/rtl/rs485_multirate.v').read_text()
  multi=replace(multi,'output wire [7999:0] observe_tasks,output wire [1279:0] observe_nodes);',
   'output wire [7999:0] observe_tasks,output wire [1279:0] observe_nodes,output wire [31:0] next_revision);')
  multi=replace(multi,' wire [255:0] push_data;', ''' wire [255:0] push_data;
 wire [31:0] revision_increment=cfg_revision+1'b1;
 assign next_revision=!rst_n ? 32'd0:
   (state==CFG_WAIT && !engine_active && cfg_revision!=32'hffffffff) ? revision_increment:cfg_revision;''')
  multi=replace(multi,"cfg_revision<=cfg_revision+1'b1;",'cfg_revision<=revision_increment;')
  (OUT/'rs485_multirate.v').write_text(multi)
  bridge=(ROOT/'pl_rs485/rtl/rs485_gp_bridge.v').read_text()
  bridge=replace(bridge,'interlock_config_change,interlock_busy,interlock_stop_commit);',
   'interlock_config_change,interlock_busy,interlock_stop_commit,output wire [31:0] next_generation,next_revision);')
  bridge=replace(bridge,'wire run,collector_rst_n,cv,cr,ca,ce,busy,rv,rr,push;',
   'wire run,collector_rst_n,cv,cr,ca,ce,busy,rv,rr,push;\nwire reset_commit;wire [31:0] next_revision_raw;')
  bridge=replace(bridge,'assign interlock_busy=busy;',
   "assign interlock_busy=busy;\nassign next_revision=(!collector_rst_n || reset_commit) ? 32'd0:next_revision_raw;")
  assert bridge.count('.cfg_revision(revision),.cfg_apply_sequence(sequence)')==2
  bridge=bridge.replace('.cfg_revision(revision),.cfg_apply_sequence(sequence)',
   '.cfg_revision(revision),.next_revision(next_revision_raw),.cfg_apply_sequence(sequence)',1)
  bridge=replace(bridge,'.interlock_stop_commit(interlock_stop_commit),',
   '.interlock_stop_commit(interlock_stop_commit),.next_generation(next_generation),.reset_commit(reset_commit),')
  (OUT/'rs485_gp_bridge.v').write_text(bridge)
  e2e=(ROOT/'pl_rs485/tests/tb_gp_e2e.v').read_text()
  observer=r'''
integer predictions_checked=0;reg [31:0] predicted_generation,predicted_revision;
always @(posedge clk)if(rst_n)begin
 predicted_generation=dut.next_generation;predicted_revision=dut.next_revision;
 #1;if(rst_n)begin
  predictions_checked=predictions_checked+1;
  if(dut.completed_generation!==predicted_generation || dut.revision!==predicted_revision)
   $fatal(1,"source next-value mismatch G expected=%h actual=%h R expected=%h actual=%h",
    predicted_generation,dut.completed_generation,predicted_revision,dut.revision);
 end
end
'''
  e2e=replace(e2e,'endmodule',observer+'\nendmodule')
  e2e=e2e.replace('$finish;', '$display("COUNTER_PREDICTOR_CHECKS %0d",predictions_checked);$finish;')
  (OUT/'tb_e2e.v').write_text(e2e)
  spec=importlib.util.spec_from_file_location('gp_guard',ROOT/'pl_safety/tests/interlock_rs485_fixture.py')
  fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
  guard=fixture.render()
  observer=r'''
integer predictions_checked=0;reg [31:0] predicted_generation;
always @(posedge clk)if(rst_n)begin
 predicted_generation=dut.next_generation;
 #1;if(rst_n)begin
  predictions_checked=predictions_checked+1;
  if(dut.generation!==predicted_generation)$fatal(1,"guarded GP generation prediction differs from real register");
 end
end
'''
  guard=replace(guard,'endmodule',observer+'\nendmodule')
  guard=guard.replace('$finish;', '$display("COUNTER_PREDICTOR_CHECKS %0d",predictions_checked);$finish;')
  (OUT/'tb_guard.v').write_text(guard)
  sources=[OUT/p.name if (OUT/p.name).exists() else p for p in (ROOT/'pl_rs485/rtl').glob('*.v')]
  for label,top,bench in [('e2e','tb_gp_e2e','tb_e2e.v'),('guard','tb_interlock_rs485','tb_guard.v')]:
   commands=[[shutil.which('iverilog'),'-g2005',
    *sum((['-I',str(ROOT/x)] for x in ['pl_interface','pl_rs485/generated','pl_rs485/tests']),[]),
    '-s',top,'-o',str(OUT/(label+'.vvp')),*map(str,sources),str(OUT/bench)],
    [shutil.which('vvp'),str(OUT/(label+'.vvp'))]]
   record={'name':label,'passed':False};result['tests'].append(record)
   for stage,command in zip(['compile','simulation'],commands):
    with (OUT/(label+'_'+stage+'.log')).open('w') as log:
     p=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    assert p.returncode==0,(label,stage)
   text=(OUT/(label+'_simulation.log')).read_text();assert 'PASS' in text
   count=int(re.search(r'COUNTER_PREDICTOR_CHECKS (\d+)',text)[1]);assert count>0
   record.update(passed=True,actual_source_edges_checked=count)
   print(label,count,text.strip().splitlines()[-3:])
  result['passed']=True
 except Exception:
  result['failure']=traceback.format_exc();raise
 finally:(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
