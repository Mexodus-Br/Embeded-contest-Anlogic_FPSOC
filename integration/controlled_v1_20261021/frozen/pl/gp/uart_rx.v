// Input synchronizer remains active while decoder is disabled.
// Single center samples, 8N1; false starts filtered at half-bit.
module uart_rx #(parameter integer BIT_CYCLES=868)(
 input wire clk,rst_n,enable,rx,
 output wire line_idle,output reg [7:0] data,output reg valid,framing);
 (* async_reg="true" *) reg meta,sync;
 reg prev;
 reg [1:0] state;
 reg [31:0] timer;
 reg [2:0] index;
 reg [7:0] shift;
 assign line_idle=sync;
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin meta<=1;sync<=1;end
  else begin meta<=rx;sync<=meta;end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin prev<=1;state<=0;timer<=0;index<=0;shift<=0;data<=0;valid<=0;framing<=0;end
  else begin
   prev<=sync;valid<=0;framing<=0;
   if(!enable) state<=0;
   else case(state)
    0: if(prev && !sync) begin state<=1;timer<=BIT_CYCLES/2-1;end
    1: if(timer!=0) timer<=timer-1;
       else if(sync) state<=0;
       else begin state<=2;index<=0;timer<=BIT_CYCLES-1;end
    2: if(timer!=0) timer<=timer-1;
       else begin shift[index]<=sync;timer<=BIT_CYCLES-1;
        if(index==7) state<=3;else index<=index+1;end
    3: if(timer!=0) timer<=timer-1;
       else begin state<=0;data<=shift;if(sync) valid<=1;else framing<=1;end
   endcase
  end
 end
endmodule
