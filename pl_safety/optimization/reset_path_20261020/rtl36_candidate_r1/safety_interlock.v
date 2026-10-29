`timescale 1ns/1ps
`include "interlock_defs.vh"
// Same-domain monitor. No ownership of STEP/DIR/EN or the shared timebase.
module safety_interlock #(parameter LOOKAHEAD_EPOCH=0,parameter FEEDBACK_PREDECODE=0,parameter LOOKAHEAD_CONTEXT=0,parameter LOOKAHEAD_WRAP=0,parameter LOOKAHEAD_TIME=0)(
 input wire clk,rst_n,input wire [63:0] time_us,
 input wire poll_run,collector_reset,config_change,
 input wire [31:0] collector_generation,collector_revision,
 input wire [159:0] collector_periods,input wire [4:0] collector_mask,
 input wire feedback_commit,input wire [255:0] feedback_raw,
 input wire [31:0] feedback_generation,feedback_revision,
 input wire config_apply,input wire [2:0] config_axes,
 input wire [31:0] config_feedback_us,config_watchdog_us,
 input wire idle_off,input wire owner_open,owner_close,
 input wire heartbeat_commit,input wire [63:0] heartbeat_owner,heartbeat_sequence,
 input wire clear_request,
 output wire owner_open_ok,owner_close_ok,heartbeat_ok,clear_ok,
 output reg [63:0] owner_id,last_sequence,
 output reg owner_active,heartbeat_qualified,
 output reg [2:0] active_axes,feedback_seen,
 output reg [31:0] feedback_timeout_us,watchdog_timeout_us,
 output wire feedback_qualified,permit,detect,disable_request,
 output wire [31:0] detected_causes,
 output reg [31:0] causes,first_cause,
 output reg [63:0] first_time,
 output wire [255:0] last_times,
 input wire poll_stop_commit,
 input wire [31:0] next_generation,next_revision,
 input wire [5:0] feedback_predecoded,
 input wire next_collector_reset,next_config_change,next_config_apply,
 input wire [1:0] feedback_time_valid,output wire [63:0] next_round_start_time
);
 reg previous_run,round_valid;reg epoch_match_q;reg active_context_q,off_context_q;
 reg [31:0] round_generation,round_revision;
 reg [63:0] round_start,owner_watermark,watchdog_start,watchdog_deadline;
 reg [63:0] feedback_start[0:2],feedback_deadline[0:2];
 reg watchdog_wrap;reg [2:0] feedback_wrap;
 `include "rs485_defs.vh"
 localparam [79:0] NODE_ADDRS=`RS_SLAVE_ADDRS;
 wire [7:0] enum_raw=feedback_raw[7:0];
 // Fixed protection-format specialization of rs485_light_parse. Avoid its
 // generic query/task encoding, variable payload shift and task re-decoding
 // in the same-edge stop cone. The general acquisition parser is unchanged.
 wire protection_record=feedback_raw[255:248]==`RS_VERSION &&
   feedback_raw[239:232]==query_code(3'd4) && feedback_raw[231:224]==`RS_STATUS_VALID &&
   feedback_raw[215:208]=={4'd0,query_length(3'd4)} && feedback_raw[47:8]==0 &&
   (enum_raw==1 || enum_raw==2);
 wire polling_config_ok=collector_mask[4] && collector_periods[128+:32]!=0;
 wire epoch_match=LOOKAHEAD_EPOCH ? epoch_match_q :
   collector_generation==round_generation && collector_revision==round_revision;
 wire restart=poll_run && (!previous_run || config_change || collector_reset || !epoch_match || config_apply);
 assign next_round_start_time=restart ? time_us:round_start;
 wire [31:0] next_round_generation=restart ? collector_generation:round_generation;
 wire [31:0] next_round_revision=restart ? collector_revision:round_revision;
 wire next_epoch_match=next_generation==next_round_generation && next_revision==next_round_revision;
 // An accepted OFF suppresses feedback expiry on its original write edge.
 // Keep it out of restart/protection qualification: in-flight protection
 // remains valid and the only stored RUN is still the collector register.
 wire monitoring=LOOKAHEAD_CONTEXT ? (poll_run && !poll_stop_commit && active_context_q):
   (poll_run && !poll_stop_commit && previous_run && !restart && !collector_reset);
 wire [63:0] request_age=feedback_raw[175:112]-round_start;
 wire [63:0] event_age=feedback_raw[111:48]-round_start;
 wire feedback_valid=feedback_commit && (FEEDBACK_PREDECODE ? |feedback_predecoded[2:0]:protection_record) &&
   (LOOKAHEAD_EPOCH ? ((LOOKAHEAD_CONTEXT ? 1'b1:epoch_match_q) && feedback_generation==collector_generation &&
    feedback_revision==collector_revision) :
    (feedback_generation==round_generation && feedback_revision==round_revision)) &&
   (LOOKAHEAD_TIME ? (&feedback_time_valid):(!request_age[63] && !event_age[63])) && round_valid &&
   (LOOKAHEAD_CONTEXT ? (poll_run ? active_context_q:off_context_q):(!restart && !collector_reset));
 wire [2:0] feedback_axis={feedback_raw[247:240]==NODE_ADDRS[16+:8],
   feedback_raw[247:240]==NODE_ADDRS[8+:8],feedback_raw[247:240]==NODE_ADDRS[0+:8]};
 wire [2:0] update_axis=(FEEDBACK_PREDECODE ? feedback_predecoded[2:0]:feedback_axis) & active_axes & {3{feedback_valid && monitoring}};
 // Every configured Delta axis reporting protection stops the group, even
 // when only a subset has been selected for feedback-age monitoring.
 wire [2:0] protected_axis=(FEEDBACK_PREDECODE ? feedback_predecoded[5:3]:
   (feedback_axis & {3{enum_raw==1}})) & {3{feedback_valid}};
 wire watchdog_expired=owner_active && (LOOKAHEAD_WRAP ? expired_marked(time_us,watchdog_start,watchdog_deadline,watchdog_wrap):expired(time_us,watchdog_start,watchdog_deadline));
 reg [2:0] feedback_expired;
 integer a;
 function expired;
  input [63:0] now_us,start_us,deadline_us;
  begin
   expired=deadline_us<start_us ? (now_us>=deadline_us && now_us<start_us) :
                                    (now_us>=deadline_us || now_us<start_us);
  end
 endfunction
 always @*begin
  feedback_expired=0;
  for(a=0;a<3;a=a+1)
   feedback_expired[a]=monitoring && active_axes[a] &&
     (LOOKAHEAD_WRAP ? expired_marked(time_us,feedback_start[a],feedback_deadline[a],feedback_wrap[a]):expired(time_us,feedback_start[a],feedback_deadline[a]));
 end
 // Configuration cannot silently turn a monitored query off. The GP admission
 // path also rejects it before application. This is a defensive final guard.
 wire [2:0] missing_query=monitoring && !polling_config_ok ? active_axes:3'd0;
 assign detected_causes=({29'd0,protected_axis}<<9) |
   ({29'd0,(feedback_expired|missing_query)}<<12) |
   (watchdog_expired ? `SI_CAUSE_WATCHDOG:32'd0);
 assign detect=|detected_causes;
 assign disable_request=|(detected_causes & ~causes);
 assign feedback_qualified=monitoring && polling_config_ok &&
   (feedback_seen & active_axes)==active_axes && !(|feedback_expired);
 assign permit=feedback_qualified && owner_active && heartbeat_qualified && !detect && causes==0;
 assign owner_open_ok=idle_off && !owner_active && owner_watermark!=64'hffffffffffffffff && !detect;
 assign owner_close_ok=idle_off && owner_active && !detect;
 assign heartbeat_ok=owner_active && !watchdog_expired && heartbeat_owner==owner_id &&
   heartbeat_sequence!=0 && heartbeat_sequence>last_sequence;
 // Recover qualification while fault stays latched; clear never creates an
 // owner, enables an actuator, restores valid, opens transport or starts HOME.
 assign clear_ok=idle_off && !detect && feedback_qualified && owner_active && heartbeat_qualified;
 assign last_times={watchdog_start,feedback_start[2],feedback_start[1],feedback_start[0]};
 integer i;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   active_context_q<=0;off_context_q<=1;epoch_match_q<=1;previous_run<=0;round_valid<=0;round_generation<=0;round_revision<=0;round_start<=0;
   owner_watermark<=0;owner_id<=0;owner_active<=0;last_sequence<=0;heartbeat_qualified<=0;
   watchdog_start<=0;watchdog_deadline<=0;watchdog_wrap<=0;feedback_wrap<=0;feedback_seen<=0;
   active_axes<=`SI_DEFAULT_AXIS_MASK;
   feedback_timeout_us<=`SI_TIMEOUT_DEFAULT_US;watchdog_timeout_us<=`SI_TIMEOUT_DEFAULT_US;
   causes<=0;first_cause<=0;first_time<=0;
   for(i=0;i<3;i=i+1)begin feedback_start[i]<=0;feedback_deadline[i]<=0;end
  end else begin
   previous_run<=poll_run;
   epoch_match_q<=next_epoch_match;
   // Project complete NEXT source/round values, not delayed current flags.
   // At the current edge these equal the original expanded qualifications.
   off_context_q<=next_epoch_match && !next_collector_reset;
   active_context_q<=poll_run && next_epoch_match && !next_collector_reset &&
     !next_config_change && !next_config_apply;
   if(collector_reset || (!poll_run && (config_apply || config_change ||
      collector_generation!=round_generation || collector_revision!=round_revision)))round_valid<=0;
   if(config_apply)begin
    active_axes<=config_axes;feedback_timeout_us<=config_feedback_us;watchdog_timeout_us<=config_watchdog_us;
   end
   if(!poll_run || poll_stop_commit || collector_reset)feedback_seen<=0;
   if(restart)begin
    round_start<=time_us;round_valid<=1;round_generation<=collector_generation;round_revision<=collector_revision;
    feedback_seen<=0;
    for(i=0;i<3;i=i+1)begin
     feedback_start[i]<=time_us;
     {feedback_wrap[i],feedback_deadline[i]}<={1'b0,time_us}+{33'd0,(config_apply ? config_feedback_us:feedback_timeout_us)};
    end
   end else for(i=0;i<3;i=i+1)if(update_axis[i])begin
    feedback_start[i]<=time_us;{feedback_wrap[i],feedback_deadline[i]}<={1'b0,time_us}+{33'd0,feedback_timeout_us};
    feedback_seen[i]<=enum_raw==2;
   end
   if(owner_open && owner_open_ok)begin
    owner_watermark<=owner_watermark+1'b1;owner_id<=owner_watermark+1'b1;
    owner_active<=1;last_sequence<=0;heartbeat_qualified<=0;
    watchdog_start<=time_us;{watchdog_wrap,watchdog_deadline}<={1'b0,time_us}+{33'd0,watchdog_timeout_us};
   end
   if(owner_close && owner_close_ok)begin owner_active<=0;heartbeat_qualified<=0;end
   if(heartbeat_commit && heartbeat_ok)begin
    last_sequence<=heartbeat_sequence;heartbeat_qualified<=1;
    watchdog_start<=time_us;{watchdog_wrap,watchdog_deadline}<={1'b0,time_us}+{33'd0,watchdog_timeout_us};
   end
   if(clear_request && clear_ok)begin causes<=0;first_cause<=0;first_time<=0;end
   if(detect)begin
    causes<=causes|detected_causes;
    if(causes==0)begin
     first_time<=time_us;
     first_cause<=|protected_axis ? ({29'd0,protected_axis}<<9) :
       |(feedback_expired|missing_query) ? ({29'd0,(feedback_expired|missing_query)}<<12):`SI_CAUSE_WATCHDOG;
    end
    if(disable_request)begin owner_active<=0;heartbeat_qualified<=0;end
   end
  end
 end

// A u32 timeout added to u64 start wraps iff the carry bit is set. Store
// that carry on the SAME deadline update edge, so this is the original
// CURRENT comparison deadline<start, not a delayed expiry observation.
// now may still jump or wrap arbitrarily; the original two-arc rule holds.
function expired_marked;
 input [63:0] now_us,start_us,deadline_us;input wrapped;
 begin expired_marked=wrapped ? (now_us>=deadline_us && now_us<start_us):
                               (now_us>=deadline_us || now_us<start_us);end
endfunction
// synthesis translate_off
integer wrap_axis;
always @(posedge clk)if(rst_n && LOOKAHEAD_WRAP)begin
 if(watchdog_wrap !== (watchdog_deadline<watchdog_start))$fatal(1,"watchdog current wrap projection mismatch");
 for(wrap_axis=0;wrap_axis<3;wrap_axis=wrap_axis+1)
  if(feedback_wrap[wrap_axis] !== (feedback_deadline[wrap_axis]<feedback_start[wrap_axis]))
   $fatal(1,"feedback current wrap projection mismatch");
end
// synthesis translate_on

// synthesis translate_off
always @(posedge clk)if(rst_n && LOOKAHEAD_TIME && feedback_commit)
 if(feedback_time_valid !== {!event_age[63],!request_age[63]})
  $fatal(1,"same-EMIT time qualification differs from current raw/round timestamps");
// synthesis translate_on
endmodule
