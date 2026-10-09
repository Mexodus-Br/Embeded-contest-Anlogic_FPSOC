`timescale 1ns/1ps
// Synchronous show-ahead FIFO; simultaneous full pop/push is supported.
// DEPTH/WIDTH are implementation parameters, not frozen product capacities.
module motion_fifo #(parameter WIDTH=16, DEPTH=2)(
    input wire clk,rst_n,flush,
    input wire in_valid, output wire in_ready, input wire [WIDTH-1:0] in_data,
    output wire out_valid, input wire out_ready, output wire [WIDTH-1:0] out_data,
    output wire [31:0] level
);
    function integer bits;
        input integer n;integer v;
        begin bits=1;v=n-1;while(v>1)begin bits=bits+1;v=v>>1;end end
    endfunction
    localparam PTR_BITS=bits(DEPTH), COUNT_BITS=bits(DEPTH+1);
    reg [WIDTH-1:0] memory[0:DEPTH-1];
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
            if(push)begin memory[wr]<=in_data;wr<=wr==DEPTH-1 ? 0 : wr+1'b1;end
            if(pop)rd<=rd==DEPTH-1 ? 0 : rd+1'b1;
            case({push,pop})2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:begin end endcase
        end
    end
    // synthesis translate_off
    initial if(DEPTH<2 || WIDTH<1)$fatal(1,"invalid FIFO parameters");
    // synthesis translate_on
endmodule
