module record_fifo #(parameter integer DEPTH=8)(
 input wire clk,rst_n,push,input wire [255:0] push_data,
 input wire ready,output wire valid,output wire [255:0] data,
 output reg [31:0] dropped,output wire [31:0] level);
 localparam integer PTR_BITS=(DEPTH<=2)?1:$clog2(DEPTH);
 reg [255:0] mem[0:DEPTH-1];
 reg [PTR_BITS-1:0] wr,rd;
 reg [PTR_BITS:0] count;
 wire pop=ready && valid;
 wire accept=push && ((count<DEPTH)||pop);
 assign valid=count!=0;
 assign data=mem[rd];
 assign level=count;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin wr<=0;rd<=0;count<=0;dropped<=0;end
  else begin
   if(pop) rd<=(rd==DEPTH-1)?0:rd+1'b1;
   if(accept) begin mem[wr]<=push_data;wr<=(wr==DEPTH-1)?0:wr+1'b1;end
   case({accept,pop}) 2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:count<=count;endcase
   if(push && !accept && dropped!=32'hffffffff) dropped<=dropped+1'b1;
  end
 end
endmodule
