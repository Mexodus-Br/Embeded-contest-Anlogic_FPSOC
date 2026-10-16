`timescale 1ns/1ps
module tb_router;
reg clk=0,rst_n=0;always #5 clk=~clk;
reg [32:0] s_awaddr=0,s_araddr=0;reg [31:0] s_wdata=0;reg [3:0] s_wstrb=15;
reg s_awvalid=0,s_wvalid=0,s_bready=0,s_arvalid=0,s_rready=0;
wire s_awready,s_wready,s_bvalid,s_arready,s_rvalid;wire [1:0] s_bresp,s_rresp;wire [31:0] s_rdata;
wire [230:0] m_awaddr,m_araddr;wire [223:0] m_wdata;wire [27:0] m_wstrb;
wire [6:0] m_awvalid,m_wvalid,m_bready,m_arvalid,m_rready;
reg [6:0] m_awready=127,m_wready=127,m_bvalid=127,m_arready=127,m_rvalid=127;
reg [13:0] m_bresp,m_rresp;reg [223:0] m_rdata;
safety_axi_lite_seven_way dut(clk,rst_n,s_awaddr,s_araddr,s_wdata,s_wstrb,s_awvalid,s_wvalid,s_bready,s_arvalid,s_rready,
s_awready,s_wready,s_bvalid,s_arready,s_rvalid,s_bresp,s_rresp,s_rdata,m_awaddr,m_araddr,m_wdata,m_wstrb,m_awvalid,m_wvalid,m_bready,m_arvalid,m_rready,
m_awready,m_wready,m_bvalid,m_arready,m_rvalid,m_bresp,m_rresp,m_rdata);
integer checks=0,i,j,wowner,rowner;reg [32:0] addr;
task check;input condition;begin checks=checks+1;if(!condition)begin $display("FAIL router check=%0d",checks);$fatal(1);end end endtask
task tick;begin @(posedge clk);#1;end endtask
task transaction;input [32:0] address;input integer target;begin
 @(negedge clk);s_awaddr=address;s_araddr=address;s_wdata=32'h51a00000+target;
 // W before AW, and read independently in parallel.
 s_wvalid=1;s_arvalid=1;tick;
 @(negedge clk);s_wvalid=0;s_arvalid=0;s_awvalid=1;tick;
 @(negedge clk);s_awvalid=0;
 check(m_awvalid==(1<<target));check(m_wvalid==(1<<target));
 check(m_awaddr[target*33+:33]==address);check(m_araddr[target*33+:33]==address);
 tick;tick;check(s_bvalid&&s_rvalid);check(s_bresp==(target%4));check(s_rresp==((target+1)%4));check(s_rdata==32'hf0000000+target);
 // All six slaves assert valid: only the selected owner is acknowledged.
 repeat(4)begin tick;check(s_bvalid&&s_rvalid);check(m_bready==0&&m_rready==0);check(s_rdata==32'hf0000000+target);end
 @(negedge clk);s_bready=1;s_rready=1;#1;check(m_bready==(1<<target));check(m_rready==(1<<target));tick;
 @(negedge clk);s_bready=0;s_rready=0;check(!s_bvalid&&!s_rvalid);
end endtask
initial begin
 for(i=0;i<7;i=i+1)begin m_bresp[i*2+:2]=i%4;m_rresp[i*2+:2]=(i+1)%4;m_rdata[i*32+:32]=32'hf0000000+i;end
 repeat(3)tick;rst_n=1;tick;
 for(j=0;j<7;j=j+1)begin addr=33'h080400000+j*33'h100000;transaction(addr,j);transaction(addr+33'hffc,j);end
 transaction(33'h180400000,1);transaction(33'h180700000,1);transaction(33'h080b00000,1);transaction(33'h180a00000,1);transaction(33'h0803ffffc,1);transaction(33'h080401000,1);
 $display("PASS seven-way A33 response ownership checks=%0d",checks);$finish;
end
initial begin #100000;$fatal(1,"router timeout");end
endmodule
