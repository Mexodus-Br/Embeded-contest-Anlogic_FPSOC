`timescale 1ns/1ps
`include "generated/interface_defs.vh"
// Preserve independent AW/W and R/B backpressure. Reject before vendor MMIO.
module telemetry_dma_guard(
 input wire clk,rst_n,
 input wire [32:0] s_awaddr,input wire s_awvalid,output wire s_awready,
 input wire [31:0] s_wdata,input wire [3:0] s_wstrb,input wire s_wvalid,output wire s_wready,
 output wire [1:0] s_bresp,output wire s_bvalid,input wire s_bready,
 input wire [32:0] s_araddr,input wire s_arvalid,output wire s_arready,
 output wire [31:0] s_rdata,output wire [1:0] s_rresp,output wire s_rvalid,input wire s_rready,
 output wire [9:0] m_awaddr,output wire m_awvalid,input wire m_awready,
 output wire [31:0] m_wdata,output wire m_wvalid,input wire m_wready,
 input wire [1:0] m_bresp,input wire m_bvalid,output wire m_bready,
 output wire [9:0] m_araddr,output wire m_arvalid,input wire m_arready,
 input wire [31:0] m_rdata,input wire [1:0] m_rresp,input wire m_rvalid,output wire m_rready
);
 localparam [32:0] BASE={1'b0,`PLI_TELEM_DMA_BASE};
 reg ah,wh,asent,wsent;reg [32:0] wa;reg [31:0] wd;reg [3:0] st;
 reg rh,rsent;reg [32:0] ra;
 function [1:0] address_error;input [32:0] a;
 begin
  if(a[32:12]!=BASE[32:12]) address_error=3;
  else if(a[11:10]!=0 || a[1:0]!=0) address_error=2;
  else if(!(a[9:0]==10'h030 || a[9:0]==10'h034 || a[9:0]==10'h048 || a[9:0]==10'h04c || a[9:0]==10'h058)) address_error=2;
  else address_error=0;
 end endfunction
 // Reject a simple-mode BTT/address that would otherwise be silently aliased.
 wire length_bad=wa[9:0]==10'h058 && (wd==0 || wd>65535);
 wire address_bad=(wa[9:0]==10'h048 && wd[2:0]!=0) || (wa[9:0]==10'h04c && wd!=0);
 wire [1:0] we=address_error(wa)!=0 ? address_error(wa) : (st!=15 || length_bad || address_bad) ? 2 : 0;
 wire [1:0] re=address_error(ra);
 assign s_awready=rst_n && !ah;assign s_wready=rst_n && !wh;
 assign m_awaddr=wa[9:0];assign m_wdata=wd;
 assign m_awvalid=rst_n && ah && wh && we==0 && !asent;
 assign m_wvalid=rst_n && ah && wh && we==0 && !wsent;
 assign s_bvalid=rst_n && ah && wh && (we!=0 || (asent && wsent && m_bvalid));
 assign s_bresp=we!=0 ? we : m_bresp;
 assign m_bready=rst_n && ah && wh && we==0 && asent && wsent && s_bready;
 assign s_arready=rst_n && !rh;
 assign m_araddr=ra[9:0];assign m_arvalid=rst_n && rh && re==0 && !rsent;
 assign s_rvalid=rst_n && rh && (re!=0 || (rsent && m_rvalid));
 assign s_rresp=re!=0 ? re : m_rresp;assign s_rdata=re!=0 ? 0 : m_rdata;
 assign m_rready=rst_n && rh && re==0 && rsent && s_rready;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin ah<=0;wh<=0;asent<=0;wsent<=0;rh<=0;rsent<=0;wa<=0;wd<=0;st<=0;ra<=0;end
  else begin
   if(s_awvalid && s_awready) begin ah<=1;wa<=s_awaddr;end
   if(s_wvalid && s_wready) begin wh<=1;wd<=s_wdata;st<=s_wstrb;end
   if(m_awvalid && m_awready) asent<=1;
   if(m_wvalid && m_wready) wsent<=1;
   if(s_bvalid && s_bready) begin ah<=0;wh<=0;asent<=0;wsent<=0;end
   if(s_arvalid && s_arready) begin rh<=1;ra<=s_araddr;end
   if(m_arvalid && m_arready) rsent<=1;
   if(s_rvalid && s_rready) begin rh<=0;rsent<=0;end
  end
 end
endmodule
