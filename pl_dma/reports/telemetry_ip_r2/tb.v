`timescale 1ns/1ps
module tb_s2mm_real;
`include "dut_bindings.vh"
always #5 clk_100m=~clk_100m;
reg [7:0] memory[0:262143];
integer cycle=0,checks=0,transfers=0,streams=0,lasts=0;
integer read_beats=0,write_beats=0,stream_bytes=0,stream_expected=0;
integer max_occ=0;reg stall_all=0,stall_writes=0,monitor_packet=0;
reg rd_active=0,wr_active=0,b_pending=0;integer b_delay=0;
reg [32:0] rd_addr,wr_addr;reg [4:0] rd_left,wr_left;
reg [5:0] wr_id;integer j;
assign hp_arready=control_rst_n && !rd_active && !hp_rvalid && !stall_all && cycle%5!=0;
assign hp_awready=control_rst_n && !wr_active && !b_pending && !hp_bvalid && !stall_all && !stall_writes && cycle%7!=0;
assign hp_wready=control_rst_n && wr_active && !stall_all && !stall_writes && cycle%4!=0;
assign hp_bresp=0;assign hp_rresp=0;
function [63:0] word_at;input [32:0] a;integer k;
 begin for(k=0;k<8;k=k+1) word_at[8*k+:8]=memory[a+k];end
endfunction
task check;input condition;input [255:0] message;
 begin checks=checks+1;if(!condition) begin $display("FAIL %0s cycle=%0d",message,cycle);$fatal(1);end end
endtask
always @(posedge clk_100m) begin
 cycle<=cycle+1;
 if(cycle>2000000) $fatal(1,"watchdog");
 if(!control_rst_n) begin rd_active<=0;wr_active<=0;b_pending<=0;b_delay<=0;hp_rvalid<=0;hp_bvalid<=0;hp_rlast<=0;end
 else begin
  if(hp_arvalid && hp_arready) begin
   check(hp_araddr<262136 && hp_araddr[2:0]==0,"HP read address");
   check(hp_arlen<=15 && hp_arsize==3 && hp_arburst==1 && hp_arid==0,"HP read geometry");
   check(hp_arqos==0,"HP read QoS");
   check(dut.bridge_arsize[2]==0 && dut.bridge_arlock==0,"HP read no truncation");
   rd_active<=1;rd_addr<=hp_araddr;rd_left<=hp_arlen+1'b1;hp_rid<=hp_arid;
  end
  if(rd_active && !hp_rvalid && !stall_all && cycle%3!=0) begin
   hp_rdata<=word_at(rd_addr);hp_rvalid<=1;hp_rlast<=rd_left==1;
  end
  if(hp_rvalid && hp_rready) begin
   read_beats=read_beats+1;hp_rvalid<=0;rd_addr<=rd_addr+8;rd_left<=rd_left-1'b1;
   if(rd_left==1) rd_active<=0;
  end
  if(hp_awvalid && hp_awready) begin
   check(hp_awaddr<262136 && hp_awaddr[2:0]==0,"HP write address");
   check(hp_awlen<=15 && hp_awsize==3 && hp_awburst==1 && hp_awid==0,"HP write geometry");
   check(hp_awqos==0,"HP write QoS");
   check(dut.bridge_awsize[2]==0 && dut.bridge_awlock==0,"HP write no truncation");
   wr_active<=1;wr_addr<=hp_awaddr;wr_left<=hp_awlen+1'b1;wr_id<=hp_awid;
  end
  if(hp_wvalid && hp_wready) begin
   check(hp_wlast==(wr_left==1),"HP WLAST burst");write_beats=write_beats+1;
   for(j=0;j<8;j=j+1) if(hp_wstrb[j]) memory[wr_addr+j]<=hp_wdata[8*j+:8];
   wr_addr<=wr_addr+8;wr_left<=wr_left-1'b1;
   if(wr_left==1) begin wr_active<=0;b_pending<=1;b_delay<=5;end
  end
  // BVALID must disappear immediately after handshake, never resend B.
  if(b_pending && !hp_bvalid) begin
   if(b_delay!=0) b_delay<=b_delay-1;
   else begin hp_bvalid<=1;hp_bid<=wr_id;end
  end
  if(hp_bvalid && hp_bready) begin hp_bvalid<=0;b_pending<=0;end
  if(loop_occupancy>max_occ) max_occ=loop_occupancy;
  if(monitor_packet && dut.d_m_axis_mm2s_tvalid && dut.d_m_axis_mm2s_tready) begin
   streams=streams+1;
   for(j=0;j<8;j=j+1) if(dut.d_m_axis_mm2s_tkeep[j]) stream_bytes=stream_bytes+1;
   if(dut.d_m_axis_mm2s_tlast) begin
    lasts=lasts+1;check(stream_bytes==stream_expected,"MM2S byte count/TLAST");
   end else check(dut.d_m_axis_mm2s_tkeep==255,"full nonfinal TKEEP");
  end
 end
end
// AXI payload stability under deterministic memory backpressure.
reg rb=0,wb=0,ab=0,arb=0;reg [64:0] old_r;reg [72:0] old_w;
reg [42:0] old_aw,old_ar;
always @(posedge clk_100m) begin
 if(!control_rst_n) begin rb<=0;wb<=0;ab<=0;arb<=0;end
 else begin
  if(rb) check(hp_rvalid && {hp_rlast,hp_rdata}===old_r,"R blocked stable");
  if(wb) check(hp_wvalid && {hp_wlast,hp_wstrb,hp_wdata}===old_w,"W blocked stable");
  if(ab) check(hp_awvalid && {hp_awaddr,hp_awlen,hp_awsize,hp_awburst}===old_aw,"AW blocked stable");
  if(arb) check(hp_arvalid && {hp_araddr,hp_arlen,hp_arsize,hp_arburst}===old_ar,"AR blocked stable");
  rb<=hp_rvalid&&!hp_rready;wb<=hp_wvalid&&!hp_wready;ab<=hp_awvalid&&!hp_awready;arb<=hp_arvalid&&!hp_arready;
  old_r<={hp_rlast,hp_rdata};old_w<={hp_wlast,hp_wstrb,hp_wdata};
  old_aw<={hp_awaddr,hp_awlen,hp_awsize,hp_awburst};old_ar<={hp_araddr,hp_arlen,hp_arsize,hp_arburst};
 end
end
task write_reg;input [32:0] addr;input [31:0] value;input [3:0] strobe;input [1:0] response;input integer order;
 begin
  fork
   begin repeat(order==1 ? 3 : 0) @(negedge clk_100m);s_awaddr=addr;s_awvalid=1;
    @(posedge clk_100m);while(!s_awready) @(posedge clk_100m);@(negedge clk_100m);s_awvalid=0;end
   begin repeat(order==2 ? 3 : 0) @(negedge clk_100m);s_wdata=value;s_wstrb=strobe;s_wvalid=1;
    @(posedge clk_100m);while(!s_wready) @(posedge clk_100m);@(negedge clk_100m);s_wvalid=0;end
  join
  while(!s_bvalid) @(negedge clk_100m);
  repeat(3) begin check(s_bvalid && s_bresp==response,"Lite B hold/response");@(negedge clk_100m);end
  s_bready=1;@(negedge clk_100m);s_bready=0;
 end
endtask
task read_reg;input [32:0] addr;input [1:0] response;output [31:0] value;
 begin
  @(negedge clk_100m);s_araddr=addr;s_arvalid=1;
  @(posedge clk_100m);while(!s_arready) @(posedge clk_100m);@(negedge clk_100m);s_arvalid=0;
  while(!s_rvalid) @(negedge clk_100m);value=s_rdata;
  repeat(2) begin check(s_rvalid && s_rresp==response && s_rdata===value,"Lite R hold/response");@(negedge clk_100m);end
  s_rready=1;@(negedge clk_100m);s_rready=0;
 end
endtask
localparam [32:0] BASE=33'h080900000;
reg [31:0] status_value;integer n,pattern,k,polls,initial_lasts;
task reset_design;
 begin
  @(negedge clk_100m);arst_n=0;monitor_packet=0;
  repeat(6) @(negedge clk_100m);arst_n=1;repeat(25) @(negedge clk_100m);
  check(loop_occupancy==0,"reset FIFO empty");
 end
endtask
task reset_dma;
 begin
  write_reg(BASE,4,15,0,0);write_reg(BASE+48,4,15,0,1);
  polls=0;status_value=4;
  while(status_value[2] && polls<1000) begin read_reg(BASE,0,status_value);polls=polls+1;end
  check(!status_value[2],"DMA reset completes");repeat(15) @(negedge clk_100m);
  check(loop_occupancy==0,"DMA primary reset flush");
 end
endtask
task send_bytes;input integer size,send_last;integer x,z;
 begin
  for(x=0;x<size;x=x+8) begin
   @(negedge clk_100m);for(z=0;z<8;z=z+1) stream_data[z*8+:8]=(x+z)^8'h5a;
   stream_keep=255;stream_last=send_last && x+8==size;stream_valid=1;
   @(posedge clk_100m);while(!stream_ready && stream_rst_n) @(posedge clk_100m);
   @(negedge clk_100m);stream_valid=0;
  end
 end
endtask
task reset_rx;
 begin
  stream_valid=0;write_reg(BASE+48,4,15,0,0);polls=0;status_value=4;
  while(status_value[2] && polls<1000) begin read_reg(BASE+48,0,status_value);polls=polls+1;end
  check(!status_value[2],"independent reset complete");repeat(30) @(negedge clk_100m);
 end
endtask
task receive_case;input integer btt,size,last_flag,exact;integer x;reg [31:0] sr,actual;
 begin
  for(x=0;x<2048;x=x+1) memory[69632+x]=8'hcc;
  write_reg(BASE+48,32'h5001,15,0,0);write_reg(BASE+72,69632,15,0,0);write_reg(BASE+88,btt,15,0,0);
  send_bytes(size,last_flag);polls=0;sr=0;
  while(!(sr[12] || (sr&32'h770)!=0) && polls<200) begin read_reg(BASE+52,0,sr);polls=polls+1;end
  read_reg(BASE+88,0,actual);
  $display("PROBE BTT=%0d sent=%0d TLAST=%0d status=%h actual=%0d writes=%0d",btt,size,last_flag,sr,actual,write_beats);
  if(exact) begin
   check(sr[12] && (sr&32'h770)==0,"exact S2MM IOC");check(actual==size,"actual S2MM length");
   for(x=0;x<size;x=x+1) check(memory[69632+x]===((x^8'h5a)&255),"DDR bytes");
   check(memory[69632+size]==8'hcc,"DDR end guard");
  end
  reset_rx;
 end
endtask
initial begin
 clk_100m=0;arst_n=0;s_awaddr=0;s_araddr=0;s_awvalid=0;s_wvalid=0;s_bready=0;s_arvalid=0;s_rready=0;s_wdata=0;s_wstrb=0;
 hp_rdata=0;hp_rid=0;hp_rlast=0;hp_rvalid=0;hp_bid=0;hp_bvalid=0;stream_data=0;stream_keep=0;stream_last=0;stream_valid=0;
 reset_design;repeat(100) @(negedge clk_100m);check(stream_rst_n,"S2MM-only primary release");
 read_reg(BASE,2,status_value);write_reg(BASE+40,64,15,2,0);
 receive_case(64,64,1,1);receive_case(1024,1024,1,1);receive_case(1024,64,1,1);
 receive_case(64,128,1,0);receive_case(128,64,0,0);
 receive_case(192,192,1,1);
 check(read_beats==0,"S2MM-only no HP reads");check(hp_idle,"all HP write responses drained");
 $display("PASS telemetry_real_s2mm checks=%0d DDR writes=%0d no HP reads",checks,write_beats);$finish;
end

endmodule
