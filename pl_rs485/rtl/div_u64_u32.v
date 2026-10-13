// Bounded restoring divider: exactly 64 iterations, no combinational divide.
module div_u64_u32(input wire clk,rst_n,start,
 input wire [63:0] numerator,input wire [31:0] denominator,
 output reg busy,done,output reg [63:0] quotient,output reg [31:0] remainder);
 reg [63:0] bits;
 reg [31:0] divisor,rem;
 reg [6:0] count;
 wire [32:0] trial={rem,bits[63]};
 wire take=(trial>={1'b0,divisor});
 wire [32:0] reduced=trial-{1'b0,divisor};
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin busy<=0;done<=0;quotient<=0;remainder<=0;bits<=0;divisor<=1;rem<=0;count<=0;end
  else begin
   done<=0;
   if(start && !busy) begin busy<=1;bits<=numerator;divisor<=denominator;rem<=0;quotient<=0;count<=0;end
   else if(busy) begin
    bits<={bits[62:0],1'b0};rem<=take?reduced[31:0]:trial[31:0];quotient<={quotient[62:0],take};
    if(count==63) begin busy<=0;done<=1;remainder<=take?reduced[31:0]:trial[31:0];end
    else count<=count+1'b1;
   end
  end
 end
endmodule
