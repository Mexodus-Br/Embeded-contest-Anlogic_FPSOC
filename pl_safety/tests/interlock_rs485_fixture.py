"""Guarded old GP entries using the original randomized AW/W BFM and FIFO."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def render():
    text = (ROOT / 'pl_rs485/tests/tb_gp_regs.v').read_text()
    text = text[:text.index(' initial begin\n  ticks(5)')]
    text = text.replace('module tb_gp_regs;', 'module tb_interlock_rs485;\n`include "interlock_gp_defs.vh"')
    text = text.replace(' rs485_gp_regs dut(', ''' reg safe_idle=1,safe_off=1;
 wire effective_run,stop_commit,local_reset,pending_config,applied_config;
 rs485_gp_regs #(.INTERLOCK_SUPPORT(1)) dut(
 .interlock_idle(safe_idle),.interlock_idle_off(safe_off),.interlock_run(effective_run),.interlock_stop_commit(stop_commit),
 .interlock_reset(local_reset),.interlock_config_pending(pending_config),.interlock_config_change(applied_config),''')
    return text + r'''
 integer si,vi;reg [31:0] trial,lane_mask,expected_word;
 always @(posedge clk)if(rst_n && dut.write_fire && dut.wa[11:0]==`RG_REG_RUN &&
   dut.effective_run_write>1)begin
  if(effective_run!==run || stop_commit)$fatal(1,"rejected RUN write must not suspend/restart monitor");
 end
 // Differential oracle for the original full address/merge predicate. This
 // verifies predecoding across independent AW/W capture and all WSTRB masks.
 always @(posedge clk)if(rst_n && dut.write_fire)begin
  if(effective_run!==run)$fatal(1,"monitor RUN must equal actual collector RUN");
  if((effective_run && !stop_commit) !== (run && !(dut.wa=={1'b0,`RG_BASE}+`RG_REG_RUN &&
       dut.ws!=0 && dut.effective_run_write==0 && dut.reset_count==0 && safe_idle)))
   $fatal(1,"RUN clear must take effect on the original accepted write edge");
 end
 initial begin
  ticks(5);rst_n=1;ticks(3);
  eq(`RG_REG_PROFILE,`RGI_PROFILE);eq(`RG_REG_VERSION,2);eq(`RG_REG_CAPS,63);
  wr(`RG_REG_RUN,1,15,2);eq(`RG_REG_RUN,0);
  ap={32'd1000000,128'd0};am=16;
  busy=1;wr(`RG_REG_RUN,1,15,2);eq(`RG_REG_RUN,0);busy=0;
  wr(`RG_REG_RUN,1,15,0);eq(`RG_REG_RUN,1);
  wr(`RG_REG_RUN,2,15,2);eq(`RG_REG_RUN,1);
  wr(`RG_REG_RUN,256,2,2);eq(`RG_REG_RUN,1);
  wr(`RG_REG_RUN,0,0,0);eq(`RG_REG_RUN,1);
  for(si=0;si<16;si=si+1)for(vi=0;vi<8;vi=vi+1)begin
   wr(`RG_REG_RUN,1,15,0);
   case(vi)
    0:trial=0;1:trial=1;2:trial=2;3:trial=32'h100;
    4:trial=32'h10000;5:trial=32'h1000000;6:trial=32'hffffffff;7:trial=32'h80000001;
   endcase
   lane_mask={{8{si[3]}},{8{si[2]}},{8{si[1]}},{8{si[0]}}};
   expected_word=(trial & lane_mask) | (32'd1 & ~lane_mask);
   wr(`RG_REG_RUN,trial,si[3:0],expected_word>1 ? 2:0);
   eq(`RG_REG_RUN,expected_word>1 ? 1:expected_word);
  end
  safe_idle=0;safe_off=0;
  wr(`RG_REG_RUN,0,15,2);eq(`RG_REG_RUN,1);
  wr(`RG_REG_LOCAL_RESET,1,15,2);
  wr(`RG_REG_SHADOW_PERIOD4,1000000,15,0);wr(`RG_REG_SHADOW_MASK,16,15,0);
  wr(`RG_REG_TXN_ID,1,15,0);wr(`RG_REG_CFG_SUBMIT,1,15,2);
  if(configs!=0)$fatal(1,"motion-busy config bypass");
  safe_idle=1;
  wr(`RG_REG_RUN,0,15,0);wr(`RG_REG_LOCAL_RESET,1,15,2);
  wr(`RG_REG_SHADOW_MASK,0,15,0);wr(`RG_REG_CFG_SUBMIT,1,15,2);
  wr(`RG_REG_SHADOW_MASK,16,15,0);wr(`RG_REG_SHADOW_PERIOD4,0,15,0);
  wr(`RG_REG_CFG_SUBMIT,1,15,2);
  wr(`RG_REG_SHADOW_PERIOD4,1000000,15,0);wr(`RG_REG_CFG_SUBMIT,1,15,0);
  if(configs!=1 || captured_mask!=16 || captured[128+:32]!=1000000)$fatal(1,"atomic guarded config capture");
  if(!pending_config)$fatal(1,"pending application must block motion qualification");
  apply(0,0);if(pending_config)$fatal(1,"application pending did not retire");
  safe_off=1;wr(`RG_REG_LOCAL_RESET,1,15,0);ticks(5);
  if(run || dut.generation!=1)$fatal(1,"local reset retains RUN off and new generation");
  $display("PASS interlock_rs485_guard checks=%0d",checks);$finish;
 end
 initial begin #1000000;$fatal(1,"guard test timeout");end
endmodule
'''
