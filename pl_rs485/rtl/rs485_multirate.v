// Multi-rate read-only collector. One logical transaction, bounded config/divide.
module rs485_multirate #(
 `include "parameters.vh"
 ,
 `include "rate_parameters.vh"
)(input wire clk,rst_n,enable,input wire [63:0] time_us,input wire rx,
 output wire tx,de,busy,
 input wire cfg_valid,output wire cfg_ready,input wire [159:0] cfg_period_us,
 input wire [4:0] cfg_mask,output reg cfg_applied,cfg_rejected,
 output reg [7:0] cfg_error,output reg [31:0] cfg_revision,cfg_apply_sequence,
 output reg [159:0] active_period_us,output reg [4:0] active_mask,
 output reg [31:0] config_load_ppm,
 input wire record_ready,output wire record_valid,output wire [255:0] record_data,
 output wire [31:0] fifo_level,dropped,accepted,errors,ignored_rx,
 output reg [31:0] bus_busy_events,output wire [9:0] node_offline,
 input wire [5:0] debug_task,input wire [3:0] debug_node,
 output wire [31:0] stat_scheduled,stat_sent,stat_valid,stat_missed,stat_max_lateness_us,
 output wire [7:0] node_failure_streak,output wire [63:0] node_cooldown_until_us,
 output wire [31:0] node_backoff_entries);
 `include "rs485_defs.vh"
 `include "rate_defs.vh"
 localparam integer TASKS=SLAVE_COUNT*5;
 localparam integer BIT_CYCLES=(CLK_HZ+BAUD/2)/BAUD;
 localparam [3:0] IDLE=0,SCAN=1,DISPATCH=2,ADVANCE_WAIT=3,
  CFG_CHECK=4,CFG_DIV=5,CFG_WAIT=6;
 reg [3:0] state;
 reg initialized,pending,div_start;
 reg [159:0] shadow_period;
 reg [4:0] shadow_mask;
 reg [2:0] cfg_q;
 reg [63:0] load_sum;
 reg [31:0] shortest,shadow_shortest;
 reg [63:0] next_due[0:TASKS-1];
 reg [31:0] scheduled[0:TASKS-1],sent[0:TASKS-1],valid_count[0:TASKS-1],missed[0:TASKS-1],max_late[0:TASKS-1];
 reg offline[0:SLAVE_COUNT-1];
 reg [7:0] failures[0:SLAVE_COUNT-1];
 reg [63:0] cooldown[0:SLAVE_COUNT-1];
 reg [31:0] backoffs[0:SLAVE_COUNT-1];
 reg [5:0] cursor,scan_index,scanned,selected,inflight;
 reg [3:0] scan_node,selected_node,inflight_node;
 reg [2:0] scan_q,selected_q;
 reg found,selected_probe,inflight_probe;
 reg [63:0] best_due,scan_now,dispatch_time;
 reg [31:0] dispatch_period,next_sequence;
 reg [63:0] numerator;
 reg [31:0] denominator;
 wire div_busy,div_done;
 wire [63:0] quotient;
 wire [31:0] remainder;
 wire engine_ready,engine_active,engine_done,engine_blocked,push;
 wire [7:0] engine_result;
 wire [255:0] push_data;
 wire request_valid=state==DISPATCH && found && enable && !pending && !(cfg_valid && cfg_ready);
 assign cfg_ready=!pending;
 assign busy=engine_active;
 wire [31:0] scan_period=active_period_us[scan_q*32 +:32];
 wire scan_enabled=active_mask[scan_q] && scan_period!=0;
 wire scan_probe=offline[scan_node];
 wire [63:0] scan_due=scan_probe?cooldown[scan_node]:next_due[scan_index];
 wire [31:0] cfg_period=shadow_period[cfg_q*32 +:32];
 function due;input [63:0] now,t;reg [63:0] diff;
  begin diff=now-t;due=!diff[63];end
 endfunction
 function older;input [63:0] a,b;reg [63:0] diff;
  begin diff=a-b;older=diff[63];end
 endfunction
 function [31:0] sat_add;input [31:0] a;input [63:0] b;reg [64:0] total;
  begin total={33'd0,a}+{1'b0,b};sat_add=(total>65'hffffffff)?32'hffffffff:total[31:0];end
 endfunction
 function [31:0] service_cost;input [2:0] q;reg [63:0] c,gap;
  begin c=query_wire_us(q)+RESPONSE_BUDGET_US;
   c=c+(64'd1000000*(PRE_CYCLES+POST_CYCLES+NORMAL_CYCLES)+CLK_HZ-1)/CLK_HZ;
   gap=(64'd1000000*POLL_CYCLES+CLK_HZ-1)/CLK_HZ;
   service_cost=(c>gap)?c[31:0]:gap[31:0];end
 endfunction
 function [31:0] default_shortest;input [159:0] ps;integer q;reg [31:0] n,p;
  begin n=32'hffffffff;for(q=0;q<5;q=q+1) begin p=ps[q*32 +:32];if(p!=0 && p<n) n=p;end default_shortest=n;end
 endfunction
 assign stat_scheduled=debug_task<TASKS?scheduled[debug_task]:0;
 assign stat_sent=debug_task<TASKS?sent[debug_task]:0;
 assign stat_valid=debug_task<TASKS?valid_count[debug_task]:0;
 assign stat_missed=debug_task<TASKS?missed[debug_task]:0;
 assign stat_max_lateness_us=debug_task<TASKS?max_late[debug_task]:0;
 assign node_failure_streak=debug_node<SLAVE_COUNT?failures[debug_node]:0;
 assign node_cooldown_until_us=debug_node<SLAVE_COUNT?cooldown[debug_node]:0;
 assign node_backoff_entries=debug_node<SLAVE_COUNT?backoffs[debug_node]:0;
 genvar g;generate for(g=0;g<10;g=g+1) begin: off_view
  if(g<SLAVE_COUNT) assign node_offline[g]=offline[g];else assign node_offline[g]=1'b0;
 end endgenerate
 div_u64_u32 divider(clk,rst_n,div_start,numerator,denominator,div_busy,div_done,quotient,remainder);
 rs485_transaction #(.CLK_HZ(CLK_HZ),.BAUD(BAUD),.POLL_CYCLES(POLL_CYCLES),
  .TIMEOUT_CYCLES(TIMEOUT_CYCLES),.INTERBYTE_CYCLES(INTERBYTE_CYCLES),.RETRIES(RETRIES),
  .PRE_CYCLES(PRE_CYCLES),.POST_CYCLES(POST_CYCLES),.TURN_CYCLES(TURN_CYCLES),
  .NORMAL_CYCLES(NORMAL_CYCLES),.ERROR_CYCLES(ERROR_CYCLES)) engine(
  .clk(clk),.rst_n(rst_n),.time_us(time_us),.rx(rx),.request_valid(request_valid),.request_ready(engine_ready),
  .request_address(SLAVE_ADDRS[selected_node*8 +:8]),.request_query(selected_q),.request_sequence(next_sequence),
  .tx(tx),.de(de),.active(engine_active),.done(engine_done),.result(engine_result),.bus_blocked(engine_blocked),
  .push(push),.push_data(push_data),.accepted(accepted),.errors(errors),.ignored_rx(ignored_rx));
 record_fifo #(.DEPTH(FIFO_DEPTH)) fifo(clk,rst_n,push,push_data,record_ready,record_valid,record_data,dropped,fifo_level);
 integer i,j;
 reg [63:0] lateness;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   state<=IDLE;initialized<=0;pending<=1;div_start<=0;shadow_period<=DEFAULT_PERIODS;shadow_mask<=`RS_QUERY_MASK;cfg_q<=0;
   load_sum<=0;shortest<=default_shortest(DEFAULT_PERIODS);shadow_shortest<=32'hffffffff;
   active_period_us<=0;active_mask<=0;
   cfg_applied<=0;cfg_rejected<=0;cfg_error<=0;cfg_revision<=0;cfg_apply_sequence<=0;config_load_ppm<=0;
   cursor<=0;scan_index<=0;scanned<=0;selected<=0;inflight<=0;scan_node<=0;selected_node<=0;inflight_node<=0;
   scan_q<=0;selected_q<=0;found<=0;selected_probe<=0;inflight_probe<=0;best_due<=0;scan_now<=0;
   dispatch_time<=0;dispatch_period<=0;next_sequence<=0;numerator<=0;denominator<=1;bus_busy_events<=0;
   for(i=0;i<TASKS;i=i+1) begin next_due[i]<=0;scheduled[i]<=0;sent[i]<=0;valid_count[i]<=0;missed[i]<=0;max_late[i]<=0;end
   for(i=0;i<SLAVE_COUNT;i=i+1) begin offline[i]<=0;failures[i]<=0;cooldown[i]<=0;backoffs[i]<=0;end
  end else begin
   div_start<=0;cfg_applied<=0;cfg_rejected<=0;
   if(cfg_valid && cfg_ready) begin pending<=1;shadow_period<=cfg_period_us;shadow_mask<=cfg_mask;end
   if(!initialized) begin initialized<=1;for(i=0;i<TASKS;i=i+1) next_due[i]<=time_us;end
   if(engine_blocked) bus_busy_events<=sat_add(bus_busy_events,1);
   if(engine_done) begin
    if(engine_result==`RS_STATUS_VALID) begin
     valid_count[inflight]<=sat_add(valid_count[inflight],1);failures[inflight_node]<=0;
     if(inflight_probe) begin offline[inflight_node]<=0;
      for(j=0;j<5;j=j+1) next_due[inflight_node*5+j]<=time_us;end
    end else if(engine_result!=`RS_STATUS_BUS_BUSY) begin
     if(inflight_probe || failures[inflight_node]>=FAILURE_THRESHOLD-1) begin
      offline[inflight_node]<=1;cooldown[inflight_node]<=time_us+BACKOFF_US;
      backoffs[inflight_node]<=sat_add(backoffs[inflight_node],1);
     end
     if(failures[inflight_node]!=8'hff) failures[inflight_node]<=failures[inflight_node]+1'b1;
    end else if(inflight_probe) cooldown[inflight_node]<=time_us+BACKOFF_US;
   end
   case(state)
    IDLE: if(initialized) begin
     if(pending) begin cfg_q<=0;load_sum<=0;shadow_shortest<=32'hffffffff;cfg_error<=0;state<=CFG_CHECK;end
     else if(engine_ready && enable && active_mask!=0 && time_us!=scan_now) begin
      scan_index<=cursor;scan_node<=cursor/5;scan_q<=cursor%5;scanned<=0;found<=0;scan_now<=time_us;state<=SCAN;
     end
    end
    SCAN: begin
     if(scan_enabled && (!scan_probe || scan_period==shortest) && due(scan_now,scan_due)) begin
      if(!found || older(scan_due,best_due)) begin
       found<=1;selected<=scan_index;selected_node<=scan_node;selected_q<=scan_q;
       selected_probe<=scan_probe;best_due<=scan_due;
      end
     end
     if(scanned==TASKS-1) state<=DISPATCH;
     else begin
      scanned<=scanned+1'b1;scan_index<=(scan_index==TASKS-1)?0:scan_index+1'b1;
      if(scan_q==4) begin scan_q<=0;scan_node<=(scan_node==SLAVE_COUNT-1)?0:scan_node+1'b1;end else scan_q<=scan_q+1'b1;
     end
    end
    DISPATCH: begin
     if(pending || !found || !enable || (cfg_valid && cfg_ready)) state<=IDLE;
     else if(engine_ready) begin
      inflight<=selected;inflight_node<=selected_node;inflight_probe<=selected_probe;
      next_sequence<=next_sequence+1'b1;cursor<=(selected==TASKS-1)?0:selected+1'b1;
      sent[selected]<=sat_add(sent[selected],1);
      dispatch_time<=time_us;dispatch_period<=active_period_us[selected_q*32 +:32];
      lateness=time_us-best_due;
      if(lateness>max_late[selected]) max_late[selected]<=sat_add(0,lateness);
      if(selected_probe) begin scheduled[selected]<=sat_add(scheduled[selected],1);state<=IDLE;end
      else begin
       numerator<=lateness;denominator<=active_period_us[selected_q*32 +:32];div_start<=1;state<=ADVANCE_WAIT;
      end
     end
    end
    ADVANCE_WAIT: if(div_done) begin
     // Modulo arithmetic preserves ideal phase across 64-bit time wrap.
     next_due[inflight]<=dispatch_time-remainder+dispatch_period;
     missed[inflight]<=sat_add(missed[inflight],quotient);
     scheduled[inflight]<=sat_add(scheduled[inflight],quotient+1'b1);state<=IDLE;
    end
    CFG_CHECK: begin
     if(cfg_period!=0 && (cfg_period<MIN_PERIOD_US || cfg_period>MAX_PERIOD_US)) begin
      cfg_error<=`MR_CFG_RANGE;cfg_rejected<=1;pending<=0;state<=IDLE;
     end else if(shadow_mask[cfg_q] && cfg_period!=0) begin
      if(cfg_period<shadow_shortest) shadow_shortest<=cfg_period;
      numerator<=64'd1000000*SLAVE_COUNT*service_cost(cfg_q);denominator<=cfg_period;div_start<=1;state<=CFG_DIV;
     end else if(cfg_q==4) state<=CFG_WAIT;
     else cfg_q<=cfg_q+1'b1;
    end
    CFG_DIV: if(div_done) begin
     // Round each utilization contribution UP, avoiding false admission.
     load_sum<=load_sum+quotient+(remainder!=0);
     if(load_sum+quotient+(remainder!=0)>LOAD_LIMIT_PPM) begin
      cfg_error<=`MR_CFG_LOAD;cfg_rejected<=1;pending<=0;state<=IDLE;
     end else if(cfg_q==4) state<=CFG_WAIT;
     else begin cfg_q<=cfg_q+1'b1;state<=CFG_CHECK;end
    end
    CFG_WAIT: if(!engine_active) begin
     pending<=0;state<=IDLE;
     if(cfg_revision==32'hffffffff) begin cfg_error<=`MR_CFG_REVISION;cfg_rejected<=1;end
     else begin
      active_period_us<=shadow_period;active_mask<=shadow_mask;shortest<=shadow_shortest;
      config_load_ppm<=load_sum[31:0];cfg_revision<=cfg_revision+1'b1;cfg_apply_sequence<=next_sequence;
      cfg_error<=0;cfg_applied<=1;cursor<=0;scan_now<=time_us-1'b1;
      for(i=0;i<TASKS;i=i+1) next_due[i]<=time_us;
     end
    end
    default: state<=IDLE;
   endcase
  end
 end
 // synthesis translate_off
 initial begin
  if(SLAVE_COUNT<1 || SLAVE_COUNT>10 || RETRIES!=1 || FAILURE_THRESHOLD<1 || FAILURE_THRESHOLD>255 ||
   BACKOFF_US<1 || MIN_PERIOD_US<1 || LOAD_LIMIT_PPM<1 || LOAD_LIMIT_PPM>1000000 ||
   BIT_CYCLES<8 || NORMAL_CYCLES<10*BIT_CYCLES || ERROR_CYCLES<10*BIT_CYCLES ||
   PRE_CYCLES<1 || POST_CYCLES<1 || TURN_CYCLES<1 || TIMEOUT_CYCLES<=TURN_CYCLES || FIFO_DEPTH<2)
    $fatal(1,"invalid multirate parameters");
 end
 // synthesis translate_on
endmodule
