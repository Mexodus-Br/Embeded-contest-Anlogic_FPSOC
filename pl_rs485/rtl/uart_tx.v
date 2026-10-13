// 8N1, LSB first. done follows the FULL final stop bit, never data bit 7.
module uart_tx #(parameter integer BIT_CYCLES=868)(
 input wire clk,rst_n,start,input wire [7:0] data,
 output reg tx,busy,done);
 reg [31:0] timer;
 reg [3:0] bit_index;
 reg [9:0] frame;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin tx<=1;busy<=0;done<=0;timer<=0;bit_index<=0;frame<=10'h3ff;end
  else begin
   done<=0;
   if(!busy) begin
    tx<=1;
    if(start) begin frame<={1'b1,data,1'b0};tx<=0;busy<=1;bit_index<=0;timer<=BIT_CYCLES-1;end
   end else if(timer!=0) timer<=timer-1;
   else if(bit_index==9) begin tx<=1;busy<=0;done<=1;end
   else begin bit_index<=bit_index+1;tx<=frame[bit_index+1];timer<=BIT_CYCLES-1;end
  end
 end
endmodule
