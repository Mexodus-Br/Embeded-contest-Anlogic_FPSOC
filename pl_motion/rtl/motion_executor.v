`timescale 1ns/1ps
// Prepared plans commit atomically at idle or at the current duration boundary.
module motion_executor #(
    parameter [255:0] STEP_HIGH_CYCLES=0, STEP_LOW_CYCLES=0,
    parameter [255:0] DIR_SETUP_CYCLES=0, DIR_HOLD_CYCLES=0,
    parameter [255:0] EN_SETUP_CYCLES=0, EN_DISABLE_CYCLES=0,
    parameter [255:0] MAX_STEP_HZ=0,
    parameter [3:0] EN_ACTIVE_LEVEL=4'b1111
)(
 input wire clk,rst_n,
 input wire rebase_req,input wire [3:0] rebase_mask,input wire [255:0] rebase_position,
 input wire enable_req,input wire [3:0] enable_mask,
 input wire disable_req,input wire [3:0] disable_mask,
 input wire stop_req,input wire [3:0] fault,input wire clear_fault,
 input wire plan_valid,output wire plan_ready,input wire [1196:0] plan_data,
 output reg [3:0] step,dir,output wire [3:0] en,
 output wire [255:0] position,output reg [3:0] position_valid,
 output reg [3:0] fault_latched,output wire [3:0] config_valid,enabled_state,enable_ready_state,
 output wire busy,boundary,pulse_safe,
 output reg point_start,done,stopped,plan_rejected,rebase_accepted,
 output reg [3:0] pulse_event,output reg slot_event,output reg [63:0] slot_id
);
    localparam IDLE=0,RUN=3,DRAIN=4;
    reg [2:0] state;
    reg [3:0] enabled, disabling, moving, positive;
    reg signed [63:0] pos[0:3];
    reg [63:0] count[0:3], accumulator[0:3];
    reg [63:0] high_left[0:3], edge_age[0:3], low_age[0:3];
    reg [63:0] dir_age[0:3], en_age[0:3], off_left[0:3];
    wire [63:0] min_period[0:3];
    wire [63:0] h[0:3], l[0:3], s[0:3], q[0:3], e[0:3], off[0:3], rate[0:3];
    genvar g;
    generate for(g=0;g<4;g=g+1)begin: lanes
        assign h[g]=STEP_HIGH_CYCLES[g*64+:64];
        assign l[g]=STEP_LOW_CYCLES[g*64+:64];
        assign s[g]=DIR_SETUP_CYCLES[g*64+:64];
        assign q[g]=DIR_HOLD_CYCLES[g*64+:64];
        assign e[g]=EN_SETUP_CYCLES[g*64+:64];
        assign off[g]=EN_DISABLE_CYCLES[g*64+:64];
        assign rate[g]=MAX_STEP_HZ[g*64+:64];
        localparam [63:0] R=MAX_STEP_HZ[g*64+:64];
        // Exact elaboration-time integer threshold; retain same-cycle checks.
        assign min_period[g]=R==0 ? 64'hffffffffffffffff : (128'd100000000+R-1)/R;
        assign position[g*64+:64]=pos[g];
        assign en[g]=enabled[g] ? EN_ACTIVE_LEVEL[g] : !EN_ACTIVE_LEVEL[g];
        assign enable_ready_state[g]=enabled[g] && reached(en_age[g],e[g]);
        assign config_valid[g]=h[g]>0 && l[g]>0 && rate[g]>0 &&
            ({1'b0,h[g]}+{1'b0,l[g]})<=65'h0ffffffffffffffff &&
            ({2'b0,q[g]}+{2'b0,s[g]}+66'd2)<=66'h0ffffffffffffffff &&
            e[g]<=64'hfffffffffffffffd && l[g]<=64'hfffffffffffffffd;
    end endgenerate
    wire safety=stop_req || (|fault) || disable_req;
    assign busy=state!=IDLE || (|disabling);
    assign enabled_state=enabled;
    assign plan_ready=(state==IDLE || boundary) && !(|disabling) && !(|fault_latched) && !safety;
    function [63:0] age_next;
        input [63:0] age;
        begin age_next=(&age) ? age : age+64'd1; end
    endfunction
    // Event resets age=0. Before the next edge, age+1 is elapsed cycles.
    function reached;
        input [63:0] age, minimum;
        begin reached=(minimum==0) || age>=minimum-64'd1; end
    endfunction
    reg all_safe;
    integer a;
    always @* begin
        all_safe=1;
        for(a=0;a<4;a=a+1)
            if(step[a] || !reached(low_age[a],l[a]) ||
                         !reached(edge_age[a],q[a])) all_safe=0;
    end

wire [255:0] plan_base,plan_endpoint,plan_counts;
wire [3:0] plan_positive,plan_moving,plan_mask;
wire [63:0] plan_master,plan_guard,plan_cycles,plan_quotient,plan_remainder,plan_session;
wire [31:0] plan_sequence;wire plan_end;
assign {plan_base,plan_endpoint,plan_counts,plan_positive,plan_moving,plan_master,plan_guard,plan_cycles,plan_quotient,plan_remainder,plan_session,plan_sequence,plan_end,plan_mask}=plan_data;
wire commit_ok=plan_base==position && all_safe &&
 (plan_mask & ~enabled)==0 && (plan_mask & ~position_valid)==0 &&
 (plan_mask & ~config_valid)==0 && plan_cycles!=0;
reg [63:0] cycles,master,quotient,remainder;
    // elapsed names the cycle being executed, starting at 1 after commit.
    reg [63:0] elapsed, next_slot, slot_index, time_remainder;
    assign boundary=state==RUN && elapsed==cycles;
    assign pulse_safe=all_safe;
    wire slot_due=state==RUN && master!=0 && slot_index<master &&
                  elapsed==next_slot;
    reg [3:0] emit;
    reg emission_ok;
    reg [64:0] sum_lane;

    integer d;
    always @* begin
        emit=0;emission_ok=1;sum_lane=0;
        for(d=0;d<4;d=d+1)begin
            sum_lane={1'b0,accumulator[d]}+{1'b0,count[d]};
            if(moving[d] && sum_lane>={1'b0,master})begin
                emit[d]=1;
                if(step[d] || !enabled[d] || !position_valid[d] || dir[d]!=positive[d] ||
                   !reached(low_age[d],l[d]) || !reached(dir_age[d],s[d]) ||
                   !reached(en_age[d],e[d]) || !reached(edge_age[d],min_period[d]) ||
                   (positive[d] ? pos[d]==64'sh7fffffffffffffff : pos[d]==64'sh8000000000000000))emission_ok=0;
            end
        end
    end
reg [64:0] sum_time,sum_axis;
integer i;
always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin
  state<=IDLE;enabled<=0;disabling<=0;step<=0;dir<=15;position_valid<=0;fault_latched<=0;
  moving<=0;positive<=15;cycles<=0;master<=0;quotient<=0;remainder<=0;elapsed<=0;
  next_slot<=0;slot_index<=0;time_remainder<=0;slot_id<=0;
  point_start<=0;done<=0;stopped<=0;plan_rejected<=0;rebase_accepted<=0;pulse_event<=0;slot_event<=0;
  for(i=0;i<4;i=i+1)begin pos[i]<=0;count[i]<=0;accumulator[i]<=0;high_left[i]<=0;edge_age[i]<=0;low_age[i]<=0;dir_age[i]<=0;en_age[i]<=0;off_left[i]<=0;end
 end else begin
  point_start<=0;done<=0;stopped<=0;plan_rejected<=0;rebase_accepted<=0;pulse_event<=0;slot_event<=0;
  fault_latched<=fault_latched|fault;
  if(clear_fault && !busy && !safety)fault_latched<=0;
  for(i=0;i<4;i=i+1)begin
   edge_age[i]<=age_next(edge_age[i]);dir_age[i]<=age_next(dir_age[i]);
   if(!step[i])low_age[i]<=age_next(low_age[i]);if(enabled[i])en_age[i]<=age_next(en_age[i]);
   if(step[i])begin if(high_left[i]==1)begin step[i]<=0;low_age[i]<=0;high_left[i]<=0;end else high_left[i]<=high_left[i]-64'd1;end
   if(disabling[i] && state==IDLE && all_safe && !disable_req)begin
    if(off_left[i]==0)begin enabled[i]<=0;disabling[i]<=0;end else off_left[i]<=off_left[i]-64'd1;
   end
  end
  if(safety)begin
   if(state!=DRAIN && (state!=IDLE || stop_req || disable_req))state<=DRAIN;
   if(disable_req)begin position_valid<=position_valid & ~disable_mask;disabling<=disabling|disable_mask;
    for(i=0;i<4;i=i+1)if(disable_mask[i])off_left[i]<=off[i];end
  end else begin
   if(rebase_req && enable_req)plan_rejected<=1;
   else if(rebase_req)begin
    if(!busy && !(|fault_latched) && rebase_mask!=0 && (rebase_mask & enabled)==0)begin
     for(i=0;i<4;i=i+1)if(rebase_mask[i])pos[i]<=$signed(rebase_position[i*64+:64]);
     position_valid<=position_valid|rebase_mask;rebase_accepted<=1;
    end else plan_rejected<=1;
   end else if(enable_req)begin
    if(!busy && !(|fault_latched) && enable_mask!=0 && (enable_mask & ~position_valid)==0 && (enable_mask & ~config_valid)==0)begin
     enabled<=enabled|enable_mask;for(i=0;i<4;i=i+1)if(enable_mask[i] && !enabled[i])en_age[i]<=0;
    end else plan_rejected<=1;
   end
   if(state==RUN)begin
    elapsed<=elapsed+64'd1;
    if(slot_due)begin
     if(!emission_ok)begin state<=DRAIN;fault_latched<=15;plan_rejected<=1;end
     else begin
      slot_event<=1;slot_id<=slot_index;slot_index<=slot_index+64'd1;
      sum_time={1'b0,time_remainder}+{1'b0,remainder};
      if(sum_time>={1'b0,master})begin time_remainder<=sum_time-{1'b0,master};next_slot<=next_slot+quotient+64'd1;end
      else begin time_remainder<=sum_time[63:0];next_slot<=next_slot+quotient;end
      for(i=0;i<4;i=i+1)if(moving[i])begin
       sum_axis={1'b0,accumulator[i]}+{1'b0,count[i]};accumulator[i]<=emit[i] ? sum_axis-{1'b0,master} : sum_axis[63:0];
       if(emit[i])begin step[i]<=1;pulse_event[i]<=1;edge_age[i]<=0;high_left[i]<=h[i];pos[i]<=pos[i]+(positive[i] ? 64'sd1 : -64'sd1);end
      end
     end
    end
    if(boundary)begin
     if(all_safe && (master==0 || slot_index==master))begin state<=IDLE;done<=1;end
     else begin state<=DRAIN;fault_latched<=15;plan_rejected<=1;end
    end
   end
   // This overrides normal boundary IDLE on the SAME clock, without a gap.
   if(plan_valid && plan_ready)begin
    if(!commit_ok)begin state<=DRAIN;plan_rejected<=1;end
    else begin
     state<=RUN;cycles<=plan_cycles;master<=plan_master;quotient<=plan_quotient;remainder<=plan_remainder;
     moving<=plan_moving;positive<=plan_positive;elapsed<=1;next_slot<=plan_guard;slot_index<=0;time_remainder<=0;point_start<=1;
     for(i=0;i<4;i=i+1)begin
      count[i]<=plan_counts[i*64+:64];accumulator[i]<=plan_master-plan_counts[i*64+:64];
      if(plan_moving[i] && dir[i]!=plan_positive[i])begin dir[i]<=plan_positive[i];dir_age[i]<=0;end
     end
    end
   end
  end
  if(state==DRAIN && all_safe)begin state<=IDLE;stopped<=1;end
 end
end
endmodule
