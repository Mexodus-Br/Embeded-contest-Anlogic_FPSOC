
`timescale 1ns/1ps

module ARM_Processor_System_f6ddd1d59490
#(

	parameter Slave_AXI_HP0_DATA_WIDTH = 64,
	parameter Slave_AXI_HP1_DATA_WIDTH = 64,
	parameter GPIO_PL_Dot_IO = 64

)
(

	output                        p2f_clk0
);

	wire [19:0] f2p_irq_TB;
	wire [34:0] p2f_irq;

//f2p_irq_TB	

	assign f2p_irq_TB[15:0] = 16'h0;

	assign f2p_irq_TB[16] = 1'b0;

	assign f2p_irq_TB[17] = 1'b0;

	assign f2p_irq_TB[18] = 1'b0;

	assign f2p_irq_TB[19] = 1'b0;

//p2f_irq

//	localparam real P2F_CLK0_DIV = p2f_clk0_1st_Divisor/2;
	
DR1_PHY_PROCESSOR_SYSTEM DR1_PHY_PROCESSOR_SYSTEM_Inst (
		.pl2ps_fahb_refclk(1'b1),
		.pl2ps_fahb_fbclk(1'b1),
		.master_fahb_hrdata(32'hFFFFFFFF),
		.master_fahb_hreadyout(1'b1),
		.master_fahb_hresp(1'b1),

		.gbe0_col(1'b0),
		.gbe0_crs(1'b0),
		.gbe0_rx_clk(1'b0),
		.gbe0_rxd(8'hFF),
		.gbe0_rxdv(1'b0),
		.gbe0_rxer(1'b0),
		.gbe0_ex_clk(1'b0),

		.gbe0_ptp_aux_ts_trig_i(1'b0),
		.gbe0_mcgr_dma_ack_i(1'b1),
		.gbe0_mcg_pst_trig_i(1'b0),
		.ptp0_clk_in(1'b1),
		.gbe0_ptp_timestamp_i(88'hFFFFFFFFFFFFFFFFFFFFFF),

		.mdio0_in(1'b0),

		.gbe1_col(1'b0),
		.gbe1_crs(1'b0),
		.gbe1_rx_clk(1'b0),
		.gbe1_rxd(8'hFF),
		.gbe1_rxdv(1'b0),
		.gbe1_rxer(1'b0),
		.gbe1_ex_clk(1'b0),

		.gbe1_ptp_aux_ts_trig_i(1'b0),
		.gbe1_mcgr_dma_ack_i(1'b1),
		.gbe1_mcg_pst_trig_i(1'b0),
		.ptp1_clk_in(1'b1),
		.gbe1_ptp_timestamp_i(88'hFFFFFFFFFFFFFFFFFFFFFF),

		.mdio1_in(1'b0),

		.slave_gp0_axi_aclk(1'b0),
		.slave_gp0_axi_araddr(33'h0),
		.slave_gp0_axi_arburst(2'h0),
		.slave_gp0_axi_arcache(4'h0),
		.slave_gp0_axi_arid(6'h0),
		.slave_gp0_axi_arlen(4'h0),
		.slave_gp0_axi_arlock(1'b0),
		.slave_gp0_axi_arprot(3'h0),
		.slave_gp0_axi_arsize(2'h0),
		.slave_gp0_axi_arvalid(1'b0),
		.slave_gp0_axi_awaddr(33'h0),
		.slave_gp0_axi_awburst(2'h0),
		.slave_gp0_axi_awcache(4'h0),
		.slave_gp0_axi_awid(6'h0),
		.slave_gp0_axi_awlen(4'h0),
		.slave_gp0_axi_awlock(1'b0),
		.slave_gp0_axi_awprot(3'h0),
		.slave_gp0_axi_awsize(2'h0),
		.slave_gp0_axi_awvalid(1'b0),
		.slave_gp0_axi_bready(1'b0),
		.slave_gp0_axi_rready(1'b0),
		.slave_gp0_axi_wdata(32'h0),
		.slave_gp0_axi_wlast(1'b0),
		.slave_gp0_axi_wstrb(4'h0),
		.slave_gp0_axi_wvalid(1'b0),

		.slave_gp1_axi_aclk(1'b0),
		.slave_gp1_axi_araddr(33'h0),
		.slave_gp1_axi_arburst(2'h0),
		.slave_gp1_axi_arcache(4'h0),
		.slave_gp1_axi_arid(6'h0),
		.slave_gp1_axi_arlen(4'h0),
		.slave_gp1_axi_arlock(1'b0),
		.slave_gp1_axi_arprot(3'h0),
		.slave_gp1_axi_arsize(2'h0),
		.slave_gp1_axi_arvalid(1'b0),
		.slave_gp1_axi_awaddr(33'h0),
		.slave_gp1_axi_awburst(2'h0),
		.slave_gp1_axi_awcache(4'h0),
		.slave_gp1_axi_awid(6'h0),
		.slave_gp1_axi_awlen(4'h0),
		.slave_gp1_axi_awlock(1'b0),
		.slave_gp1_axi_awprot(3'h0),
		.slave_gp1_axi_awsize(2'h0),
		.slave_gp1_axi_awvalid(1'b0),
		.slave_gp1_axi_bready(1'b0),
		.slave_gp1_axi_rready(1'b0),
		.slave_gp1_axi_wdata(32'h0),
		.slave_gp1_axi_wlast(1'b0),
		.slave_gp1_axi_wstrb(4'h0),
		.slave_gp1_axi_wvalid(1'b0),

		.slave_hp0_axi_aclk(1'b0),
		.slave_hp0_axi_araddr(33'h0),
		.slave_hp0_axi_arburst(2'h0),
		.slave_hp0_axi_arcache(4'h0),
		.slave_hp0_axi_arid(6'h0),
		.slave_hp0_axi_arlen(4'h0),
		.slave_hp0_axi_arlock(1'b0),
		.slave_hp0_axi_arprot(3'h0),
		.slave_hp0_axi_arqos(4'h0),
		.slave_hp0_axi_arsize(2'h0),
		.slave_hp0_axi_arvalid(1'b0),
		.slave_hp0_axi_awaddr(33'h0),
		.slave_hp0_axi_awburst(2'h0),
		.slave_hp0_axi_awcache(4'h0),
		.slave_hp0_axi_awid(6'h0),
		.slave_hp0_axi_awlen(4'h0),
		.slave_hp0_axi_awlock(1'b0),
		.slave_hp0_axi_awprot(3'h0),
		.slave_hp0_axi_awqos(4'h0),
		.slave_hp0_axi_awsize(2'h0),
		.slave_hp0_axi_awvalid(1'b0),
		.slave_hp0_axi_bready(1'b0),
		.slave_hp0_axi_rready(1'b0),
		.slave_hp0_axi_wdata(32'h0),
		.slave_hp0_axi_wlast(1'b0),
		.slave_hp0_axi_wstrb(4'h0),
		.slave_hp0_axi_wvalid(1'b0),

		.slave_hp1_axi_aclk(1'b0),
		.slave_hp1_axi_araddr(33'h0),
		.slave_hp1_axi_arburst(2'h0),
		.slave_hp1_axi_arcache(4'h0),
		.slave_hp1_axi_arid(6'h0),
		.slave_hp1_axi_arlen(4'h0),
		.slave_hp1_axi_arlock(1'b0),
		.slave_hp1_axi_arprot(3'h0),
		.slave_hp1_axi_arqos(4'h0),
		.slave_hp1_axi_arsize(2'h0),
		.slave_hp1_axi_arvalid(1'b0),
		.slave_hp1_axi_awaddr(33'h0),
		.slave_hp1_axi_awburst(2'h0),
		.slave_hp1_axi_awcache(4'h0),
		.slave_hp1_axi_awid(6'h0),
		.slave_hp1_axi_awlen(4'h0),
		.slave_hp1_axi_awlock(1'b0),
		.slave_hp1_axi_awprot(3'h0),
		.slave_hp1_axi_awqos(4'h0),
		.slave_hp1_axi_awsize(2'h0),
		.slave_hp1_axi_awvalid(1'b0),
		.slave_hp1_axi_bready(1'b0),
		.slave_hp1_axi_rready(1'b0),
		.slave_hp1_axi_wdata(32'h0),
		.slave_hp1_axi_wlast(1'b0),
		.slave_hp1_axi_wstrb(4'h0),
		.slave_hp1_axi_wvalid(1'b0),

		.f2p_cti_trig(4'hF),
		.p2f_cti_trig_ack(4'hF),

		.master_gp0_axi_aclk(1'b0),
		.master_gp0_axi_arready(1'b1),
		.master_gp0_axi_awready(1'b1),
		.master_gp0_axi_bid(12'h0),
		.master_gp0_axi_bresp(2'h3),
		.master_gp0_axi_bvalid(1'b0),
		.master_gp0_axi_rdata(32'h0),
		.master_gp0_axi_rid(12'h0),
		.master_gp0_axi_rlast(1'b0),
		.master_gp0_axi_rresp(2'h3),
		.master_gp0_axi_rvalid(1'b1),
		.master_gp0_axi_wready(1'b0),

		.master_gp1_axi_aclk(1'b0),
		.master_gp1_axi_arready(1'b1),
		.master_gp1_axi_awready(1'b1),
		.master_gp1_axi_bid(12'h0),
		.master_gp1_axi_bresp(2'h3),
		.master_gp1_axi_bvalid(1'b0),
		.master_gp1_axi_rdata(32'h0),
		.master_gp1_axi_rid(12'h0),
		.master_gp1_axi_rlast(1'b0),
		.master_gp1_axi_rresp(2'h3),
		.master_gp1_axi_rvalid(1'b1),
		.master_gp1_axi_wready(1'b0),

		.slave_acp_aclk_in(1'b0),
		.slave_acp_araddr(33'h0),
		.slave_acp_arcache(4'h0),
		.slave_acp_arid(5'h0),
		.slave_acp_arlen(3'h0),
		.slave_acp_arprot(3'h0),
		.slave_acp_arusers(2'h0),
		.slave_acp_arvalid(1'b0),
		.slave_acp_awaddr(33'h0),
		.slave_acp_awcache(4'h0),
		.slave_acp_awid(5'h0),
		.slave_acp_awlen(3'h0),
		.slave_acp_awprot(3'h0),
		.slave_acp_awusers(2'h0),
		.slave_acp_awvalid(1'b0),
		.slave_acp_bready(1'b0),
		.slave_acp_rready(1'b0),
		.slave_acp_wdata(64'h0),
		.slave_acp_wlast(1'b0),
		.slave_acp_wstrb(8'h0),
		.slave_acp_wvalid(1'b0),

		.f2p_irq(f2p_irq_TB),
		.p2f_irq(p2f_irq),

		.uart0_rx_in(1'b1),
		.uart0_cts_n(1'b0),
		.uart0_dcd_n(1'b0),
		.uart0_dsr_n(1'b0),
		.uart0_ri_n(1'b0),

		.uart1_rx_in(1'b1),
		.uart1_cts_n(1'b0),
		.uart1_dcd_n(1'b0),
		.uart1_dsr_n(1'b0),
		.uart1_ri_n(1'b0),

		.dmac0_clk_in(1'b0),
		.dma0_daready(1'b0),
		.dma0_drlast(1'b0),
		.dma0_drtype(2'h3),
		.dma0_drvalid(1'b0),

		.dmac1_clk_in(1'b0),
		.dma1_daready(1'b0),
		.dma1_drlast(1'b0),
		.dma1_drtype(2'h3),
		.dma1_drvalid(1'b0),

		.dmac2_clk_in(1'b0),
		.dma2_daready(1'b0),
		.dma2_drlast(1'b0),
		.dma2_drtype(2'h3),
		.dma2_drvalid(1'b0),

		.dmac3_clk_in(1'b0),
		.dma3_daready(1'b0),
		.dma3_drlast(1'b0),
		.dma3_drtype(2'h3),
		.dma3_drvalid(1'b0),

		.can0_rx_in(1'b0),

		.can1_rx_in(1'b0),

		.gpio_in(64'h0),

		.i2c0_scl_in(1'b0),
		.i2c0_sda_in(1'b0),

		.i2c1_scl_in(1'b0),
		.i2c1_sda_in(1'b0),

		.sdio0_cmd_in(1'b0),
		.sdio0_data_0_in(1'b0),
		.sdio0_data_1_in(1'b0),
		.sdio0_data_2_in(1'b0),
		.sdio0_data_3_in(1'b0),
		.sdio0_data_4_in(1'b0),
		.sdio0_data_5_in(1'b0),
		.sdio0_data_6_in(1'b0),
		.sdio0_data_7_in(1'b0),
		.sdio0_cd_in(1'b0),
		.sdio0_wp_in(1'b0),

		.sdio1_cmd_in(1'b0),
		.sdio1_data_0_in(1'b0),
		.sdio1_data_1_in(1'b0),
		.sdio1_data_2_in(1'b0),
		.sdio1_data_3_in(1'b0),
		.sdio1_cd_in(1'b0),
		.sdio1_wp_in(1'b0),

		.spi0_sclk_in(1'b0),
		.spi0_miso_in(1'b0),
		.spi0_mosi_in(1'b0),
		.spi0_ss_0_in(1'b0),

		.spi1_sclk_in(1'b0),
		.spi1_miso_in(1'b0),
		.spi1_mosi_in(1'b0),
		.spi1_ss_0_in(1'b0),

		.swdt_clk_in(1'b0),

		.ttc0_clk0_in(1'b0),
		.ttc0_clk1_in(1'b0),
		.ttc0_clk2_in(1'b0),

		.ttc1_clk0_in(1'b0),
		.ttc1_clk1_in(1'b0),
		.ttc1_clk2_in(1'b0),

		.event_in(1'b0),

		.p2f_clk0(p2f_clk0)
	);

endmodule
