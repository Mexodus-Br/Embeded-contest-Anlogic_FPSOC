module telem_probe(input clk,rst_n,scan_in,load,output scan_out);
reg [255:0] inp;reg [128:0] obs;
wire [5:0] o_task_index;
wire [0:0] o_well_formed;
wire [0:0] o_data_valid;
wire [0:0] o_enum_known;
wire [63:0] o_signed_value;
wire [31:0] o_carry;
wire [15:0] o_value;
wire [7:0] o_enum_raw;
always @(posedge clk) begin inp<={inp[254:0],scan_in};if(load) obs<={o_task_index,o_well_formed,o_data_valid,o_enum_known,o_signed_value,o_carry,o_value,o_enum_raw};else obs<={obs[127:0],1'b0};end
assign scan_out=obs[128];
rs485_light_parse dut(.raw(inp[0+: 256]),.task_index(o_task_index),.well_formed(o_well_formed),.data_valid(o_data_valid),.enum_known(o_enum_known),.signed_value(o_signed_value),.carry(o_carry),.value(o_value),.enum_raw(o_enum_raw));
endmodule
