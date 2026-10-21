// GENERATED from rate_design.json and schema.json.
`define MR_CFG_NONE 0
`define MR_CFG_RANGE 1
`define MR_CFG_LOAD 2
`define MR_CFG_REVISION 3
function [31:0] query_wire_us;
input [2:0] q;
begin case(q)
3'd0: query_wire_us=(64'd11*10*BIT_CYCLES*1000000+CLK_HZ-1)/CLK_HZ;
3'd1: query_wire_us=(64'd9*10*BIT_CYCLES*1000000+CLK_HZ-1)/CLK_HZ;
3'd2: query_wire_us=(64'd7*10*BIT_CYCLES*1000000+CLK_HZ-1)/CLK_HZ;
3'd3: query_wire_us=(64'd6*10*BIT_CYCLES*1000000+CLK_HZ-1)/CLK_HZ;
3'd4: query_wire_us=(64'd6*10*BIT_CYCLES*1000000+CLK_HZ-1)/CLK_HZ;
default: query_wire_us=0;
endcase end endfunction
