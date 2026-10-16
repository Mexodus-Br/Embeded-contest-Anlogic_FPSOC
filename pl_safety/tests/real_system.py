"""Real protected GP/DMA/HP models, seven-window safety candidate self-check."""
import argparse,hashlib,json,re,shutil,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'pl_safety'
sys.path[:0]=[str(R/'pl_dma'),str(R/'pl_dma/tests')]
from prepare_ip import prepare
from generate_telemetry import portnames
from run_telemetry import run
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);a=ap.parse_args();b=D/'build'/a.tag;b.mkdir(exist_ok=False)
 e=D/'evidence'/a.tag;e.mkdir(exist_ok=False)
 ip=prepare();top=(D/'generated/safety_rs485_gp_ps_top.v').read_text();ports=portnames(top.split(')(\n',1)[1].split(');',1)[0])
 decl=[];bind=[]
 for n,(d,w) in ports.items():
  wire=d=='output' or n in ['hp_arready','hp_awready','hp_wready','hp_bresp','hp_rresp'] or n.startswith('hp1_') and n not in ['hp1_bid','hp1_bvalid']
  decl.append(('wire' if wire else 'reg')+' '+(f'[{w-1}:0] ' if w>1 else '')+n+';');bind.append(f'.{n}({n})')
 params=','.join(f'.{n}({{4{{64\'d{v}}}}})' for n,v in [('STEP_HIGH_CYCLES',3),('STEP_LOW_CYCLES',2),('DIR_SETUP_CYCLES',4),('DIR_HOLD_CYCLES',7),('EN_SETUP_CYCLES',5),('EN_DISABLE_CYCLES',3),('MAX_STEP_HZ',10000000)])
 (b/'dut_bindings.vh').write_text('\n'.join(decl)+'\nsafety_rs485_gp_ps_top #(.CONFIG_PROFILE(1),'+params+') dut('+','.join(bind)+');\n')
 tb=(R/'pl_dma/tb/tb_dma.v').read_text().split('task transfer;',1)[0].replace('module tb_dma;','module tb_safety_real;\n`include "generated/interface_defs.vh"\n`include "safety_defs.vh"')
 tb=re.sub(r'\bs_','gp_',tb).replace('dut.d_','dut.core.fabric.dma_core.d_').replace('dut.bridge_','dut.core.fabric.dma_core.bridge_')
 tb=tb.replace('`include "dut_bindings.vh"','`include "dut_bindings.vh"\nwire [31:0] loop_occupancy=dut.core.fabric.dma_core.loop_occupancy;')
 helpers=(R/'pl_dma/tb/motion_dma_scenarios.vh').read_text();helpers=helpers[helpers.index('task motion_command;'):helpers.index('reg [63:0] motion_time;')]
 helpers=helpers.replace('r[176+:16]=15','r[176+:16]=7').replace('r[448+:64]=-target','r[448+:64]=0')
 tb+='''
`define SAFETY dut.core.fabric.dma_core.motion
`define MOTION dut.core.fabric.dma_core.motion.motion
localparam [32:0] MB={1'b0,`PLI_MOTION_GP_MOTION_V1_BASE},SB={1'b0,`SAF_BASE};
integer motion_txn=0,motion_gen=0,motion_session=0;
'''+helpers+(R/'pl_dma/tb/telemetry_hp1_bfm.vh').read_text().split('always @(negedge clk_100m) if(control_rst_n) begin')[0]+'''
integer pc[0:2],axis;reg [3:0] prev_step=0,prev_state=0;
always @(negedge clk_100m)if(control_rst_n)begin
 if(`SAFETY.state!=prev_state)for(axis=0;axis<3;axis=axis+1)pc[axis]=0;
 for(axis=0;axis<3;axis=axis+1)begin
  if(motion_step[axis] && !prev_step[axis])pc[axis]=pc[axis]+1;
  if(`SAFETY.state==`SAF_STATES_SEARCH && pc[axis]>=3+axis*3)safety_limit_n[axis]=0;
  if(`SAFETY.state==`SAF_STATES_PULL && pc[axis]>=2)safety_limit_n[axis]=1;
 end
 prev_state=`SAFETY.state;prev_step=motion_step;
 check(`MOTION.timestamp===dut.core.fabric.registers.timestamp,"common 1MHz epoch remains aligned");
 check(hp1_writes==0,"safety operation never initiates telemetry DMA");
end
initial begin
 clk_100m=0;arst_n=0;safety_limit_n=7;safety_estop_n=1;rs485_rx=1;
 gp_awid=0;gp_arid=0;gp_awlen=0;gp_arlen=0;gp_awsize=2;gp_arsize=2;gp_awburst=1;gp_arburst=1;
 gp_awlock=0;gp_arlock=0;gp_awcache=0;gp_arcache=0;gp_awprot=0;gp_arprot=0;gp_wlast=1;
 gp_awaddr=0;gp_awvalid=0;gp_wdata=0;gp_wstrb=0;gp_wvalid=0;gp_bready=0;gp_araddr=0;gp_arvalid=0;gp_rready=0;
 hp_rdata=0;hp_rvalid=0;hp_rlast=0;hp_rid=0;hp_bvalid=0;hp_bid=0;hp1_bvalid=0;hp1_bid=0;
 for(axis=0;axis<3;axis=axis+1)pc[axis]=0;
 reset_design;repeat(20)@(negedge clk_100m);
 read_reg(SB+4,0,status_value);check(status_value==`SAF_PROFILE,"seventh GP profile through real converter");
 read_reg(SB+33'h100000000,3,status_value);read_reg(SB+4096,3,status_value);
 read_reg(33'h080400000,0,status_value);check(status_value==1,"old GP probe remains selected");
 write_reg(SB+`SAF_REGISTERS_OPCODE,`SAF_COMMANDS_HOME_START,15,0,1);
 write_reg(SB+`SAF_REGISTERS_TXN,1,15,0,2);write_reg(SB+`SAF_REGISTERS_SUBMIT,1,15,0,0);
 while(`SAFETY.state!=`SAF_STATES_READY)@(negedge clk_100m);
 check(`MOTION.position_valid[2:0]==7 && `MOTION.position[63:0]==92 && $signed(`MOTION.position[127:64])==-191 && `MOTION.position[191:128]==290,"real GP HOME final coordinate");
 motion_recover;motion_open;fill_motion(2,motion_session,0,1,100,100);issue_motion(2);await_dma;
 while(!`MOTION.start_ready)@(negedge clk_100m);motion_command(`PLI_CMD_START,0);
 check(`MOTION.running,"real MM2S trajectory executes after HOME");
 write_reg(SB+`SAF_REGISTERS_IRQ_MASK,1,15,0,0);
 @(negedge clk_100m);#2;safety_limit_n[0]=0;repeat(20)@(negedge clk_100m);
 check(`MOTION.position_valid[2:0]==0 && !`MOTION.session_valid && `MOTION.buffered_points==0 && `MOTION.partial_empty,"limit cancels real DMA transport and position validity");
 check(f2p_irq[7],"independent safety level IRQ7");
 write_reg(SB+`SAF_REGISTERS_IRQ_PENDING,1,15,0,0);check(f2p_irq[7],"persistent source dominates W1C");
 write_reg(SB+`SAF_REGISTERS_SNAP_REQ,1,15,0,0);
 read_reg(SB+`SAF_SNAPSHOT_BASE+`SAF_SNAPSHOT_CAUSES*4,0,status_value);check(status_value[0],"snapshot reason survives endpoint/backpressure");
 safety_limit_n=7;repeat(10)@(negedge clk_100m);
 write_reg(SB+`SAF_REGISTERS_OPCODE,`SAF_COMMANDS_CLEAR_FAULT,15,0,0);write_reg(SB+`SAF_REGISTERS_TXN,2,15,0,0);write_reg(SB+`SAF_REGISTERS_SUBMIT,1,15,0,0);
 repeat(10)@(negedge clk_100m);check(`SAFETY.state==`SAF_STATES_NEED && `MOTION.position_valid[2:0]==0 && !`MOTION.session_valid,"clear never restores HOME or old session");
 check(read_beats==18 && hp1_writes==0,"real HP0 two MOT2 records, no HP1 writes");
 $display("PASS safety_real_system checks=%0d hp0_read=%0d hp1_write=%0d",checks,read_beats,hp1_writes);$finish;
end
endmodule
'''
 (b/'tb.v').write_text(tb)
 vlog=shutil.which('vlog');vsim=shutil.which('vsim');result={'passed':False,'real_ip':ip}
 rtl=[p for folder in ['pl_dma/rtl','pl_motion/rtl','pl_rs485/rtl','pl_safety/rtl','pl_safety/generated'] for p in (R/folder).glob('*.v')]
 try:
  run([Path(vlog).parent/'vlib.exe','work'],b,'library')
  run([vlog,'-work','work',*['+incdir+'+str(p) for p in [R/'pl_interface',R/'pl_rs485/generated',R/'pl_dma/build/ip',D/'generated',b]],*[Path(x['staged']) for x in ip['libraries'].values()],*rtl,b/'tb.v'],b,'compile')
  output=run([vsim,'-batch','work.tb_safety_real','-do','onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0'],b,'simulation',timeout=600)
  assert 'PASS safety_real_system' in output;result['passed']=True;result['output']=[x for x in output.splitlines() if 'PASS safety' in x];print(result['output'])
 finally:
  result['source_sha256']={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in rtl+[b/'tb.v']}
  for p in b.glob('*.log'):shutil.copyfile(p,e/p.name)
  shutil.copyfile(b/'tb.v',e/'tb.v');shutil.copyfile(b/'dut_bindings.vh',e/'dut_bindings.vh')
  (e/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
