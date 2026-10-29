`timescale 1ns/1ps
// Synchronous show-ahead FIFO; simultaneous full pop/push is supported.
// DEPTH/WIDTH are implementation parameters, not frozen product capacities.
module motion_fifo #(parameter WIDTH=16, DEPTH=2, SPARE_SLOT=0)(
    input wire clk,rst_n,flush,
    input wire in_valid, output wire in_ready, input wire [WIDTH-1:0] in_data,
    output wire out_valid, input wire out_ready, output wire [WIDTH-1:0] out_data,
    output wire [31:0] level
);
    function integer bits;
        input integer n;integer v;
        begin bits=1;v=n-1;while(v>1)begin bits=bits+1;v=v>>1;end end
    endfunction
    // Keep the public capacity at DEPTH. An optional physical spare address
    // prevents a full pop/push from reading and writing the same RAM word.
    // This does not depend on the vendor RAM's collision/write-through mode.
    localparam STORAGE_DEPTH=DEPTH+SPARE_SLOT;
    localparam PTR_BITS=bits(STORAGE_DEPTH), COUNT_BITS=bits(DEPTH+1);
    reg [WIDTH-1:0] memory[0:STORAGE_DEPTH-1];
    reg [PTR_BITS-1:0] rd,wr;
    reg [COUNT_BITS-1:0] count;
    assign out_valid=rst_n && !flush && count!=0;
    wire pop=out_valid && out_ready;
    assign in_ready=rst_n && !flush && (count<DEPTH || pop);
    wire push=in_valid && in_ready;
    assign out_data=memory[rd];
    assign level=count;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin rd<=0;wr<=0;count<=0;end
        else if(flush)begin rd<=0;wr<=0;count<=0;end
        else begin
            if(push)begin memory[wr]<=in_data;wr<=wr==STORAGE_DEPTH-1 ? 0 : wr+1'b1;end
            if(pop)rd<=rd==STORAGE_DEPTH-1 ? 0 : rd+1'b1;
            case({push,pop})2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:begin end endcase
        end
    end
    // synthesis translate_off
    initial if(DEPTH<2 || WIDTH<1 || SPARE_SLOT<0 || SPARE_SLOT>1)$fatal(1,"invalid FIFO parameters");
    always @(posedge clk)if(rst_n && SPARE_SLOT)begin
        if(count>DEPTH || rd>=STORAGE_DEPTH || wr>=STORAGE_DEPTH)$fatal(1,"FIFO storage bounds");
        if((wr>=rd ? wr-rd:wr+STORAGE_DEPTH-rd)!=count)$fatal(1,"FIFO spare distance invariant");
        if(push && pop && wr==rd)$fatal(1,"FIFO RAM collision is unreachable");
    end
    // synthesis translate_on
endmodule

// Private prepared-plan FIFO. Public ready/valid/level retain original cycles.
// flush invalidates the logical epoch on its original edge; its registered
// marker resets the PHYSICAL pointer basis on the following edge. Speculative
// storage activity on a flush edge is unreachable by a valid consumer.
// The spare address preserves old-head data for every valid full pop/push.
module motion_plan_fifo #(parameter WIDTH=1197,DEPTH=8)(
 input wire clk,rst_n,flush,in_valid,
 output wire in_ready,input wire [WIDTH-1:0] in_data,
 output wire out_valid,input wire out_ready,output wire [WIDTH-1:0] out_data,
 output wire [31:0] level,input wire storage_out_ready,output wire storage_valid
);
 localparam STORAGE_DEPTH=DEPTH+1;
 localparam PB=$clog2(STORAGE_DEPTH),CB=$clog2(DEPTH+1);
 reg [WIDTH-1:0] memory[0:STORAGE_DEPTH-1];
 reg [PB-1:0] rd,wr;reg [CB-1:0] count;reg invalidate_q;
 wire [PB-1:0] read_pointer=invalidate_q ? {PB{1'b0}}:rd;
 wire [PB-1:0] write_pointer=invalidate_q ? {PB{1'b0}}:wr;
 wire [CB-1:0] owned_count=invalidate_q ? {CB{1'b0}}:count;
 assign level=owned_count;
 assign storage_valid=rst_n && owned_count!=0;
 assign out_valid=storage_valid && !flush;
 wire public_pop=out_valid && out_ready;
 assign in_ready=rst_n && !flush && (owned_count<DEPTH || public_pop);
 assign out_data=memory[read_pointer];
 wire store_pop=owned_count!=0 && storage_out_ready;
 wire store_push=in_valid && (owned_count<DEPTH || store_pop);
 always @(posedge clk)if(store_push)memory[write_pointer]<=in_data;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin rd<=0;wr<=0;count<=0;invalidate_q<=0;end
  else begin
   invalidate_q<=flush;
   wr<=store_push ? (write_pointer==STORAGE_DEPTH-1 ? 0:write_pointer+1'b1):write_pointer;
   rd<=store_pop ? (read_pointer==STORAGE_DEPTH-1 ? 0:read_pointer+1'b1):read_pointer;
   case({store_push,store_pop})
    2'b10:count<=owned_count+1'b1;
    2'b01:count<=owned_count-1'b1;
    default:count<=owned_count;
   endcase
  end
 end
 // synthesis translate_off
 initial if(DEPTH<2 || WIDTH<1)$fatal(1,"invalid prepared FIFO parameters");
 always @(posedge clk)if(rst_n)begin
  if(owned_count>DEPTH || rd>=STORAGE_DEPTH || wr>=STORAGE_DEPTH)$fatal(1,"prepared FIFO bounds");
  if((wr>=rd ? wr-rd:wr+STORAGE_DEPTH-rd)!=count)$fatal(1,"physical prepared FIFO distance invariant");
  if(store_pop && store_push && write_pointer==read_pointer)$fatal(1,"prepared RAM collision");
  if(!flush && storage_out_ready !== out_ready)$fatal(1,"prepared storage/public readiness cofactor");
 end
 // synthesis translate_on
endmodule
