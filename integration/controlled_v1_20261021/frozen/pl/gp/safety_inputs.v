`timescale 1ns/1ps
// Async contacts: two flops, fast assertion, independently qualified release.
module safety_inputs #(
 parameter [3:0] ACTIVE_LOW=4'hf,
 parameter [63:0] RELEASE_CYCLES=0
)(input wire clk,rst_n,input wire [3:0] contact_n,
 output wire [3:0] active,output reg [3:0] released,
 output wire qualified,output wire sampled);
 (* async_reg="true" *) reg [3:0] meta,sync;
 reg [1:0] startup;
 reg [63:0] release_age[0:3];
 assign active=sync ^ ACTIVE_LOW;
 assign sampled=startup[1];
 assign qualified=sampled && RELEASE_CYCLES!=0;
 integer i;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   // Treat unobserved inputs as asserted. Reset never creates permission.
   meta<=~ACTIVE_LOW;sync<=~ACTIVE_LOW;startup<=0;released<=0;
   for(i=0;i<4;i=i+1)release_age[i]<=0;
  end else begin
   meta<=contact_n;sync<=meta;startup<={startup[0],1'b1};
   for(i=0;i<4;i=i+1)begin
    if(active[i] || !qualified)begin release_age[i]<=0;released[i]<=0;end
    else if(release_age[i]<RELEASE_CYCLES)begin
     release_age[i]<=release_age[i]+1'b1;
     if(release_age[i]==RELEASE_CYCLES-1)released[i]<=1;
    end
   end
  end
 end
endmodule
