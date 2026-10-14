module telem_probe(input clk,rst_n,scan_in,load,output scan_out);
reg [591:0] inp;reg [63:0] obs;
wire [31:0] o_snapshot_data;
wire [31:0] o_parse_errors;
always @(posedge clk) begin inp<={inp[590:0],scan_in};if(load) obs<={o_snapshot_data,o_parse_errors};else obs<={obs[62:0],1'b0};end
assign scan_out=obs[63];
rs485_latest_cache dut(.clk(clk),.rst_n(rst_n),.time_us(inp[0+: 64]),.collector_generation(inp[64+: 32]),.event_valid(inp[96+: 1]),.event_raw(inp[97+: 256]),.event_generation(inp[353+: 32]),.event_revision(inp[385+: 32]),.active_period_us(inp[417+: 160]),.active_mask(inp[577+: 5]),.snapshot_capture(inp[582+: 1]),.snapshot_word(inp[583+: 9]),.snapshot_data(o_snapshot_data),.parse_errors(o_parse_errors));
endmodule
