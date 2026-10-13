module td_probe(input clk,rst_n,scan_in,load,rx_async,output scan_out,tx,de);
reg [170:0] inp;
reg [43:0] obs;
wire [0:0] irq;
wire [0:0] s_awready;
wire [0:0] s_wready;
wire [0:0] s_bvalid;
wire [0:0] s_arready;
wire [0:0] s_rvalid;
wire [1:0] s_bresp;
wire [1:0] s_rresp;
wire [31:0] s_rdata;
always @(posedge clk) begin inp<={inp[169:0],scan_in}; if(load) obs<={tx,de,irq,s_awready,s_wready,s_bvalid,s_arready,s_rvalid,s_bresp,s_rresp,s_rdata}; else obs<={obs[42:0],1'b0}; end
assign scan_out=obs[43];
rs485_gp_bridge  dut(.clk(clk),.rst_n(rst_n),.rx(rx_async),
.time_us(inp[0 +: 64]),
.s_awaddr(inp[64 +: 33]),
.s_araddr(inp[97 +: 33]),
.s_wdata(inp[130 +: 32]),
.s_wstrb(inp[162 +: 4]),
.s_awvalid(inp[166 +: 1]),
.s_wvalid(inp[167 +: 1]),
.s_bready(inp[168 +: 1]),
.s_arvalid(inp[169 +: 1]),
.s_rready(inp[170 +: 1]),
.tx(tx),
.de(de),
.irq(irq),
.s_awready(s_awready),
.s_wready(s_wready),
.s_bvalid(s_bvalid),
.s_arready(s_arready),
.s_rvalid(s_rvalid),
.s_bresp(s_bresp),
.s_rresp(s_rresp),
.s_rdata(s_rdata));
endmodule
