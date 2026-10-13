module td_probe(input clk,rst_n,scan_in,load,rx_async,output scan_out,tx,de);
reg [70:0] inp;
reg [416:0] obs;
wire valid,busy;
wire [255:0] record;
wire [31:0] level,dropped,accepted,errors,ignored;
always @(posedge clk) begin
 inp<={inp[69:0],scan_in};
 if(load) obs<={record,level,dropped,accepted,errors,ignored,valid};
 else obs<={obs[415:0],busy};
end
assign scan_out=obs[416];
rs485_master dut(.clk(clk),.rst_n(rst_n),.enable(inp[70]),.query_mask(inp[69:65]),
 .time_us(inp[63:0]),.rx(rx_async),.tx(tx),.de(de),.record_ready(inp[64]),
 .record_valid(valid),.record_data(record),.fifo_level(level),.dropped(dropped),
 .accepted(accepted),.errors(errors),.ignored_rx(ignored),.busy(busy));
endmodule
