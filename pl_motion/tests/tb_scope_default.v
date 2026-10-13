`timescale 1ns/1ps
`include "generated/interface_defs.vh"
// Default motion_service parameters remain zero even with exported GPIO wires.
module tb_scope_default;
reg clk=0,rst_n=0;always #5 clk=~clk;
reg [32:0] awaddr=0,araddr=0;reg [31:0] wd=0;reg av=0,wv=0,bready=0,rv=0,rready=0;
wire awready,wready,bvalid,arready,rvalid;wire [1:0] bresp,rresp;wire [31:0] rd;
wire [3:0] step,dir,en;integer checks=0,cycles=0;reg [31:0] value;
localparam [32:0] MB={1'b0,`PLI_MOTION_GP_MOTION_V1_BASE};
motion_service dut(.clk(clk),.rst_n(rst_n),.dma_reset_released(1'b1),.dma_error(1'b0),.fault(4'd0),
 .s_awaddr(awaddr),.s_araddr(araddr),.s_wdata(wd),.s_wstrb(4'hf),.s_awvalid(av),.s_wvalid(wv),.s_bready(bready),.s_arvalid(rv),.s_rready(rready),
 .s_awready(awready),.s_wready(wready),.s_arready(arready),.s_bvalid(bvalid),.s_rvalid(rvalid),.s_bresp(bresp),.s_rresp(rresp),.s_rdata(rd),
 .stream_data(64'd0),.stream_keep(8'hff),.stream_last(1'b0),.stream_valid(1'b0),.stream_ready(),.irq(),
 .step(step),.dir(dir),.en(en),.position_valid(),.position(),.pulses(),.running(),.paused(),.core_busy(),.session_valid(),
 .session_id(),.fifo_level(),.prepared_level(),.buffered_points(),.point_start(),.point_done(),.stopped(),.pulse_event(),.slot_event(),.slot_id());
task check;input condition;begin checks=checks+1;if(!condition)$fatal(1,"default must prohibit motion");end endtask
always @(negedge clk)begin cycles=cycles+1;if(cycles>10000)$fatal(1,"default watchdog");if(rst_n)check(step==0 && en==0);end
task write;input [31:0] offset,data;begin
 @(negedge clk);awaddr=MB+offset;wd=data;av=1;wv=1;
 @(posedge clk);while(!awready || !wready)@(posedge clk);
 @(negedge clk);av=0;wv=0;bready=1;
 while(!bvalid)@(negedge clk);check(bresp==0);@(negedge clk);bready=0;
end endtask
task read;input [31:0] offset;begin
 @(negedge clk);araddr=MB+offset;rv=1;
 @(posedge clk);while(!arready)@(posedge clk);
 @(negedge clk);rv=0;rready=1;while(!rvalid)@(negedge clk);value=rd;check(rresp==0);@(negedge clk);rready=0;
end endtask
initial begin
 repeat(4)@(negedge clk);rst_n=1;repeat(600)@(negedge clk);
 read(`PLI_MOTION_GP_MOTION_V1_REG_STATUS);check(!(value&`PLI_MOTION_GP_MOTION_V1_STATUS_BITS_CONFIG_VALID_MASK));
 write(`PLI_MOTION_GP_MOTION_V1_REG_OPCODE,`PLI_CMD_ENABLE);write(`PLI_MOTION_GP_MOTION_V1_REG_ARG,7);
 write(`PLI_MOTION_GP_MOTION_V1_REG_TXN,1);write(`PLI_MOTION_GP_MOTION_V1_REG_SUBMIT,1);
 repeat(20)@(negedge clk);read(`PLI_MOTION_GP_MOTION_V1_REG_ACK_ERROR);check(value!=0);
 repeat(600)@(negedge clk);check(step==0 && dir==15 && en==0);
 $display("PASS scope_default_zero checks=%0d",checks);$finish;
end
endmodule
