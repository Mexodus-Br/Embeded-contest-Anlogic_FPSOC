`timescale 1ns/1ps
// Synchronous show-ahead FIFO; simultaneous full pop/push is supported.
// DEPTH/WIDTH are implementation parameters, not frozen product capacities.
module motion_fifo #(parameter WIDTH=16, DEPTH=2, SPARE_SLOT=0, SPECULATIVE_STORAGE=0)(
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
    // A flush invalidates the queue through its original control edge.
    // With the private opt-in, a speculative write on that edge is invisible:
    // no count/pointer advances and every newly admitted slot is overwritten.
    // Avoid routing the cancellation cone to every payload memory write pin.
    wire store=SPECULATIVE_STORAGE ?
        in_valid && (count<DEPTH || (count!=0 && out_ready)) : push;
    always @(posedge clk)if(store)memory[wr]<=in_data;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin rd<=0;wr<=0;count<=0;end
        else if(flush)begin rd<=0;wr<=0;count<=0;end
        else begin
            if(push)begin wr<=wr==STORAGE_DEPTH-1 ? 0 : wr+1'b1;end
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
