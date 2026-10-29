`timescale 1ns/1ps
`include "interlock_defs.vh"
module tb_interlock;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg [63:0] time_us=0;
 reg poll_run=0,poll_stop_commit=0,collector_reset=0,config_change=0;
 reg [31:0] generation=1,revision=1;
 reg [159:0] periods={32'd1000000,128'd0};reg [4:0] mask=16;
 reg feedback_commit=0;reg [255:0] raw=0;
 reg [31:0] feedback_generation=1,feedback_revision=1;
 reg config_apply=0;reg [2:0] config_axes=7;
 reg [31:0] feedback_us=2000000,watchdog_us=2000000;
 reg idle_off=1,owner_open=0,owner_close=0,heartbeat_commit=0,clear_request=0;
 reg [63:0] heartbeat_owner=0,heartbeat_sequence=0;
 wire open_ok,close_ok,hb_ok,clear_ok,owner_active,hb_qualified,feedback_qualified,permit,detect,disable_request;
 wire [63:0] owner_id,last_seq,first_time;wire [31:0] causes,first_cause,detected;
 wire [2:0] axes,seen;wire [31:0] active_feedback,active_watchdog;wire [255:0] last_times;
 wire [63:0] unused_next_round;integer checks=0,i,j;
 wire [5:0] reference_task;wire reference_formed,reference_valid,reference_known;
 wire [63:0] reference_value;wire [31:0] reference_carry;
 wire [15:0] reference_word;wire [7:0] reference_enum;
 rs485_light_parse reference_parser(raw,reference_task,reference_formed,reference_valid,
  reference_known,reference_value,reference_carry,reference_word,reference_enum);
 wire [2:0] reference_axes={reference_task==14,reference_task==9,reference_task==4} &
  {3{reference_formed && reference_valid && reference_known}};
 integer parser_checks=0,pn,pe,pf;reg [255:0] parser_good;
 safety_interlock dut(clk,rst_n,time_us,poll_run,collector_reset,config_change,
  generation,revision,periods,mask,feedback_commit,raw,feedback_generation,feedback_revision,
  config_apply,config_axes,feedback_us,watchdog_us,idle_off,owner_open,owner_close,
  heartbeat_commit,heartbeat_owner,heartbeat_sequence,clear_request,open_ok,close_ok,hb_ok,clear_ok,
  owner_id,last_seq,owner_active,hb_qualified,axes,seen,active_feedback,active_watchdog,
  feedback_qualified,permit,detect,disable_request,detected,causes,first_cause,first_time,last_times,poll_stop_commit,
  32'd0,32'd0,6'd0,1'b0,1'b0,1'b0,2'd0,unused_next_round);
 task check;input condition;input [799:0] message;
  begin checks=checks+1;if(!condition)$fatal(1,"%s time=%h causes=%h",message,time_us,causes);end
 endtask
 task compare_parser;begin
  #1;parser_checks=parser_checks+1;
  if((dut.feedback_axis & {3{dut.protection_record}})!==reference_axes)
   $fatal(1,"protection specialization differs from existing parser raw=%h",raw);
 end endtask
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 task reset;
  begin rst_n=0;poll_run=0;poll_stop_commit=0;feedback_commit=0;owner_open=0;owner_close=0;
   heartbeat_commit=0;clear_request=0;collector_reset=0;config_change=0;config_apply=0;
   generation=1;revision=1;feedback_generation=1;feedback_revision=1;mask=16;time_us=0;
   tick;rst_n=1;tick;
  end
 endtask
 task reply;input integer axis;input [7:0] enumeration;
  begin
   raw=0;raw[255:248]=1;raw[247:240]=8'he0+axis;raw[239:232]=8'h3e;
   raw[215:208]=1;raw[175:112]=time_us;raw[111:48]=time_us;raw[7:0]=enumeration;
   feedback_commit=1;tick;feedback_commit=0;
  end
 endtask
 task start_poll;begin poll_run=1;tick;tick;end endtask
 task open_owner;begin check(open_ok,"owner open eligible");owner_open=1;tick;owner_open=0;end endtask
 task feed;input [63:0] seq;
  begin heartbeat_owner=owner_id;heartbeat_sequence=seq;heartbeat_commit=1;tick;heartbeat_commit=0;end
 endtask
 task qualify;
  begin start_poll;reply(0,2);reply(1,2);reply(2,2);open_owner;feed(1);
   check(permit,"first fresh feedback and heartbeat qualify");
  end
 endtask
 initial begin
  // Differential oracle is the unchanged general acquisition parser, not a
  // second copy of the specialized equations. Exercise every address/query
  // pair, all enums/header byte values and every forbidden upper payload bit.
  for(pn=0;pn<3;pn=pn+1)begin
   parser_good=0;parser_good[255:248]=1;parser_good[247:240]=8'he0+pn;
   parser_good[239:232]=8'h3e;parser_good[215:208]=1;parser_good[7:0]=2;
   for(pe=0;pe<256;pe=pe+1)begin
    raw=parser_good;raw[7:0]=pe;compare_parser;
    raw=parser_good;raw[255:248]=pe;compare_parser;
    raw=parser_good;raw[231:224]=pe;compare_parser;
    raw=parser_good;raw[215:208]=pe;compare_parser;
   end
   for(pf=8;pf<48;pf=pf+1)begin raw=parser_good;raw[pf]=1;compare_parser;end
  end
  for(pn=0;pn<256;pn=pn+1)for(pe=0;pe<256;pe=pe+1)begin
   raw=parser_good;raw[247:240]=pn;raw[239:232]=pe;compare_parser;
  end
  for(i=0;i<3;i=i+1)begin
   reset;qualify;time_us=10;reply(i,1);
   check(causes==(32'd512<<i) && !permit && !owner_active,"each axis protection cancels owner");
   check(first_time==10,"first protection timestamp");
   poll_run=0;tick;check(causes==(32'd512<<i),"poll off does not clear");
  end
  reset;start_poll;time_us=1999999;#1;check(!detect,"before first feedback deadline");
  time_us=2000000;#1;check(detected==32'h7000,"all first feedback expires at boundary");
  reply(0,2);check(causes==32'h7000,"same-edge healthy feedback loses to expiry");
  for(i=0;i<3;i=i+1)begin
   reset;start_poll;time_us=1000000;
   for(j=0;j<3;j=j+1)if(j!=i)reply(j,2);
   time_us=2000000;#1;check(detected==(32'h1000<<i),"each axis timeout independent of other axes");tick;
  end
  reset;qualify;time_us=10;reply(0,1);time_us=20;reply(1,1);
  check(causes==32'h600 && first_cause==32'h200 && first_time==10,"multiple reasons OR and first event retained");
  reset;qualify;time_us=1000000;reply(0,2);reply(1,2);
  time_us=2000000;#1;check(detected==32'hc000,"axis2 and watchdog simultaneous");
  tick;check(first_cause==32'h4000,"feedback first reason before watchdog");
  reset;qualify;
  time_us=1000000;feed(2);reply(0,2);reply(1,2);reply(2,2);
  check(permit && last_seq==2,"healthy continued activity");
  time_us=1500000;feed(2);check(last_times[255:192]==1000000,"duplicate heartbeat does not refresh");
  feed(1);check(last_seq==2,"backward heartbeat rejected");
  heartbeat_owner=owner_id+1;heartbeat_sequence=3;heartbeat_commit=1;tick;heartbeat_commit=0;
  check(last_seq==2,"wrong owner rejected");
  time_us=3000000;heartbeat_owner=owner_id;heartbeat_sequence=3;heartbeat_commit=1;
  #1;check(!hb_ok && detect,"deadline wins valid heartbeat");tick;heartbeat_commit=0;
  check(!owner_active && causes[15],"watchdog owner removed");
  feed(4);check(!owner_active && !permit,"late heartbeat cannot revive");
  // Fresh feedback may establish recovery eligibility while the fault stays.
  reply(0,2);reply(1,2);reply(2,2);open_owner;
  check(owner_id==2,"new PL-issued identity");feed(1);
  check(causes!=0 && !permit && clear_ok,"recovery health does not auto-clear");
  clear_request=1;tick;clear_request=0;check(causes==0 && permit,"explicit clear after eligibility");
  idle_off=0;#1;check(!close_ok,"active actuator blocks handoff");
  idle_off=1;owner_close=1;tick;owner_close=0;check(!owner_active,"explicit close");
  reset;start_poll;time_us=100;reply(0,2);reply(1,2);reply(2,2);
  poll_run=0;tick;time_us=9000000;tick;check(!detect && causes==0,"off suppresses new feedback timeout");
  start_poll;check(!feedback_qualified && seen==0,"reenable rejects history");
  raw=0;raw[255:248]=1;raw[247:240]=8'he0;raw[239:232]=8'h3e;
  raw[215:208]=1;raw[7:0]=2;raw[175:112]=100;raw[111:48]=100;feedback_commit=1;
  tick;feedback_commit=0;check(seen==0,"old round record rejected");
  feedback_generation=0;reply(0,2);check(seen==0,"old generation rejected");
  feedback_generation=1;feedback_revision=0;reply(0,2);check(seen==0,"old revision rejected");
  feedback_revision=1;reply(0,0);check(seen==0,"unknown enum rejected");
  reply(0,2);check(seen==1,"only addressed axis refreshed");
  raw[239:232]=8'h3a;feedback_commit=1;tick;feedback_commit=0;
  check(seen==1,"other query does not qualify axis");
  revision=2;tick;check(seen==0,"configuration revision resets qualification");
  collector_reset=1;tick;collector_reset=0;tick;check(seen==0,"local reset invalidates health");
  reset;config_axes=1;config_apply=1;tick;config_apply=0;start_poll;
  reply(0,2);check(feedback_qualified,"subset age monitoring qualifies independently");
  reply(2,1);check(causes==`SI_CAUSE_PROTECT_A2,"unmonitored Delta axis protection still stops group");
  config_axes=7;
  reset;qualify;poll_run=0;tick;reply(1,1);
  check(causes==`SI_CAUSE_PROTECT_A1,"in-flight valid protection remains effective after RUN off");
  // Accepted OFF must suppress expiry on the original fire edge, without
  // disarming the watchdog or invalidating a completed in-flight protection.
  reset;qualify;time_us=1000000;feed(2);
  time_us=2000000;poll_stop_commit=1;#1;
  check(!detect && !feedback_qualified,"OFF commit wins feedback expiry on its write edge");
  tick;poll_run=0;poll_stop_commit=0;
  check(causes==0 && owner_active && seen==0,"OFF removes qualification but retains watchdog");
  time_us=2000001;reply(2,1);
  check(causes==`SI_CAUSE_PROTECT_A2,"in-flight protection still valid after accepted OFF");
  reset;qualify;time_us=1000000;feed(2);
  time_us=2000000;poll_stop_commit=1;tick;poll_run=0;poll_stop_commit=0;
  time_us=3000000;#1;check(detected==`SI_CAUSE_WATCHDOG,"OFF cannot suppress watchdog expiry");tick;
  reset;qualify;time_us=2000000;poll_stop_commit=1;
  reply(0,1);poll_run=0;poll_stop_commit=0;
  check(causes==(`SI_CAUSE_PROTECT_A0|`SI_CAUSE_WATCHDOG),"OFF same-edge protection and watchdog remain effective");
  reset;time_us=64'hfffffffffff00000;start_poll;open_owner;feed(1);
  time_us=64'hfffffffffff00000+64'd1999999;#1;check(!detect,"time wrap before expiry");
  time_us=64'hfffffffffff00000+64'd2000000;#1;check(detected==32'hf000,"time wrap at expiry");tick;
  // Non-production state preload skips 2^64-2 OPEN operations, then exercises
  // the public OPEN/feed/CLOSE boundary; no production parameter is changed.
  reset;start_poll;dut.owner_watermark=64'hfffffffffffffffe;open_owner;
  check(owner_id==64'hffffffffffffffff && owner_active,"last nonzero owner identity may be allocated");
  feed(64'hffffffffffffffff);check(last_seq==64'hffffffffffffffff,"last increasing heartbeat sequence accepted");
  time_us=1;feed(0);check(last_seq==64'hffffffffffffffff && last_times[255:192]==0,"wrapped sequence cannot refresh");
  feed(64'hffffffffffffffff);check(last_times[255:192]==0,"max sequence replay cannot refresh");
  owner_close=1;tick;owner_close=0;check(!owner_active && !open_ok,"exhausted epoch forbids owner wrap reuse");
  owner_open=1;tick;owner_open=0;check(!owner_active && owner_id==64'hffffffffffffffff,"rejected OPEN never wraps to owner zero or one");
  $display("PASS interlock_monitor checks=%0d parser_equivalence=%0d",checks,parser_checks);$finish;
 end
endmodule
