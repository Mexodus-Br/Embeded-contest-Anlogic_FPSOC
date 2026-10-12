`timescale 1ns/1ps
`include "generated/interface_defs.vh"
// One pending write and one pending read, with independent response ownership.
// Endpoint0 is the exact GP window; all other addresses go to DMA's full guard.
module axi_lite_two_way(
 input wire clk,rst_n,
 input wire [32:0] s_awaddr,s_araddr,input wire [31:0] s_wdata,input wire [3:0] s_wstrb,
 input wire s_awvalid,s_wvalid,s_bready,s_arvalid,s_rready,
 output wire s_awready,s_wready,s_bvalid,s_arready,s_rvalid,
 output wire [1:0] s_bresp,s_rresp,output wire [31:0] s_rdata,
 output wire [65:0] m_awaddr,m_araddr,output wire [63:0] m_wdata,
 output wire [7:0] m_wstrb,
 output wire [1:0] m_awvalid,m_wvalid,m_bready,m_arvalid,m_rready,
 input wire [1:0] m_awready,m_wready,m_bvalid,m_arready,m_rvalid,
 input wire [3:0] m_bresp,m_rresp,input wire [63:0] m_rdata
);
 localparam [32:0] GP_BASE={1'b0,`PLI_GP_GP_CONTROL_PROBE_V1_BASE};
 reg ah,wh,asent,wsent,write_sel,rh,rsent,read_sel;
 reg [32:0] wa,ra;reg [31:0] wd;reg [3:0] st;
 assign s_awready=rst_n && !ah;assign s_wready=rst_n && !wh;
 assign s_arready=rst_n && !rh;
 assign m_awaddr={wa,wa};assign m_araddr={ra,ra};assign m_wdata={wd,wd};assign m_wstrb={st,st};
 assign m_awvalid=(rst_n && ah && wh && !asent) ? (2'b01<<write_sel) : 0;
 assign m_wvalid=(rst_n && ah && wh && !wsent) ? (2'b01<<write_sel) : 0;
 assign s_bvalid=rst_n && ah && wh && asent && wsent && m_bvalid[write_sel];
 assign s_bresp=m_bresp[write_sel*2+:2];
 assign m_bready=(rst_n && ah && wh && asent && wsent && s_bready) ? (2'b01<<write_sel) : 0;
 assign m_arvalid=(rst_n && rh && !rsent) ? (2'b01<<read_sel) : 0;
 assign s_rvalid=rst_n && rh && rsent && m_rvalid[read_sel];
 assign s_rresp=m_rresp[read_sel*2+:2];assign s_rdata=m_rdata[read_sel*32+:32];
 assign m_rready=(rst_n && rh && rsent && s_rready) ? (2'b01<<read_sel) : 0;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin ah<=0;wh<=0;asent<=0;wsent<=0;write_sel<=0;rh<=0;rsent<=0;read_sel<=0;wa<=0;ra<=0;wd<=0;st<=0;end
  else begin
   if(s_awvalid && s_awready) begin ah<=1;wa<=s_awaddr;write_sel<=s_awaddr[32:12]!=GP_BASE[32:12];end
   if(s_wvalid && s_wready) begin wh<=1;wd<=s_wdata;st<=s_wstrb;end
   if(m_awvalid[write_sel] && m_awready[write_sel]) asent<=1;
   if(m_wvalid[write_sel] && m_wready[write_sel]) wsent<=1;
   if(s_bvalid && s_bready) begin ah<=0;wh<=0;asent<=0;wsent<=0;end
   if(s_arvalid && s_arready) begin rh<=1;ra<=s_araddr;read_sel<=s_araddr[32:12]!=GP_BASE[32:12];end
   if(m_arvalid[read_sel] && m_arready[read_sel]) rsent<=1;
   if(s_rvalid && s_rready) begin rh<=0;rsent<=0;end
  end
 end
endmodule
