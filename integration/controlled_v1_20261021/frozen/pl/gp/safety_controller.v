`timescale 1ns/1ps
`include "safety_defs.vh"
module safety_controller #(
 parameter CONFIG_APPROVED=0,INTERLOCK_SUPPORT=0,SPLIT_RUN_PERMIT=0,
 parameter [2:0] HOME_DIRECTION=0,
 parameter [191:0] SEARCH_PERIOD=0,PULL_PERIOD=0,PRE_PERIOD=0,
 parameter [191:0] REFERENCE_POSITION=0,PULL_DISTANCE=0,PRE_DISTANCE=0,
 parameter [191:0] SEARCH_MAX_STEPS=0,PULL_MAX_STEPS=0,PRE_MAX_STEPS=0,
 parameter [63:0] SEARCH_MAX_US=0,PULL_MAX_US=0,PRE_MAX_US=0
)(input wire clk,rst_n,input wire [63:0] time_us,
 input wire qualified,input wire [3:0] active,released,
 input wire home_request,clear_request,stop_request,
 input wire idle,pulse_safe,external_abort,input wire [2:0] executor_fault,
 input wire [3:0] position_valid,pulse_event,config_valid,
 output wire config_ok,normal_inhibit,home_owner,
 output wire home_enable,home_reference,home_complete,
 output reg [2:0] home_run,output wire [2:0] home_direction,
 output wire [191:0] home_period,home_reference_position,
 output wire stop_motion,disable_motion,output wire [3:0] invalidate,
 output reg clear_executor,
 output reg [3:0] state,output reg [31:0] causes,first_cause,
 output reg [63:0] first_time,event_sequence,home_start_time,home_done_time,
 output reg [2:0] hit_mask,released_mask,done_mask,
 output wire [191:0] travel,
 output reg accepted,rejected,home_done,home_cancelled,
 output wire request_ok,clear_ok,
 input wire interlock_run_permit,interlock_permit,interlock_detect,interlock_disable,interlock_clear_ok,
 input wire [31:0] interlock_causes
);
 localparam NEED=`SAF_STATES_NEED,PRE=`SAF_STATES_PRE,SEARCH=`SAF_STATES_SEARCH,SEARCH_DRAIN=`SAF_STATES_SEARCH_DRAIN,REF=`SAF_STATES_REF,PULL=`SAF_STATES_PULL,FINISH=`SAF_STATES_FINISH,READY=`SAF_STATES_READY,DRAIN=`SAF_STATES_DRAIN,FAULT=`SAF_STATES_FAULT;
 localparam [31:0] ESTOP=`SAF_CAUSES_ESTOP,PRE_FAIL=`SAF_CAUSES_PRE_FAIL,SEARCH_FAIL=`SAF_CAUSES_SEARCH_FAIL,
  PULL_FAIL=`SAF_CAUSES_PULL_FAIL,RECONTACT=`SAF_CAUSES_RECONTACT,EXEC_FAIL=`SAF_CAUSES_EXEC_FAIL;
 reg [63:0] count[0:2];reg [63:0] phase_time;
 // (now-start) mod 2^64 >= M, without a serial subtract/compare chain.
 // Retain start to distinguish the two arcs around the unsigned wrap.
 reg [63:0] phase_deadline;reg phase_wrap;
 wire before_phase=time_us<phase_time;
 wire timeout_reached=phase_wrap ? (time_us>=phase_deadline && before_phase) :
                                    (time_us>=phase_deadline || before_phase);
 // Boundary flags name the current registered count, not a delayed sample.
 // For T>0: count+pulse >= T iff at_T || (pulse && before_T).
 // Update before_T from count==T-2 while the counter increments; there is
 // no increment carry chain in the same-cycle HOME run/failure decision.
 reg [2:0] search_at,search_before,pre_at,pre_before,pull_at,pull_before,count_full;
 reg [2:0] pre_mask;
 reg config_parameters;
 integer c;
 always @*begin
  config_parameters=(&config_valid[2:0]) && CONFIG_APPROVED && SEARCH_MAX_US>0 && PULL_MAX_US>0 && PRE_MAX_US>0 &&
   !SEARCH_MAX_US[63] && !PULL_MAX_US[63] && !PRE_MAX_US[63];
  for(c=0;c<3;c=c+1)begin
   if(SEARCH_PERIOD[c*64+:64]==0 || PULL_PERIOD[c*64+:64]==0 || PRE_PERIOD[c*64+:64]==0 ||
      PULL_DISTANCE[c*64+:64]==0 || PRE_DISTANCE[c*64+:64]==0 ||
      SEARCH_MAX_STEPS[c*64+:64]==0 || PULL_MAX_STEPS[c*64+:64]<PULL_DISTANCE[c*64+:64] ||
      PRE_MAX_STEPS[c*64+:64]<PRE_DISTANCE[c*64+:64])config_parameters=0;
  end
 end
 assign config_ok=config_parameters && (&config_valid[2:0]);
 // SAF2 caches the ownership decode alongside state, not one clock after it.
 // Every ownership-changing state assignment below updates the same FF; the
 // final DRAIN completion retains the original last-assignment priority.
 reg home_owner_q;
 assign home_owner=INTERLOCK_SUPPORT ? home_owner_q : (state>=PRE && state<=FINISH || state==DRAIN);
 wire in_motion=state==PRE || state==SEARCH || state==PULL;
 wire estop=qualified && active[3];
 wire ordinary_limit=qualified && (|active[2:0]) && !home_owner && (|position_valid[2:0]);
 wire [31:0] limit_cause={29'd0,active[2:0]};
 reg [31:0] failure;
 reg [2:0] reached_target;
 integer a;
 always @*begin
  failure=0;home_run=0;reached_target=0;
  for(a=0;a<3;a=a+1)begin
   if(state==SEARCH)begin
    if(!hit_mask[a] && !active[a])begin
     if((search_at[a] || (pulse_event[a] && search_before[a])))failure=failure|SEARCH_FAIL;
     else home_run[a]=1;
    end
   end else if(state==PRE || state==PULL)begin
    reached_target[a]=(state==PRE && !pre_mask[a]) ||
      (state==PRE ? (pre_at[a] || (pulse_event[a] && pre_before[a])) : (pull_at[a] || (pulse_event[a] && pull_before[a])));
    if(!reached_target[a])home_run[a]=1;
    else if(active[a] && (state==PULL || pre_mask[a]))failure=failure|(state==PRE ? PRE_FAIL : PULL_FAIL);
    if(released_mask[a] && active[a])failure=failure|RECONTACT;
   end
   if((count_full[a] && pulse_event[a]))failure=failure|EXEC_FAIL;
  end
  if(state==FINISH && (|active[2:0]))failure=failure|RECONTACT;
  if(state==SEARCH && timeout_reached)failure=failure|SEARCH_FAIL;
  if(state==PRE && timeout_reached)failure=failure|PRE_FAIL;
  if(state==PULL && timeout_reached)failure=failure|PULL_FAIL;
  if(state!=DRAIN && state!=FAULT && !clear_executor && (|executor_fault))failure=failure|EXEC_FAIL;
  if(!config_ok || estop || stop_request || external_abort || (|failure) || (|causes) ||
    (INTERLOCK_SUPPORT && (!(SPLIT_RUN_PERMIT ? interlock_run_permit:interlock_permit) || interlock_detect)))home_run=0;
 end
 wire [31:0] new_causes=(estop ? ESTOP:0) | (ordinary_limit ? limit_cause:0) | failure |
   (INTERLOCK_SUPPORT ? interlock_causes:32'd0);
 wire abort_now=estop || ordinary_limit || (|failure) || stop_request || external_abort ||
   (INTERLOCK_SUPPORT && interlock_detect);
 assign request_ok=config_ok && qualified && released[3] && !estop && idle && pulse_safe &&
  !(|causes) && (state==NEED || state==READY) && !abort_now && (!INTERLOCK_SUPPORT || interlock_permit);
 // Closed limit is allowed here: clearing cannot authorize ordinary motion;
 // only the bounded HOME pre-clear path can subsequently move away.
 assign clear_ok=qualified && released[3] && !estop && idle && pulse_safe &&
  !stop_request && !external_abort && (!INTERLOCK_SUPPORT || interlock_clear_ok);
 assign home_enable=home_request && request_ok;
 assign home_reference=state==REF && !abort_now && !(|causes);
 assign home_complete=state==FINISH && pulse_safe && (&released[2:0]) && !(|active[2:0]) && !abort_now && !(|causes);
 assign home_direction=state==SEARCH ? HOME_DIRECTION : ~HOME_DIRECTION;
 assign home_period=state==SEARCH ? SEARCH_PERIOD : state==PRE ? PRE_PERIOD : PULL_PERIOD;
 assign home_reference_position=REFERENCE_POSITION;
 assign normal_inhibit=!config_ok || state!=READY || home_request || estop || ordinary_limit || (|causes) ||
   (INTERLOCK_SUPPORT && !interlock_permit);
 assign stop_motion=abort_now;
 assign disable_motion=(estop && !causes[3]) || (INTERLOCK_SUPPORT && interlock_disable);
 assign invalidate=(home_enable || estop || ordinary_limit || (home_owner && (abort_now || state==DRAIN)) ||
   (INTERLOCK_SUPPORT && interlock_detect)) ? 4'b0111 : 4'd0;
 genvar g;generate for(g=0;g<3;g=g+1)begin: travels
  assign travel[g*64+:64]=count[g];
 end endgenerate
 integer i;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   state<=NEED;home_owner_q<=0;causes<=0;first_cause<=0;first_time<=0;event_sequence<=0;
   hit_mask<=0;released_mask<=0;done_mask<=0;pre_mask<=0;phase_time<=0;phase_deadline<=0;phase_wrap<=0;
   clear_executor<=0;accepted<=0;rejected<=0;home_done<=0;home_cancelled<=0;
   home_start_time<=0;home_done_time<=0;
   for(i=0;i<3;i=i+1)begin
    count[i]<=0;count_full[i]<=0;
    search_at[i]<=SEARCH_MAX_STEPS[i*64+:64]==0;
    search_before[i]<=SEARCH_MAX_STEPS[i*64+:64]==1;
    pre_at[i]<=PRE_DISTANCE[i*64+:64]==0;pre_before[i]<=PRE_DISTANCE[i*64+:64]==1;
    pull_at[i]<=PULL_DISTANCE[i*64+:64]==0;pull_before[i]<=PULL_DISTANCE[i*64+:64]==1;
   end
  end else begin
   accepted<=0;rejected<=0;home_done<=0;home_cancelled<=0;clear_executor<=0;
   for(i=0;i<3;i=i+1)if(in_motion && pulse_event[i])begin
    if(!count_full[i])begin
     count[i]<=count[i]+1'b1;
     count_full[i]<=count[i]==64'hfffffffffffffffe;
     search_at[i]<=search_at[i] || search_before[i];
     pre_at[i]<=pre_at[i] || pre_before[i];pull_at[i]<=pull_at[i] || pull_before[i];
     search_before[i]<=SEARCH_MAX_STEPS[i*64+:64]>1 && count[i]==SEARCH_MAX_STEPS[i*64+:64]-64'd2;
     pre_before[i]<=PRE_DISTANCE[i*64+:64]>1 && count[i]==PRE_DISTANCE[i*64+:64]-64'd2;
     pull_before[i]<=PULL_DISTANCE[i*64+:64]>1 && count[i]==PULL_DISTANCE[i*64+:64]-64'd2;
    end
   end
   if(in_motion)released_mask<=released_mask|released[2:0];
   if(state==SEARCH)hit_mask<=hit_mask|active[2:0];
   if(|new_causes)begin
    causes<=causes|new_causes;
    if(causes==0)begin
     first_cause<=new_causes[3] ? ESTOP : !INTERLOCK_SUPPORT ? new_causes :
       |new_causes[2:0] ? (new_causes & 32'h7) : |new_causes[11:9] ? (new_causes & 32'he00) :
       |new_causes[14:12] ? (new_causes & 32'h7000) : new_causes[15] ? 32'h8000:new_causes;
     first_time<=time_us;
    end
    if((new_causes & ~causes)!=0)event_sequence<=event_sequence+1'b1;
   end
   if(abort_now)begin
    if(home_owner && state!=DRAIN)home_cancelled<=1;
    if(home_owner || ordinary_limit || (estop && !causes[3]) ||
      (INTERLOCK_SUPPORT && interlock_disable))begin state<=DRAIN;home_owner_q<=1;end
    if(home_request || clear_request)rejected<=1;
   end else if(home_request)begin
    if(request_ok)begin
     state<=PRE;home_owner_q<=1;pre_mask<=active[2:0];hit_mask<=0;released_mask<=0;done_mask<=0;
     phase_time<=time_us;{phase_wrap,phase_deadline}<={1'b0,time_us}+{1'b0,PRE_MAX_US};home_start_time<=time_us;accepted<=1;
     for(i=0;i<3;i=i+1)begin
    count[i]<=0;count_full[i]<=0;
    search_at[i]<=SEARCH_MAX_STEPS[i*64+:64]==0;
    search_before[i]<=SEARCH_MAX_STEPS[i*64+:64]==1;
    pre_at[i]<=PRE_DISTANCE[i*64+:64]==0;pre_before[i]<=PRE_DISTANCE[i*64+:64]==1;
    pull_at[i]<=PULL_DISTANCE[i*64+:64]==0;pull_before[i]<=PULL_DISTANCE[i*64+:64]==1;
   end
    end else rejected<=1;
   end else if(clear_request)begin
    if(clear_ok)begin
     causes<=0;first_cause<=0;first_time<=0;state<=NEED;home_owner_q<=0;clear_executor<=1;accepted<=1;
    end else rejected<=1;
   end else case(state)
    PRE:if((&reached_target) && (&released[2:0]) && pulse_safe)begin
     state<=SEARCH;phase_time<=time_us;{phase_wrap,phase_deadline}<={1'b0,time_us}+{1'b0,SEARCH_MAX_US};released_mask<=0;
     for(i=0;i<3;i=i+1)begin
    count[i]<=0;count_full[i]<=0;
    search_at[i]<=SEARCH_MAX_STEPS[i*64+:64]==0;
    search_before[i]<=SEARCH_MAX_STEPS[i*64+:64]==1;
    pre_at[i]<=PRE_DISTANCE[i*64+:64]==0;pre_before[i]<=PRE_DISTANCE[i*64+:64]==1;
    pull_at[i]<=PULL_DISTANCE[i*64+:64]==0;pull_before[i]<=PULL_DISTANCE[i*64+:64]==1;
   end
    end
    SEARCH:if(&(hit_mask|active[2:0]))state<=SEARCH_DRAIN;
    SEARCH_DRAIN:if(pulse_safe)state<=REF;
    REF:begin
     state<=PULL;phase_time<=time_us;{phase_wrap,phase_deadline}<={1'b0,time_us}+{1'b0,PULL_MAX_US};released_mask<=0;
     for(i=0;i<3;i=i+1)begin
    count[i]<=0;count_full[i]<=0;
    search_at[i]<=SEARCH_MAX_STEPS[i*64+:64]==0;
    search_before[i]<=SEARCH_MAX_STEPS[i*64+:64]==1;
    pre_at[i]<=PRE_DISTANCE[i*64+:64]==0;pre_before[i]<=PRE_DISTANCE[i*64+:64]==1;
    pull_at[i]<=PULL_DISTANCE[i*64+:64]==0;pull_before[i]<=PULL_DISTANCE[i*64+:64]==1;
   end
    end
    PULL:begin
     done_mask<=reached_target;
     if((&reached_target) && pulse_safe && (&released[2:0]))state<=FINISH;
    end
    FINISH:if(home_complete)begin state<=READY;home_owner_q<=0;home_done<=1;home_done_time<=time_us;event_sequence<=event_sequence+1'b1;end
    default:begin end
   endcase
   // Persistent sources must not prevent safe drain completion.
   if(state==DRAIN && pulse_safe)begin state<=(|(causes|new_causes)) ? FAULT:NEED;home_owner_q<=0;end
  end
 end
endmodule
