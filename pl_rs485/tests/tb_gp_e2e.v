`timescale 1ns/1ps
module tb_gp_e2e;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,rx=1;reg [63:0] time_us=64'd900000;
 integer div=0,cycles=0,rise,stop;
 always @(posedge clk) begin cycles=cycles+1;if(div==99) begin div=0;time_us<=time_us+1;end else div=div+1;end
 `include "gp_bfm.vh"
 wire tx,de,irq;
 rs485_gp_bridge #(.NORMAL_CYCLES(100000),.POLL_CYCLES(100000)) dut(
 .clk(clk),.rst_n(rst_n),.time_us(time_us),.rx(rx),.tx(tx),.de(de),.irq(irq),
 .s_awaddr(s_awaddr),.s_araddr(s_araddr),.s_wdata(s_wdata),.s_wstrb(s_wstrb),
 .s_awvalid(s_awvalid),.s_wvalid(s_wvalid),.s_bready(s_bready),.s_arvalid(s_arvalid),.s_rready(s_rready),
 .s_awready(s_awready),.s_wready(s_wready),.s_bvalid(s_bvalid),.s_arready(s_arready),.s_rvalid(s_rvalid),.s_bresp(s_bresp),.s_rresp(s_rresp),.s_rdata(s_rdata));
 always @(posedge de) rise=cycles;
 task read_byte;output [7:0] b;integer j;
  begin ticks(1302);for(j=0;j<8;j=j+1) begin b[j]=tx;ticks(868);end if(tx!==1) $fatal(1,"stop");ticks(434);end
 endtask
 task send_byte;input [7:0] b;integer j;
  begin if(de) $fatal(1,"half-duplex overlap");rx=0;ticks(868);
   for(j=0;j<8;j=j+1) begin rx=b[j];ticks(868);end rx=1;ticks(868);end
 endtask
 function integer data_len;input [7:0] q;
  begin case(q) 8'h30:data_len=6;8'h33:data_len=4;8'h39:data_len=2;8'h3a,8'h3e:data_len=1;default:data_len=0;endcase end
 endfunction
 reg [7:0] a,c,checksum_byte,check,b;integer len,ix;
 initial forever begin
  @(negedge tx);if(cycles-rise<1000) $fatal(1,"DE pre");
  read_byte(a);@(negedge tx);read_byte(c);@(negedge tx);read_byte(checksum_byte);stop=cycles;
  if(a<8'he0 || a>8'he2 || data_len(c)==0 || checksum_byte!=((a+c)&255)) $fatal(1,"request whitelist/checksum");
  @(negedge de);if(cycles-stop<1000) $fatal(1,"DE true stop hold");
  ticks(2000);check=a;send_byte(a);len=data_len(c);
  for(ix=0;ix<len;ix=ix+1) begin b=ix+1;send_byte(b);check=check+b;end send_byte(check);
 end

 // Independent STEP activity cannot be affected by any GP/UART event.
 reg step=0,reference_step=0;integer step_div=0,reference_div=0;
 always @(posedge clk) begin
  if(step_div==36) begin step<=~step;step_div<=0;end else step_div<=step_div+1;
  if(reference_div==36) begin reference_step<=~reference_step;reference_div<=0;end else reference_div<=reference_div+1;
 end
 always @(negedge clk) if(step!==reference_step) $fatal(1,"STEP isolation");
 integer k,counts[0:2],n=0;reg [31:0] v,id,revision,old_revision;reg [255:0] rec;
 task await_result;input [31:0] state;
  begin v=0;while(!(v & (`RG_CFG_APPLIED|`RG_CFG_REJECTED))) rd(`RG_REG_CFG_STATE,0,v);
   if(v!=state) $fatal(1,"config result state %d",v);
  end
 endtask
 initial begin
  for(k=0;k<3;k=k+1) counts[k]=0;
  ticks(10);rst_n=1;await_result(5);eq(`RG_REG_CFG_REVISION,1);eq(`RG_REG_RUN,0);
  for(k=0;k<5;k=k+1) wr(`RG_REG_SHADOW_PERIOD0+k*4,0,15,0);
  wr(`RG_REG_SHADOW_PERIOD3,10000,15,0);wr(`RG_REG_SHADOW_MASK,8,15,0);wr(`RG_REG_TXN_ID,1,15,0);wr(`RG_REG_CFG_SUBMIT,1,15,0);
  await_result(5);eq(`RG_REG_CFG_REVISION,2);wr(`RG_REG_RUN,1,15,0);
  wait(dut.drop>=2);wr(`RG_REG_RUN,0,15,0);wait(!dut.busy);ticks(10);old_revision=dut.revision;
  // Budget/range rejects against true collector; source FIFO survives applies.
  wr(`RG_REG_SHADOW_PERIOD3,999,15,0);wr(`RG_REG_TXN_ID,2,15,0);wr(`RG_REG_CFG_SUBMIT,1,15,0);await_result(9);eq(`RG_REG_CFG_ERROR,1);
  wr(`RG_REG_SHADOW_PERIOD3,1000,15,0);wr(`RG_REG_TXN_ID,3,15,0);wr(`RG_REG_CFG_SUBMIT,1,15,0);await_result(9);eq(`RG_REG_CFG_ERROR,2);
  wr(`RG_REG_SHADOW_PERIOD3,20000,15,0);wr(`RG_REG_TXN_ID,4,15,0);wr(`RG_REG_CFG_SUBMIT,1,15,0);await_result(5);eq(`RG_REG_CFG_REVISION,3);
  for(k=0;k<8;k=k+1) begin
   wr(`RG_REG_CAPTURE,1,15,0);rd(`RG_REG_CAPTURE_ID,0,id);eq(`RG_REG_CAPTURE_REVISION,old_revision);read_record(rec);
   if(rec[255:248]!=1 || rec[231:224]!=0 || rec[239:232]!=8'h3a || rec[215:208]!=1 || rec[7:0]!=1) $fatal(1,"e2e decode");
   if(rec[247:240]<8'he0 || rec[247:240]>8'he2 || rec[175:112]>rec[111:48]) $fatal(1,"e2e address/time");
   counts[rec[247:240]-8'he0]=counts[rec[247:240]-8'he0]+1;n=n+1;wr(`RG_REG_CONSUME_ID,id,15,0);
  end
  for(k=0;k<3;k=k+1) if(counts[k]<2) $fatal(1,"multi-address missing");
  wr(`RG_REG_RUN,1,15,0);wait(dut.level>=3);wr(`RG_REG_RUN,0,15,0);wait(!dut.busy);
  while(dut.level!=0) begin
   wr(`RG_REG_CAPTURE,1,15,0);eq(`RG_REG_CAPTURE_REVISION,3);rd(`RG_REG_CAPTURE_ID,0,id);read_record(rec);wr(`RG_REG_CONSUME_ID,id,15,0);n=n+1;
  end
  wr(`RG_REG_SNAP_REQ_ID,1,15,0);wr(`RG_REG_SNAP_SUBMIT,1,15,0);
  rd(`RG_SNAPSHOT_BASE+`RG_SNAP_ACCEPTED*4,0,v);if(v<n+2) $fatal(1,"drop accounting");
  eq(`RG_SNAPSHOT_BASE+`RG_SNAP_ERRORS*4,0);
  force dut.collector.cfg_revision=32'hffffffff;
  wr(`RG_REG_TXN_ID,5,15,0);wr(`RG_REG_CFG_SUBMIT,1,15,0);await_result(9);eq(`RG_REG_CFG_ERROR,3);release dut.collector.cfg_revision;
  wr(`RG_REG_LOCAL_RESET,1,15,0);await_result(5);eq(`RG_REG_GENERATION,1);eq(`RG_REG_CFG_REVISION,1);eq(`RG_REG_RUN,0);
  $display("PASS GP e2e real 100MHz/115200 checks=%0d records=%0d drops>=2 STP isolated",checks,n);$finish;
 end
 initial begin #150000000;$fatal(1,"e2e watchdog");end
endmodule
