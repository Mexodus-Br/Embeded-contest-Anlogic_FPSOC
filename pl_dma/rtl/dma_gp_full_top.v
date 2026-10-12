`timescale 1ns/1ps
`include "generated/interface_defs.vh"
// PS boundary integration module; connect gp0_aclk to PS master_gp0_axi_aclk.
// Shared GP/DMA control front end; original GP implementation is unchanged.
module dma_gp_full_top(
    input wire clk_100m, arst_n,
    output wire gp0_aclk, control_rst_n, output wire [15:0] f2p_irq,
    input wire [11:0] gp_awid, input wire [32:0] gp_awaddr,
    input wire [3:0] gp_awlen, input wire [2:0] gp_awsize,
    input wire [1:0] gp_awburst, gp_awlock,
    input wire [3:0] gp_awcache, input wire [2:0] gp_awprot,
    input wire gp_awvalid, output wire gp_awready,
    input wire [11:0] gp_wid, input wire [31:0] gp_wdata,
    input wire [3:0] gp_wstrb, input wire gp_wlast, gp_wvalid,
    output wire gp_wready, output wire [11:0] gp_bid,
    output wire [1:0] gp_bresp, output wire gp_bvalid, input wire gp_bready,
    input wire [11:0] gp_arid, input wire [32:0] gp_araddr,
    input wire [3:0] gp_arlen, input wire [2:0] gp_arsize,
    input wire [1:0] gp_arburst, gp_arlock,
    input wire [3:0] gp_arcache, input wire [2:0] gp_arprot,
    input wire gp_arvalid, output wire gp_arready,
    output wire [11:0] gp_rid, output wire [31:0] gp_rdata,
    output wire [1:0] gp_rresp, output wire gp_rlast, gp_rvalid, input wire gp_rready
,
output wire [32:0] hp_araddr,
output wire [3:0] hp_arlen,
output wire [1:0] hp_arsize,
output wire [1:0] hp_arburst,
output wire [2:0] hp_arprot,
output wire [3:0] hp_arcache,
output wire hp_arvalid,
input wire hp_arready,
input wire [63:0] hp_rdata,
input wire [1:0] hp_rresp,
input wire hp_rlast,
input wire hp_rvalid,
output wire hp_rready,
output wire [32:0] hp_awaddr,
output wire [3:0] hp_awlen,
output wire [1:0] hp_awsize,
output wire [1:0] hp_awburst,
output wire [2:0] hp_awprot,
output wire [3:0] hp_awcache,
output wire hp_awvalid,
input wire hp_awready,
output wire [63:0] hp_wdata,
output wire [7:0] hp_wstrb,
output wire hp_wlast,
output wire hp_wvalid,
input wire hp_wready,
input wire [1:0] hp_bresp,
input wire hp_bvalid,
output wire hp_bready,
output wire [5:0] hp_awid,
output wire [5:0] hp_arid,
input wire [5:0] hp_bid,
input wire [5:0] hp_rid,
output wire hp_awlock,
output wire hp_arlock,
output wire [3:0] hp_awqos,
output wire [3:0] hp_arqos,
output wire hp0_aclk);
    reg [1:0] reset_release;
    always @(posedge clk_100m or negedge arst_n)
        if (!arst_n) reset_release<=0;
        else reset_release<={reset_release[0],1'b1};
    assign control_rst_n=reset_release[1];
    assign gp0_aclk=clk_100m;
    wire [32:0] s_awaddr,s_araddr;
    wire [2:0] unused_awprot,unused_arprot;
    wire s_awvalid,s_awready,s_wvalid,s_wready,s_bvalid,s_bready;
    wire s_arvalid,s_arready,s_rvalid,s_rready;
    wire [31:0] s_wdata,s_rdata;
    wire [3:0] s_wstrb; wire [1:0] s_bresp,s_rresp;
    // Protocol numeric codes are vendor parameters (AXI3=1, Lite=2),
    // not a second register/command ABI. Widths come from the sole schema.
    axi_protocol_converter_merge #(
        .AL_US_AXI_PROTOCOL(1),.AL_DS_AXI_PROTOCOL(2),
        .AL_AXI_ID_WIDTH(`PLI_GP_GP_CONTROL_PROBE_V1_ID_WIDTH),
        .AL_AXI_ADDR_WIDTH(`PLI_GP_GP_CONTROL_PROBE_V1_ADDRESS_WIDTH),
        .AL_AXI_DATA_WIDTH(`PLI_GP_GP_CONTROL_PROBE_V1_DATA_WIDTH),
        .AL_AXI_SUPPORTS_WRITE(1),.AL_AXI_SUPPORTS_READ(1),.AL_AXI_SUPPORTS_USER_SIGNALS(0)
    ) converter (
        .aclk(clk_100m),.aresetn(control_rst_n),
        .us_axi_awid(gp_awid),.us_axi_awaddr(gp_awaddr),.us_axi_awlen(gp_awlen),
        .us_axi_awsize(gp_awsize),.us_axi_awburst(gp_awburst),.us_axi_awlock(gp_awlock),
        .us_axi_awcache(gp_awcache),.us_axi_awprot(gp_awprot),.us_axi_awqos(4'd0),
        .us_axi_awregion(4'd0),.us_axi_awuser(1'b0),.us_axi_awvalid(gp_awvalid),.us_axi_awready(gp_awready),
        .us_axi_wid(gp_wid),.us_axi_wdata(gp_wdata),.us_axi_wstrb(gp_wstrb),.us_axi_wlast(gp_wlast),
        .us_axi_wuser(1'b0),.us_axi_wvalid(gp_wvalid),.us_axi_wready(gp_wready),
        .us_axi_bid(gp_bid),.us_axi_bresp(gp_bresp),.us_axi_buser(),.us_axi_bvalid(gp_bvalid),.us_axi_bready(gp_bready),
        .us_axi_arid(gp_arid),.us_axi_araddr(gp_araddr),.us_axi_arlen(gp_arlen),
        .us_axi_arsize(gp_arsize),.us_axi_arburst(gp_arburst),.us_axi_arlock(gp_arlock),
        .us_axi_arcache(gp_arcache),.us_axi_arprot(gp_arprot),.us_axi_arqos(4'd0),
        .us_axi_arregion(4'd0),.us_axi_aruser(1'b0),.us_axi_arvalid(gp_arvalid),.us_axi_arready(gp_arready),
        .us_axi_rid(gp_rid),.us_axi_rdata(gp_rdata),.us_axi_rresp(gp_rresp),.us_axi_rlast(gp_rlast),
        .us_axi_ruser(),.us_axi_rvalid(gp_rvalid),.us_axi_rready(gp_rready),
        .ds_axi_awaddr(s_awaddr),.ds_axi_awprot(unused_awprot),.ds_axi_awvalid(s_awvalid),.ds_axi_awready(s_awready),
        .ds_axi_wdata(s_wdata),.ds_axi_wstrb(s_wstrb),.ds_axi_wvalid(s_wvalid),.ds_axi_wready(s_wready),
        .ds_axi_bresp(s_bresp),.ds_axi_bvalid(s_bvalid),.ds_axi_bready(s_bready),
        .ds_axi_araddr(s_araddr),.ds_axi_arprot(unused_arprot),.ds_axi_arvalid(s_arvalid),.ds_axi_arready(s_arready),
        .ds_axi_rdata(s_rdata),.ds_axi_rresp(s_rresp),.ds_axi_rvalid(s_rvalid),.ds_axi_rready(s_rready),
        .ds_axi_bid(12'd0),.ds_axi_buser(1'b0),.ds_axi_rid(12'd0),.ds_axi_ruser(1'b0),.ds_axi_rlast(1'b1),
        .ds_axi_awid(),.ds_axi_awlen(),.ds_axi_awsize(),.ds_axi_awburst(),.ds_axi_awlock(),.ds_axi_awcache(),
        .ds_axi_awregion(),.ds_axi_awqos(),.ds_axi_awuser(),.ds_axi_wid(),.ds_axi_wlast(),.ds_axi_wuser(),
        .ds_axi_arid(),.ds_axi_arlen(),.ds_axi_arsize(),.ds_axi_arburst(),.ds_axi_arlock(),.ds_axi_arcache(),
        .ds_axi_arregion(),.ds_axi_arqos(),.ds_axi_aruser()
    );
dma_shared_lite_top fabric(.clk_100m(clk_100m),.arst_n(arst_n),.rst_n(control_rst_n),.control_rst_n(),.f2p_irq(f2p_irq),.loop_occupancy(),.s_awaddr(s_awaddr),.s_araddr(s_araddr),.s_wdata(s_wdata),.s_wstrb(s_wstrb),.s_awvalid(s_awvalid),.s_awready(s_awready),.s_wvalid(s_wvalid),.s_wready(s_wready),.s_bvalid(s_bvalid),.s_bready(s_bready),.s_bresp(s_bresp),.s_arvalid(s_arvalid),.s_arready(s_arready),.s_rvalid(s_rvalid),.s_rready(s_rready),.s_rdata(s_rdata),.s_rresp(s_rresp),.hp_araddr(hp_araddr),.hp_arlen(hp_arlen),.hp_arsize(hp_arsize),.hp_arburst(hp_arburst),.hp_arprot(hp_arprot),.hp_arcache(hp_arcache),.hp_arvalid(hp_arvalid),.hp_arready(hp_arready),.hp_rdata(hp_rdata),.hp_rresp(hp_rresp),.hp_rlast(hp_rlast),.hp_rvalid(hp_rvalid),.hp_rready(hp_rready),.hp_awaddr(hp_awaddr),.hp_awlen(hp_awlen),.hp_awsize(hp_awsize),.hp_awburst(hp_awburst),.hp_awprot(hp_awprot),.hp_awcache(hp_awcache),.hp_awvalid(hp_awvalid),.hp_awready(hp_awready),.hp_wdata(hp_wdata),.hp_wstrb(hp_wstrb),.hp_wlast(hp_wlast),.hp_wvalid(hp_wvalid),.hp_wready(hp_wready),.hp_bresp(hp_bresp),.hp_bvalid(hp_bvalid),.hp_bready(hp_bready),.hp_awid(hp_awid),.hp_arid(hp_arid),.hp_bid(hp_bid),.hp_rid(hp_rid),.hp_awlock(hp_awlock),.hp_arlock(hp_arlock),.hp_awqos(hp_awqos),.hp_arqos(hp_arqos),.hp0_aclk(hp0_aclk));
endmodule
