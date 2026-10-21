`timescale 1ns/1ps
// Same-clock elastic queue. Reset cancels every stored beat, including TLAST.
module axis_loop_fifo #(parameter DEPTH=16)(
 input wire clk,rst_n,
 input wire [63:0] s_data,input wire [7:0] s_keep,
 input wire s_last,s_valid,output wire s_ready,
 input wire [3:0] s_user,input wire [4:0] s_id,s_dest,
 output wire [63:0] m_data,output wire [7:0] m_keep,
 output wire m_last,m_valid,input wire m_ready,
 output wire [3:0] m_user,output wire [4:0] m_id,m_dest,
 output wire [31:0] occupancy
);
 function integer bits; input integer n; integer k;
 begin bits=1; for(k=n-1;k>1;k=k>>1) bits=bits+1; end endfunction
 localparam PW=bits(DEPTH), CW=bits(DEPTH+1);
 reg [86:0] mem[0:DEPTH-1];
 reg [PW-1:0] rd,wr; reg [CW-1:0] count;
 assign occupancy=count;
 assign m_valid=rst_n && count!=0;
 // Registered occupancy isolates downstream READY from upstream READY.
 assign s_ready=rst_n && count<DEPTH;
 assign {m_dest,m_id,m_user,m_last,m_keep,m_data}=mem[rd];
 wire push=s_valid && s_ready, pop=m_valid && m_ready;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin rd<=0;wr<=0;count<=0;end
  else begin
   if(push) begin mem[wr]<={s_dest,s_id,s_user,s_last,s_keep,s_data};wr<=wr==DEPTH-1 ? 0 : wr+1'b1;end
   if(pop) rd<=rd==DEPTH-1 ? 0 : rd+1'b1;
   case({push,pop}) 2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:count<=count;endcase
  end
 end
endmodule
