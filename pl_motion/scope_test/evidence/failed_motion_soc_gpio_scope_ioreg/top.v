// Isolated generated PS reference; no bitstream/HPF/FSBL deployment.
module motion_soc_scope(input wire clk_100m, output wire a0_step,a0_dir,a0_en,a1_step,a1_dir,a1_en,a2_step,a2_dir,a2_en);
wire [3:0] motion_step,motion_dir,motion_en;wire gp0_aclk,hp0_aclk,arst_n,control_rst_n,unused_p2f_clk0;wire [15:0] f2p_irq;
wire [32:0] hp_araddr;
wire [1:0] hp_arburst;
wire [3:0] hp_arcache;
wire [5:0] hp_arid;
wire [3:0] hp_arlen;
wire hp_arlock;
wire [2:0] hp_arprot;
wire [3:0] hp_arqos;
wire hp_arready;
wire [1:0] hp_arsize;
wire hp_arvalid;
wire [32:0] hp_awaddr;
wire [1:0] hp_awburst;
wire [3:0] hp_awcache;
wire [5:0] hp_awid;
wire [3:0] hp_awlen;
wire hp_awlock;
wire [2:0] hp_awprot;
wire [3:0] hp_awqos;
wire hp_awready;
wire [1:0] hp_awsize;
wire hp_awvalid;
wire [5:0] hp_bid;
wire hp_bready;
wire [1:0] hp_bresp;
wire hp_bvalid;
wire [63:0] hp_rdata;
wire [5:0] hp_rid;
wire hp_rlast;
wire hp_rready;
wire [1:0] hp_rresp;
wire hp_rvalid;
wire [63:0] hp_wdata;
wire hp_wlast;
wire hp_wready;
wire [7:0] hp_wstrb;
wire hp_wvalid;
wire [32:0] gp_araddr;
wire [1:0] gp_arburst;
wire [3:0] gp_arcache;
wire [11:0] gp_arid;
wire [3:0] gp_arlen;
wire gp_arlock;
wire [2:0] gp_arprot;
wire gp_arready;
wire [1:0] gp_arsize;
wire gp_arvalid;
wire [32:0] gp_awaddr;
wire [1:0] gp_awburst;
wire [3:0] gp_awcache;
wire [11:0] gp_awid;
wire [3:0] gp_awlen;
wire gp_awlock;
wire [2:0] gp_awprot;
wire gp_awready;
wire [1:0] gp_awsize;
wire gp_awvalid;
wire [11:0] gp_bid;
wire gp_bready;
wire [1:0] gp_bresp;
wire gp_bvalid;
wire [31:0] gp_rdata;
wire [11:0] gp_rid;
wire gp_rlast;
wire gp_rready;
wire [1:0] gp_rresp;
wire gp_rvalid;
wire [31:0] gp_wdata;
wire gp_wlast;
wire gp_wready;
wire [3:0] gp_wstrb;
wire gp_wvalid;
assign a0_step=motion_step[0];
assign a0_dir=motion_dir[0];
assign a0_en=motion_en[0];
assign a1_step=motion_step[1];
assign a1_dir=motion_dir[1];
assign a1_en=motion_en[1];
assign a2_step=motion_step[2];
assign a2_dir=motion_dir[2];
assign a2_en=motion_en[2];
ARM_Processor_System_f6ddd1d59490 #(.P2F_CLK0_DIV(8),.Slave_AXI_HP0_DATA_WIDTH(64)) ps(
.slave_hp0_axi_aclk(hp0_aclk),
.slave_hp0_axi_araddr(hp_araddr),
.slave_hp0_axi_arburst(hp_arburst),
.slave_hp0_axi_arcache(hp_arcache),
.slave_hp0_axi_arid(hp_arid),
.slave_hp0_axi_arlen(hp_arlen),
.slave_hp0_axi_arlock(hp_arlock),
.slave_hp0_axi_arprot(hp_arprot),
.slave_hp0_axi_arqos(hp_arqos),
.slave_hp0_axi_arready(hp_arready),
.slave_hp0_axi_arsize(hp_arsize),
.slave_hp0_axi_arvalid(hp_arvalid),
.slave_hp0_axi_awaddr(hp_awaddr),
.slave_hp0_axi_awburst(hp_awburst),
.slave_hp0_axi_awcache(hp_awcache),
.slave_hp0_axi_awid(hp_awid),
.slave_hp0_axi_awlen(hp_awlen),
.slave_hp0_axi_awlock(hp_awlock),
.slave_hp0_axi_awprot(hp_awprot),
.slave_hp0_axi_awqos(hp_awqos),
.slave_hp0_axi_awready(hp_awready),
.slave_hp0_axi_awsize(hp_awsize),
.slave_hp0_axi_awvalid(hp_awvalid),
.slave_hp0_axi_bid(hp_bid),
.slave_hp0_axi_bready(hp_bready),
.slave_hp0_axi_bresp(hp_bresp),
.slave_hp0_axi_bvalid(hp_bvalid),
.slave_hp0_axi_rdata(hp_rdata),
.slave_hp0_axi_rid(hp_rid),
.slave_hp0_axi_rlast(hp_rlast),
.slave_hp0_axi_rready(hp_rready),
.slave_hp0_axi_rresp(hp_rresp),
.slave_hp0_axi_rvalid(hp_rvalid),
.slave_hp0_axi_wdata(hp_wdata),
.slave_hp0_axi_wlast(hp_wlast),
.slave_hp0_axi_wready(hp_wready),
.slave_hp0_axi_wstrb(hp_wstrb),
.slave_hp0_axi_wvalid(hp_wvalid),
.master_gp0_axi_aclk(gp0_aclk),
.master_gp0_axi_araddr(gp_araddr),
.master_gp0_axi_arburst(gp_arburst),
.master_gp0_axi_arcache(gp_arcache),
.master_gp0_axi_arid(gp_arid),
.master_gp0_axi_arlen(gp_arlen),
.master_gp0_axi_arlock(gp_arlock),
.master_gp0_axi_arprot(gp_arprot),
.master_gp0_axi_arready(gp_arready),
.master_gp0_axi_arsize(gp_arsize),
.master_gp0_axi_arvalid(gp_arvalid),
.master_gp0_axi_awaddr(gp_awaddr),
.master_gp0_axi_awburst(gp_awburst),
.master_gp0_axi_awcache(gp_awcache),
.master_gp0_axi_awid(gp_awid),
.master_gp0_axi_awlen(gp_awlen),
.master_gp0_axi_awlock(gp_awlock),
.master_gp0_axi_awprot(gp_awprot),
.master_gp0_axi_awready(gp_awready),
.master_gp0_axi_awsize(gp_awsize),
.master_gp0_axi_awvalid(gp_awvalid),
.master_gp0_axi_bid(gp_bid),
.master_gp0_axi_bready(gp_bready),
.master_gp0_axi_bresp(gp_bresp),
.master_gp0_axi_bvalid(gp_bvalid),
.master_gp0_axi_rdata(gp_rdata),
.master_gp0_axi_rid(gp_rid),
.master_gp0_axi_rlast(gp_rlast),
.master_gp0_axi_rready(gp_rready),
.master_gp0_axi_rresp(gp_rresp),
.master_gp0_axi_rvalid(gp_rvalid),
.master_gp0_axi_wdata(gp_wdata),
.master_gp0_axi_wlast(gp_wlast),
.master_gp0_axi_wready(gp_wready),
.master_gp0_axi_wstrb(gp_wstrb),
.master_gp0_axi_wvalid(gp_wvalid),
.f2p_irq(f2p_irq),
.p2f_rst0_n(arst_n),
.p2f_clk0(unused_p2f_clk0));
motion_gp_ps_top #(.STEP_HIGH_CYCLES({64'd0,{3{64'd500}}}),.STEP_LOW_CYCLES({64'd0,{3{64'd500}}}),.DIR_SETUP_CYCLES({64'd0,{3{64'd500}}}),.DIR_HOLD_CYCLES({64'd0,{3{64'd500}}}),.EN_SETUP_CYCLES({64'd0,{3{64'd500}}}),.EN_DISABLE_CYCLES({64'd0,{3{64'd500}}}),.MAX_STEP_HZ({64'd0,{3{64'd100000}}}),.EN_ACTIVE_LEVEL(4'd15)) pl(
.clk_100m(clk_100m),
.arst_n(arst_n),
.gp0_aclk(gp0_aclk),
.hp0_aclk(hp0_aclk),
.control_rst_n(control_rst_n),
.f2p_irq(f2p_irq),
.motion_step(motion_step),
.motion_dir(motion_dir),
.motion_en(motion_en),
.hp_araddr(hp_araddr),
.hp_arburst(hp_arburst),
.hp_arcache(hp_arcache),
.hp_arid(hp_arid),
.hp_arlen(hp_arlen),
.hp_arlock(hp_arlock),
.hp_arprot(hp_arprot),
.hp_arqos(hp_arqos),
.hp_arready(hp_arready),
.hp_arsize(hp_arsize),
.hp_arvalid(hp_arvalid),
.hp_awaddr(hp_awaddr),
.hp_awburst(hp_awburst),
.hp_awcache(hp_awcache),
.hp_awid(hp_awid),
.hp_awlen(hp_awlen),
.hp_awlock(hp_awlock),
.hp_awprot(hp_awprot),
.hp_awqos(hp_awqos),
.hp_awready(hp_awready),
.hp_awsize(hp_awsize),
.hp_awvalid(hp_awvalid),
.hp_bid(hp_bid),
.hp_bready(hp_bready),
.hp_bresp(hp_bresp),
.hp_bvalid(hp_bvalid),
.hp_rdata(hp_rdata),
.hp_rid(hp_rid),
.hp_rlast(hp_rlast),
.hp_rready(hp_rready),
.hp_rresp(hp_rresp),
.hp_rvalid(hp_rvalid),
.hp_wdata(hp_wdata),
.hp_wlast(hp_wlast),
.hp_wready(hp_wready),
.hp_wstrb(hp_wstrb),
.hp_wvalid(hp_wvalid),
.gp_araddr(gp_araddr),
.gp_arburst(gp_arburst),
.gp_arcache(gp_arcache),
.gp_arid(gp_arid),
.gp_arlen(gp_arlen),
.gp_arlock(gp_arlock),
.gp_arprot(gp_arprot),
.gp_arready(gp_arready),
.gp_arsize(gp_arsize),
.gp_arvalid(gp_arvalid),
.gp_awaddr(gp_awaddr),
.gp_awburst(gp_awburst),
.gp_awcache(gp_awcache),
.gp_awid(gp_awid),
.gp_awlen(gp_awlen),
.gp_awlock(gp_awlock),
.gp_awprot(gp_awprot),
.gp_awready(gp_awready),
.gp_awsize(gp_awsize),
.gp_awvalid(gp_awvalid),
.gp_bid(gp_bid),
.gp_bready(gp_bready),
.gp_bresp(gp_bresp),
.gp_bvalid(gp_bvalid),
.gp_rdata(gp_rdata),
.gp_rid(gp_rid),
.gp_rlast(gp_rlast),
.gp_rready(gp_rready),
.gp_rresp(gp_rresp),
.gp_rvalid(gp_rvalid),
.gp_wdata(gp_wdata),
.gp_wlast(gp_wlast),
.gp_wready(gp_wready),
.gp_wstrb(gp_wstrb),
.gp_wvalid(gp_wvalid));
endmodule
