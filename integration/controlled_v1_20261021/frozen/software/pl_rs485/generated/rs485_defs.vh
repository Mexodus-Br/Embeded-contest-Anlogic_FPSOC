// GENERATED from schema.json; edit the schema and rerun tools/generate.py.
`define RS_VERSION 1
`define RS_RECORD_BITS 256
`define RS_CLK_HZ 100000000
`define RS_BAUD 115200
`define RS_SLAVE_COUNT 3
`define RS_SLAVE_ADDRS 14868960
`define RS_QUERY_MASK 31
`define RS_POLL_CYCLES 1000000
`define RS_TIMEOUT_CYCLES 1000000
`define RS_INTERBYTE_CYCLES 200000
`define RS_RETRIES 1
`define RS_PRE_CYCLES 1000
`define RS_POST_CYCLES 1000
`define RS_TURN_CYCLES 1000
`define RS_QUIET_CYCLES 1000000
`define RS_FIFO_DEPTH 8
`define RS_STATUS_VALID 0
`define RS_STATUS_CHECKSUM 1
`define RS_STATUS_FRAMING 2
`define RS_STATUS_TIMEOUT 3
`define RS_STATUS_TRUNCATED 4
`define RS_STATUS_ADDRESS 5
`define RS_STATUS_BUS_BUSY 6
`define RS_PAYLOAD_LSB 0
`define RS_PAYLOAD_WIDTH 48
`define RS_EVENT_US_LSB 48
`define RS_EVENT_US_WIDTH 64
`define RS_REQUEST_US_LSB 112
`define RS_REQUEST_US_WIDTH 64
`define RS_SEQUENCE_LSB 176
`define RS_SEQUENCE_WIDTH 32
`define RS_LENGTH_LSB 208
`define RS_LENGTH_WIDTH 8
`define RS_ATTEMPT_LSB 216
`define RS_ATTEMPT_WIDTH 8
`define RS_STATUS_LSB 224
`define RS_STATUS_WIDTH 8
`define RS_QUERY_LSB 232
`define RS_QUERY_WIDTH 8
`define RS_ADDRESS_LSB 240
`define RS_ADDRESS_WIDTH 8
`define RS_VERSION_LSB 248
`define RS_VERSION_WIDTH 8
function [7:0] query_code;
input [2:0] index;
begin case(index)
3'd0: query_code=8'h30;
3'd1: query_code=8'h33;
3'd2: query_code=8'h39;
3'd3: query_code=8'h3a;
3'd4: query_code=8'h3e;
default: query_code=0;
endcase end endfunction
function [3:0] query_length;
input [2:0] index;
begin case(index)
3'd0: query_length=4'd6;
3'd1: query_length=4'd4;
3'd2: query_length=4'd2;
3'd3: query_length=4'd1;
3'd4: query_length=4'd1;
default: query_length=0;
endcase end endfunction
