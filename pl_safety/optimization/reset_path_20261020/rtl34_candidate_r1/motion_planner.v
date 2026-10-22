`timescale 1ns/1ps
module motion_planner #(
    parameter [255:0] STEP_HIGH_CYCLES=0, STEP_LOW_CYCLES=0,
    parameter [255:0] DIR_SETUP_CYCLES=0, DIR_HOLD_CYCLES=0,
    parameter [255:0] EN_SETUP_CYCLES=0, EN_DISABLE_CYCLES=0,
    parameter [255:0] MAX_STEP_HZ=0,
    parameter [3:0] EN_ACTIVE_LEVEL=4'b1111
)(
 input wire clk,rst_n,cancel,
 input wire req_valid,output wire req_ready,output wire busy,
 input wire [255:0] base_position,target_position,
 input wire [3:0] axis_mask,
 input wire [63:0] duration_tick,request_session,
 input wire [31:0] request_sequence,input wire request_end,
 output wire plan_valid,input wire plan_ready,
 output wire [1196:0] plan_data,output reg error,output wire plan_pending,output wire req_available
);
// One owned record at a time: metadata is captured before arithmetic.
// Cancel invalidates every stage, including a held output, on the same edge.
localparam IDLE=0,DIFF=1,ABS=2,PAIR=3,MAXIMUM=4,BUDGET=5,INIT_DIV=6,DIVIDE=7,CHECK=8,HOLD=9;
reg [3:0] state;
wire [3:0] config_valid;
wire [63:0] lane_guard[0:3], min_period[0:3], tail_min[0:3];
genvar g;
generate for(g=0;g<4;g=g+1)begin: lanes
 localparam [63:0] H=STEP_HIGH_CYCLES[g*64+:64],L=STEP_LOW_CYCLES[g*64+:64];
 localparam [63:0] S=DIR_SETUP_CYCLES[g*64+:64],Q=DIR_HOLD_CYCLES[g*64+:64];
 localparam [63:0] E=EN_SETUP_CYCLES[g*64+:64],R=MAX_STEP_HZ[g*64+:64];
 localparam [65:0] QS={2'b0,Q}+{2'b0,S};
 localparam [65:0] QE=QS>{2'b0,E} ? QS : {2'b0,E};
 localparam [65:0] GL=(QE>{2'b0,L} ? QE : {2'b0,L})+66'd2;
 localparam [64:0] HL={1'b0,H}+{1'b0,L};
 assign config_valid[g]=H>0 && L>0 && R>0 && HL[64]==0 && GL[65:64]==0;
 assign lane_guard[g]=GL[63:0];
 assign tail_min[g]=HL[63:0]>Q ? HL[63:0] : Q;
 // Exact integer equivalence to quotient*R >= 100MHz; no runtime DSP.
 assign min_period[g]=R==0 ? 64'hffffffffffffffff : (128'd100000000+R-1)/R;
end endgenerate
reg [255:0] target_saved,base_saved,endpoint,counts;
reg [63:0] duration_saved,sid;
reg [31:0] seq;
reg [3:0] moving,positive,mask_saved;
reg last;
reg signed [64:0] differences[0:3];
reg [127:0] cycles_wide;
reg [63:0] max_pair[0:1],guard_pair[0:1];
reg [63:0] cycles,guard_cycles,master,quotient,remainder;
reg basic_ok;
reg [63:0] dividend,div_quotient;
reg [64:0] div_remainder;
reg [6:0] div_left;
wire [64:0] trial={div_remainder[63:0],dividend[63]};
// One subtract supplies both borrow and next remainder (no compare+subtract).
wire [65:0] div_difference={1'b0,trial}-{2'b0,master};
wire div_bit=!div_difference[65];
wire [64:0] rem_next=div_bit ? div_difference[64:0] : trial;
wire [63:0] quo_next={div_quotient[62:0],div_bit};
reg feasible;
integer c;
always @* begin
 feasible=quotient!=0;
 for(c=0;c<4;c=c+1)if(moving[c])
  if(quotient<tail_min[c] || quotient<min_period[c])feasible=0;
end
assign req_available=state==IDLE;
assign req_ready=req_available && !cancel;
assign busy=state!=IDLE;
assign plan_pending=state==HOLD;
assign plan_valid=plan_pending && !cancel;
assign plan_data={base_saved,endpoint,counts,positive,moving,master,guard_cycles,cycles,quotient,remainder,sid,seq,last,mask_saved};
function [63:0] maximum;
 input [63:0] a,b;begin maximum=a>b ? a : b;end
endfunction
integer i;
always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin
  state<=IDLE;error<=0;basic_ok<=0;
 end else begin
  error<=0;
  if(cancel)begin state<=IDLE;basic_ok<=0;end
  else case(state)
   IDLE:if(req_valid)state<=DIFF;
   DIFF:state<=ABS;
   ABS:state<=PAIR;
   PAIR:state<=MAXIMUM;
   MAXIMUM:state<=BUDGET;
   BUDGET:begin
    basic_ok<=duration_saved!=0 && cycles_wide[127:64]==0 &&
     (mask_saved & ~config_valid)==0 && (master==0 || cycles>guard_cycles);
    state<=INIT_DIV;
   end
   INIT_DIV:begin
    if(!basic_ok)begin error<=1;state<=IDLE;end
    else if(master==0)state<=HOLD;
    else state<=DIVIDE;
   end
   DIVIDE:if(div_left==1)state<=CHECK;
   CHECK:if(feasible)state<=HOLD;else begin error<=1;state<=IDLE;end
   HOLD:if(plan_ready)state<=IDLE;
  endcase
 end
end
// Only state/error/validity need asynchronous initialization. Each owned
// record writes every data dependency before use. Cancel discards the state;
// speculative data writes on that edge are unreachable by a valid plan.
// Keeping cancel out of these wide enables also localizes the stop network.
always @(posedge clk)begin
  case(state)
   IDLE:if(req_valid)begin
    target_saved<=target_position;base_saved<=base_position;endpoint<=base_position;
    duration_saved<=duration_tick;sid<=request_session;seq<=request_sequence;
    mask_saved<=axis_mask;last<=request_end;
   end
   DIFF:begin
    cycles_wide<={64'b0,duration_saved}*128'd100;
    for(i=0;i<4;i=i+1)begin
     differences[i]<=mask_saved[i] ?
      $signed({target_saved[i*64+63],target_saved[i*64+:64]})-
      $signed({base_saved[i*64+63],base_saved[i*64+:64]}) : 65'sd0;
     if(mask_saved[i])endpoint[i*64+:64]<=target_saved[i*64+:64];
    end
   end
   ABS:begin
    for(i=0;i<4;i=i+1)begin
     counts[i*64+:64]<=differences[i][64] ? -differences[i] : differences[i];
     moving[i]<=differences[i]!=0;positive[i]<=differences[i]!=0 && !differences[i][64];
    end
   end
   PAIR:begin
    for(i=0;i<2;i=i+1)begin
     max_pair[i]<=maximum(counts[i*128+:64],counts[i*128+64+:64]);
     guard_pair[i]<=maximum(moving[i*2] ? lane_guard[i*2] : 64'd0,
                            moving[i*2+1] ? lane_guard[i*2+1] : 64'd0);
    end
   end
   MAXIMUM:begin master<=maximum(max_pair[0],max_pair[1]);
    guard_cycles<=maximum(guard_pair[0],guard_pair[1]);cycles<=cycles_wide[63:0];end
   INIT_DIV:begin
    if(basic_ok)begin
     if(master==0)begin quotient<=0;remainder<=0;end
     else begin dividend<=cycles-guard_cycles;div_remainder<=0;div_quotient<=0;div_left<=64;end
    end
   end
   DIVIDE:begin
    dividend<={dividend[62:0],1'b0};div_remainder<=rem_next;div_quotient<=quo_next;div_left<=div_left-1'b1;
    if(div_left==1)begin quotient<=quo_next;remainder<=rem_next[63:0];end
   end
   default:begin end
  endcase
end
endmodule
