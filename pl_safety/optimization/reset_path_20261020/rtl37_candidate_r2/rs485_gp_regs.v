// Independent same-clock AXI-Lite endpoint; no PS full-AXI adaptation.
module rs485_gp_regs #(parameter integer FIFO_DEPTH=8,SLAVE_COUNT=3,INTERLOCK_SUPPORT=0,STATS_VALID_SUPPORT=0)(
 input wire clk,rst_n,input wire [63:0] time_us,
 input wire [32:0] s_awaddr,s_araddr,input wire [31:0] s_wdata,input wire [3:0] s_wstrb,
 input wire s_awvalid,s_wvalid,s_bready,s_arvalid,s_rready,
 output wire s_awready,s_wready,s_arready,output reg s_bvalid,s_rvalid,
 output reg [1:0] s_bresp,s_rresp,output reg [31:0] s_rdata,output wire irq,
 output reg run,output wire collector_rst_n,output reg cfg_valid,
 input wire cfg_ready,cfg_applied,cfg_rejected,input wire [7:0] cfg_error,
 output reg [159:0] cfg_period_us,output reg [4:0] cfg_mask,
 input wire [159:0] active_period_us,input wire [4:0] active_mask,
 input wire [31:0] cfg_revision,cfg_apply_sequence,config_load_ppm,
 input wire busy,record_valid,input wire [255:0] record_data,output wire record_ready,
 input wire [31:0] fifo_level,dropped,accepted,errors,ignored_rx,bus_busy_events,
 input wire [9:0] node_offline,input wire observe_push,input wire [255:0] observe_data,
 input wire [7999:0] observe_tasks,input wire [1279:0] observe_nodes,
 output wire [31:0] observe_generation,
 input wire interlock_idle,interlock_idle_off,
 output wire interlock_run,interlock_reset,interlock_config_pending,interlock_config_stored_pending,interlock_config_change,interlock_stop_commit,output wire [31:0] next_generation,output wire reset_commit,output wire next_reset,input wire observe_stats_ready);
 `include "gp_defs.vh"
 `include "interlock_gp_defs.vh"
 `include "rs485_defs.vh"
 localparam [32:0] BASE={1'b0,`RG_BASE};
 localparam integer PTR_BITS=(FIFO_DEPTH<=2)?1:$clog2(FIFO_DEPTH);
 reg ah,wh;reg [32:0] wa;reg [31:0] wd;reg [3:0] ws;
 reg aw_snapshot,aw_run,w_run_clear,aw_reset,w_reset;
 reg aw_config,w_full_one;
 reg [1:0] reset_count;
 reg [31:0] generation,irq_pending,irq_mask,access_error;
 reg [159:0] shadow_period;reg [4:0] shadow_mask;reg [31:0] shadow_id;
 reg [31:0] result_state,result_id,result_error,result_revision,result_sequence,result_generation;
 reg [63:0] result_time;
 reg [31:0] last_txn;reg [159:0] last_period;reg [4:0] last_mask;
 reg config_pending;
 reg cap_valid;reg [255:0] cap_data;reg [7:0] read_bitmap;
 reg [31:0] cap_id,cap_watermark,cap_generation,cap_revision,last_consumed;
 reg [31:0] meta[0:FIFO_DEPTH-1];reg [PTR_BITS-1:0] mw,mr;
 reg [31:0] snap_req,snap_id,snap_watermark;reg snap_valid;
 reg [31:0] snapshot[0:`RG_SNAPSHOT_WORDS-1];
 reg snapshot_stats_ready;
 reg r_record;reg [2:0] r_word;reg [31:0] r_cap_id,r_generation;
 wire write_fire=ah && wh && !s_bvalid;
 wire write_window=wa[32:12]==BASE[32:12];
 wire control_write=write_fire && write_window && wa[1:0]==0 && ws!=0;
 // Pending admissions also inhibit HOME/ENABLE on the same commit edge.
 wire config_admission=INTERLOCK_SUPPORT && write_fire && aw_config && w_full_one && shadow_id>last_txn && interlock_idle &&
   shadow_mask[4] && shadow_period[128+:32]!=0 && !config_pending && cfg_ready &&
   reset_count==0 && !cfg_applied && !cfg_rejected;
 assign interlock_config_change=cfg_applied;
 assign interlock_config_stored_pending=config_pending || cfg_valid || !cfg_ready || reset_count!=0 || cfg_applied;
 assign interlock_config_pending=interlock_config_stored_pending || config_admission;
 // The monitor already shares rst_n. Export the actual local-reset hold,
 // avoiding a redundant global reset path through its combinational stop cone.
 assign interlock_reset=INTERLOCK_SUPPORT ? reset_count!=0 : !collector_rst_n;
 wire [31:0] generation_increment=generation+1'b1;
 assign reset_commit=write_fire && aw_reset && w_reset &&
   (!INTERLOCK_SUPPORT || interlock_idle_off) && !run && !busy && !config_pending && !cfg_valid &&
   cfg_ready && reset_count==0 && !cfg_applied && !cfg_rejected && generation!=32'hffffffff;
 assign next_reset=rst_n && (reset_commit || reset_count>1);
 assign next_generation=!rst_n ? 32'd0:reset_commit ? generation_increment:generation;
 wire [31:0] effective_run_write=merge({31'd0,run},wd,ws);
 assign interlock_run=run;
 // Current mailbox predicate projected from exact next captured values.
 // Only the local request is registered; current safety idle remains a fence.
 // No extra OFF/expiry cycle: off_request_q equals the old predicate now.
 reg off_request_q;
 wire capture_aw=s_awvalid && s_awready;
 wire capture_w=s_wvalid && s_wready;
 wire next_ah=!write_fire && (ah || capture_aw);
 wire next_wh=!write_fire && (wh || capture_w);
 wire next_bvalid=write_fire || (s_bvalid && !s_bready);
 wire next_aw_run=capture_aw ? s_awaddr==BASE+`RG_REG_RUN:aw_run;
 wire next_w_clear=capture_w ?
   (s_wstrb[0] && s_wdata[7:0]==0 &&
    (!s_wstrb[1] || s_wdata[15:8]==0) && (!s_wstrb[2] || s_wdata[23:16]==0) &&
    (!s_wstrb[3] || s_wdata[31:24]==0)):w_run_clear;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)off_request_q<=0;
  else off_request_q<=next_ah && next_wh && !next_bvalid && next_aw_run && next_w_clear && !next_reset;
 assign interlock_stop_commit=INTERLOCK_SUPPORT && off_request_q && interlock_idle;
 // Address-only decode occurs at the existing AW registration edge. Payload,
 // ID, reset and write-strobe checks still use the original commit-time state.
 wire snapshot_fire=write_fire && aw_snapshot && ws==4'hf && wd==1 &&
   reset_count==0 && snap_req!=0 && snap_req>snap_watermark;
 // Base is aligned; compare full A33 window, never truncate incoming address.
 wire pop=write_fire && write_window && wa[1:0]==0 && ws==4'hf &&
   wa[11:0]==`RG_REG_CONSUME_ID && cap_valid && wd==cap_id && read_bitmap==8'hff && reset_count==0;
 assign record_ready=pop;
 wire enqueue=observe_push && ((fifo_level<FIFO_DEPTH)||pop);
 assign collector_rst_n=rst_n && reset_count==0;
 assign s_awready=rst_n && !ah && !s_bvalid;
 assign s_wready=rst_n && !wh && !s_bvalid;
 assign s_arready=rst_n && !s_rvalid;
 assign irq=|(irq_pending & irq_mask);
 assign observe_generation=generation;
 function [31:0] merge;input [31:0] oldv,newv;input [3:0] st;integer b;
  begin merge=oldv;for(b=0;b<4;b=b+1) if(st[b]) merge[b*8+:8]=newv[b*8+:8];end
 endfunction
 wire [31:0] status=(run?`RG_STATUS_RUN:0)|(busy?`RG_STATUS_BUSY:0)|
   (config_pending?`RG_STATUS_CFG_PENDING:0)|(cfg_ready?`RG_STATUS_COLLECTOR_READY:0)|
   (cap_valid?`RG_STATUS_CAPTURE_VALID:0)|(reset_count!=0?`RG_STATUS_RESETTING:0);
 wire [31:0] cap_status=(cap_valid?`RG_CAP_VALID_MASK:0)|({24'd0,read_bitmap}<<`RG_CAP_READ_BITMAP_SHIFT);
 wire [31:0] events=(record_valid||cap_valid?`RG_IRQ_DATA:0)|
  (cfg_applied||cfg_rejected?`RG_IRQ_CFG_RESULT:0)|
  (observe_push && observe_data[231:224]!=`RS_STATUS_VALID && observe_data[231:224]!=`RS_STATUS_BUS_BUSY?`RG_IRQ_COMM_ERROR:0)|
  (observe_push && observe_data[231:224]==`RS_STATUS_VALID && observe_data[239:232]==query_code(3'd4) && observe_data[7:0]==1?`RG_IRQ_PROTECT_OBSERVED:0)|
  (observe_push && !enqueue?`RG_IRQ_FIFO_DROP:0)|
  (observe_push && observe_data[231:224]==`RS_STATUS_BUS_BUSY?`RG_IRQ_BUS_DIAGNOSTIC:0);
 reg [31:0] clear_irq,errcode,value,merged;
 reg [1:0] response;
 reg reset_action,snap_action;
 integer i,j,index;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   ah<=0;wh<=0;wa<=0;wd<=0;ws<=0;aw_config<=0;w_full_one<=0;aw_snapshot<=0;aw_run<=0;w_run_clear<=0;aw_reset<=0;w_reset<=0;s_bvalid<=0;s_bresp<=0;s_rvalid<=0;s_rresp<=0;s_rdata<=0;
   run<=0;reset_count<=0;generation<=0;irq_pending<=0;irq_mask<=0;access_error<=0;
   shadow_period<=0;shadow_mask<=0;shadow_id<=0;cfg_valid<=0;
   result_state<=0;result_id<=0;result_error<=0;result_revision<=0;result_sequence<=0;result_time<=0;result_generation<=0;
   last_txn<=0;config_pending<=0;
   cap_valid<=0;read_bitmap<=0;cap_id<=0;cap_watermark<=0;cap_generation<=0;cap_revision<=0;last_consumed<=0;mw<=0;mr<=0;
   snap_req<=0;snap_id<=0;snap_watermark<=0;snap_valid<=0;snapshot_stats_ready<=0;r_record<=0;r_word<=0;r_cap_id<=0;r_generation<=0;
  end else begin
   clear_irq=0;reset_action=0;snap_action=0;
   if(reset_count!=0) reset_count<=reset_count-1'b1;
   if(s_bvalid && s_bready) s_bvalid<=0;
   if(s_rvalid && s_rready) begin
    s_rvalid<=0;
    if(r_record && cap_valid && r_cap_id==cap_id && r_generation==generation)
      read_bitmap<=read_bitmap | (8'b1<<r_word);
   end
   if(s_awvalid && s_awready) begin ah<=1;wa<=s_awaddr;
    aw_config<=s_awaddr==BASE+`RG_REG_CFG_SUBMIT;
    aw_run<=s_awaddr==BASE+`RG_REG_RUN;aw_reset<=s_awaddr==BASE+`RG_REG_LOCAL_RESET;
    aw_snapshot<=s_awaddr[32:12]==BASE[32:12] && s_awaddr[1:0]==0 && s_awaddr[11:0]==`RG_REG_SNAP_SUBMIT;
   end
   if(s_wvalid && s_wready) begin
    wh<=1;wd<=s_wdata;ws<=s_wstrb;w_full_one<=s_wstrb==15 && s_wdata==1;w_reset<=s_wstrb==4'hf && s_wdata==1;
    // With RUN=1, merged RUN can be zero only when byte 0 is written zero
    // and every other strobed byte is zero. Capture that exact predicate at
    // W acceptance; the side effect still occurs only on write_fire.
    w_run_clear<=s_wstrb[0] && s_wdata[7:0]==0 &&
      (!s_wstrb[1] || s_wdata[15:8]==0) && (!s_wstrb[2] || s_wdata[23:16]==0) &&
      (!s_wstrb[3] || s_wdata[31:24]==0);
   end
   if(cfg_valid && cfg_ready) cfg_valid<=0;
   if(cfg_applied || cfg_rejected) begin
    result_state<=`RG_CFG_ACCEPTED | (cfg_applied?`RG_CFG_APPLIED:`RG_CFG_REJECTED);
    result_id<=config_pending?last_txn:0;result_error<=cfg_rejected?{24'd0,cfg_error}:0;
    result_revision<=cfg_revision;result_sequence<=cfg_apply_sequence;result_time<=time_us;result_generation<=generation;
    config_pending<=0;
   end
   if(enqueue) begin meta[mw]<=cfg_revision;mw<=(mw==FIFO_DEPTH-1)?0:mw+1'b1;end
   if(pop) mr<=(mr==FIFO_DEPTH-1)?0:mr+1'b1;
   if(write_fire) begin
    response=0;errcode=`RG_ERR_NONE;ah<=0;wh<=0;s_bvalid<=1;
    if(!write_window) begin response=3;errcode=`RG_ERR_ADDRESS;end
    else if(wa[1:0]!=0) begin response=2;errcode=`RG_ERR_ALIGN;end
    else begin
     case(wa[11:0])
      `RG_REG_RUN:begin
       merged=merge({31'd0,run},wd,ws);
       if(merged>1) errcode=`RG_ERR_RESERVED;
       else if(INTERLOCK_SUPPORT && ws!=0 && (!interlock_idle ||
         (merged[0] && (busy || interlock_config_pending || !active_mask[4] || active_period_us[128+:32]==0))))errcode=`RG_ERR_BUSY;
       else if(reset_count!=0 && ws!=0) errcode=`RG_ERR_BUSY;else run<=merged[0];
      end
      `RG_REG_IRQ_MASK:begin
       merged=merge(irq_mask,wd,ws);if((merged & ~`RG_IRQ_VALID_MASK)!=0) errcode=`RG_ERR_RESERVED;else irq_mask<=merged;
      end
      `RG_REG_SHADOW_PERIOD0,`RG_REG_SHADOW_PERIOD1,`RG_REG_SHADOW_PERIOD2,`RG_REG_SHADOW_PERIOD3,`RG_REG_SHADOW_PERIOD4:begin
       index=(wa[11:0]-`RG_REG_SHADOW_PERIOD0)>>2;shadow_period[index*32+:32]<=merge(shadow_period[index*32+:32],wd,ws);
      end
      `RG_REG_SHADOW_MASK:begin
       merged=merge({27'd0,shadow_mask},wd,ws);if((merged & ~`RG_QUERY_VALID_MASK)!=0) errcode=`RG_ERR_RESERVED;else shadow_mask<=merged[4:0];
      end
      `RG_REG_TXN_ID:shadow_id<=merge(shadow_id,wd,ws);
      `RG_REG_SNAP_REQ_ID:snap_req<=merge(snap_req,wd,ws);
      `RG_REG_IRQ_PENDING,`RG_REG_LOCAL_RESET,`RG_REG_CFG_SUBMIT,`RG_REG_CAPTURE,`RG_REG_CONSUME_ID,`RG_REG_ABANDON_ID,`RG_REG_SNAP_SUBMIT:begin
       if(ws==0) begin end
       else if(ws!=4'hf) errcode=`RG_ERR_STROBE;
       else case(wa[11:0])
        `RG_REG_IRQ_PENDING:if((wd & ~`RG_IRQ_VALID_MASK)!=0) errcode=`RG_ERR_RESERVED;else clear_irq=wd;
        `RG_REG_CFG_SUBMIT:begin
         if(wd!=1) errcode=`RG_ERR_RESERVED;
         else if(shadow_id==0 || shadow_id<last_txn) errcode=`RG_ERR_ID;
         else if(shadow_id==last_txn) begin
          if(result_id!=last_txn || result_generation!=generation) errcode=`RG_ERR_ID;
          else if(shadow_period!=last_period || shadow_mask!=last_mask) errcode=`RG_ERR_PAYLOAD;
          // Cached result/pending remains visible; no new cfg_valid.
         end else if(INTERLOCK_SUPPORT && (!interlock_idle || !shadow_mask[4] || shadow_period[128+:32]==0))errcode=`RG_ERR_BUSY;
         else if(config_pending || !cfg_ready || reset_count!=0 || cfg_applied || cfg_rejected) errcode=`RG_ERR_BUSY;
         else begin
          last_txn<=shadow_id;
          cfg_valid<=1;config_pending<=1;
          result_state<=`RG_CFG_ACCEPTED|`RG_CFG_PENDING;result_id<=shadow_id;result_error<=0;
          result_revision<=cfg_revision;result_sequence<=cfg_apply_sequence;result_time<=0;result_generation<=generation;
         end
        end
        `RG_REG_CAPTURE:begin
         if(wd!=1) errcode=`RG_ERR_RESERVED;
         else if(reset_count!=0) errcode=`RG_ERR_BUSY;
         else if(!cap_valid) begin
          if(!record_valid) errcode=`RG_ERR_EMPTY;
          else if(cap_watermark==32'hffffffff) errcode=`RG_ERR_EXHAUSTED;
          else begin
           cap_valid<=1;read_bitmap<=0;cap_id<=cap_watermark+1'b1;cap_watermark<=cap_watermark+1'b1;
           cap_generation<=generation;cap_revision<=meta[mr];
          end
         end
        end
        `RG_REG_CONSUME_ID:begin
         if(wd==0) errcode=`RG_ERR_ID;
         else if(wd==last_consumed) begin end
         else if(!cap_valid || wd!=cap_id || reset_count!=0) errcode=`RG_ERR_ID;
         else if(read_bitmap!=8'hff) errcode=`RG_ERR_PARTIAL;
         else begin cap_valid<=0;read_bitmap<=0;last_consumed<=wd;end
        end
        `RG_REG_ABANDON_ID:begin
         if(!cap_valid || wd!=cap_id || wd==0) errcode=`RG_ERR_ID;
         else begin cap_valid<=0;read_bitmap<=0;end
        end
        `RG_REG_SNAP_SUBMIT:begin
         if(wd!=1) errcode=`RG_ERR_RESERVED;
         else if(reset_count!=0) errcode=`RG_ERR_BUSY;
         else if(snap_req==0 || snap_req<snap_watermark || (snap_req==snap_watermark && !snap_valid)) errcode=`RG_ERR_ID;
         else if(snap_req!=snap_watermark) begin snap_action=1;snap_valid<=1;snap_id<=snap_req;snap_watermark<=snap_req;end
        end
        `RG_REG_LOCAL_RESET:begin
         if(wd!=1) errcode=`RG_ERR_RESERVED;
         else if(INTERLOCK_SUPPORT && !interlock_idle_off)errcode=`RG_ERR_RESET_STATE;
         else if(run || busy || config_pending || cfg_valid || !cfg_ready || reset_count!=0 || cfg_applied || cfg_rejected) errcode=`RG_ERR_RESET_STATE;
         else if(generation==32'hffffffff) errcode=`RG_ERR_EXHAUSTED;
         else reset_action=1;
        end
       endcase
      end
      default:errcode=`RG_ERR_ACCESS;
     endcase
     if(errcode!=`RG_ERR_NONE) response=2;
    end
    s_bresp<=response;if(errcode!=0) access_error<=errcode;
   end
   if(s_arvalid && s_arready) begin
    response=0;errcode=0;value=0;r_record<=0;
    if(s_araddr[32:12]!=BASE[32:12]) begin response=3;errcode=`RG_ERR_ADDRESS;end
    else if(s_araddr[1:0]!=0) begin response=2;errcode=`RG_ERR_ALIGN;end
    else if(s_araddr[11:0]>=`RG_SNAPSHOT_BASE && s_araddr[11:0]<`RG_SNAPSHOT_BASE+`RG_SNAPSHOT_WORDS*4) begin
     if(!snap_valid) errcode=`RG_ERR_EMPTY;else if(STATS_VALID_SUPPORT && !snapshot_stats_ready && s_araddr[11:0]>=`RG_TASK_BASE) value=0;
     else value=snapshot[(s_araddr[11:0]-`RG_SNAPSHOT_BASE)>>2];
    end else case(s_araddr[11:0])
     `RG_REG_VERSION:value=INTERLOCK_SUPPORT ? `RGI_VERSION:`RG_VERSION;
     `RG_REG_PROFILE:value=INTERLOCK_SUPPORT ? `RGI_PROFILE:`RG_PROFILE;
     `RG_REG_CAPS:value=INTERLOCK_SUPPORT ? `RGI_CAPS:`RG_CAPS;
     `RG_REG_FEATURES:value=INTERLOCK_SUPPORT ? `RGI_FEATURES:`RG_FEATURES;
     `RG_REG_RUN:value={31'd0,run};
     `RG_REG_STATUS:value=status;
     `RG_REG_GENERATION:value=generation;
     `RG_REG_IRQ_PENDING:value=irq_pending;
     `RG_REG_IRQ_MASK:value=irq_mask;
     `RG_REG_LAST_ACCESS_ERROR:value=access_error;
     `RG_REG_FIFO_LEVEL:value=fifo_level;
     `RG_REG_SHADOW_PERIOD0,`RG_REG_SHADOW_PERIOD1,`RG_REG_SHADOW_PERIOD2,`RG_REG_SHADOW_PERIOD3,`RG_REG_SHADOW_PERIOD4:
      value=shadow_period[((s_araddr[11:0]-`RG_REG_SHADOW_PERIOD0)>>2)*32+:32];
     `RG_REG_SHADOW_MASK:value={27'd0,shadow_mask};
     `RG_REG_TXN_ID:value=shadow_id;
     `RG_REG_CFG_STATE:value=result_state;
     `RG_REG_CFG_TXN:value=result_id;
     `RG_REG_CFG_ERROR:value=result_error;
     `RG_REG_CFG_REVISION:value=result_revision;
     `RG_REG_CFG_SEQUENCE:value=result_sequence;
     `RG_REG_CFG_TIME_LO:value=result_time[31:0];
     `RG_REG_CFG_TIME_HI:value=result_time[63:32];
     `RG_REG_CFG_GENERATION:value=result_generation;
     `RG_REG_CURRENT_PERIOD0,`RG_REG_CURRENT_PERIOD1,`RG_REG_CURRENT_PERIOD2,`RG_REG_CURRENT_PERIOD3,`RG_REG_CURRENT_PERIOD4:
      value=active_period_us[((s_araddr[11:0]-`RG_REG_CURRENT_PERIOD0)>>2)*32+:32];
     `RG_REG_CURRENT_MASK:value={27'd0,active_mask};
     `RG_REG_CURRENT_LOAD:value=config_load_ppm;
     `RG_REG_CAPTURE_ID:value=cap_id;
     `RG_REG_CAPTURE_STATUS:value=cap_status;
     `RG_REG_CAPTURE_GENERATION:value=cap_generation;
     `RG_REG_CAPTURE_REVISION:value=cap_revision;
     `RG_REG_LAST_CONSUMED_ID:value=last_consumed;
     `RG_REG_WORD0,`RG_REG_WORD1,`RG_REG_WORD2,`RG_REG_WORD3,`RG_REG_WORD4,`RG_REG_WORD5,`RG_REG_WORD6,`RG_REG_WORD7:begin
      if(!cap_valid) errcode=`RG_ERR_EMPTY;
      else begin
       index=(s_araddr[11:0]-`RG_REG_WORD0)>>2;value=cap_data[index*32+:32];
       r_record<=1;r_word<=index;r_cap_id<=cap_id;r_generation<=generation;
      end
     end
     `RG_REG_SNAP_REQ_ID:value=snap_req;
     `RG_REG_SNAP_STATUS:value={31'd0,snap_valid};
     `RG_REG_SNAP_ID:value=snap_id;
     default:errcode=`RG_ERR_ACCESS;
    endcase
    if(response==0 && errcode!=0) response=2;
    s_rdata<=value;s_rresp<=response;s_rvalid<=1;
    if(errcode!=0) access_error<=errcode;
   end
   if(snapshot_fire) begin
    snapshot_stats_ready<=observe_stats_ready;
    for(i=0;i<`RG_SNAPSHOT_WORDS;i=i+1) snapshot[i]<=0;
    snapshot[`RG_SNAP_TIME_LO]<=time_us[31:0];snapshot[`RG_SNAP_TIME_HI]<=time_us[63:32];
    snapshot[`RG_SNAP_GENERATION]<=generation;snapshot[`RG_SNAP_REVISION]<=cfg_revision;
    snapshot[`RG_SNAP_APPLY_SEQUENCE]<=cfg_apply_sequence;snapshot[`RG_SNAP_MASK]<={27'd0,active_mask};
    for(i=0;i<5;i=i+1) snapshot[`RG_SNAP_PERIOD0+i]<=active_period_us[i*32+:32];
    snapshot[`RG_SNAP_LOAD]<=config_load_ppm;snapshot[`RG_SNAP_FIFO_LEVEL]<=fifo_level;
    snapshot[`RG_SNAP_DROPPED]<=dropped;snapshot[`RG_SNAP_ACCEPTED]<=accepted;snapshot[`RG_SNAP_ERRORS]<=errors;
    snapshot[`RG_SNAP_IGNORED_RX]<=ignored_rx;snapshot[`RG_SNAP_BUS_BUSY]<=bus_busy_events;snapshot[`RG_SNAP_OFFLINE]<={22'd0,node_offline};
    snapshot[`RG_SNAP_CFG_STATE]<=result_state;snapshot[`RG_SNAP_CFG_TXN]<=result_id;snapshot[`RG_SNAP_CFG_ERROR]<=result_error;
    snapshot[`RG_SNAP_CFG_TIME_LO]<=result_time[31:0];snapshot[`RG_SNAP_CFG_TIME_HI]<=result_time[63:32];snapshot[`RG_SNAP_CFG_GENERATION]<=result_generation;
    snapshot[`RG_SNAP_RUN]<={31'd0,run};snapshot[`RG_SNAP_CAPTURE_ID]<=cap_id;snapshot[`RG_SNAP_CAPTURE_STATUS]<=cap_status;
    snapshot[`RG_SNAP_SLAVE_COUNT]<=SLAVE_COUNT;snapshot[`RG_SNAP_FIFO_DEPTH]<=FIFO_DEPTH;
    for(i=0;i<SLAVE_COUNT;i=i+1) for(j=0;j<4;j=j+1)
     snapshot[((`RG_NODE_BASE-`RG_SNAPSHOT_BASE)>>2)+i*4+j]<=observe_nodes[i*128+j*32+:32];
    for(i=0;i<SLAVE_COUNT*5;i=i+1) for(j=0;j<5;j=j+1)
     snapshot[((`RG_TASK_BASE-`RG_SNAPSHOT_BASE)>>2)+i*8+j]<=observe_tasks[i*160+j*32+:32];
   end
   irq_pending<=(irq_pending & ~clear_irq)|events;
   if(reset_action) begin
    reset_count<=2;generation<=generation_increment;run<=0;cfg_valid<=0;config_pending<=0;
    cap_valid<=0;read_bitmap<=0;cap_id<=0;cap_generation<=generation_increment;cap_revision<=0;last_consumed<=0;mw<=0;mr<=0;
    snap_valid<=0;snap_id<=0;
    result_state<=0;result_id<=0;result_error<=0;result_revision<=0;result_sequence<=0;result_time<=0;result_generation<=generation_increment;
    irq_pending<=`RG_IRQ_RESET_DONE;
   end
  end
 end

// synthesis translate_off
always @(posedge clk)if(rst_n && write_fire)begin
 if(aw_config !== (write_window && wa[1:0]==0 && wa[11:0]==`RG_REG_CFG_SUBMIT))
  $fatal(1,"CFG address predecode mismatch");
 if(w_full_one !== (ws==15 && wd==1))$fatal(1,"CFG payload predecode mismatch");
end
// synthesis translate_on

// Private payloads are initialized on the original accepted capture edge.
// cfg_valid, last_txn!=0 and cap_valid retain asynchronous invalidation.
wire full_control_write=write_fire && write_window && wa[1:0]==0 && ws==4'hf && wd==1;
wire cfg_payload_capture=full_control_write && wa[11:0]==`RG_REG_CFG_SUBMIT &&
 shadow_id!=0 && shadow_id>last_txn &&
 !(INTERLOCK_SUPPORT && (!interlock_idle || !shadow_mask[4] || shadow_period[159:128]==0)) &&
 !config_pending && cfg_ready && reset_count==0 && !cfg_applied && !cfg_rejected;
wire record_payload_capture=full_control_write && wa[11:0]==`RG_REG_CAPTURE &&
 reset_count==0 && !cap_valid && record_valid && cap_watermark!=32'hffffffff;
always @(posedge clk)begin
 if(cfg_payload_capture)begin
  last_period<=shadow_period;last_mask<=shadow_mask;
  cfg_period_us<=shadow_period;cfg_mask<=shadow_mask;
 end
 if(record_payload_capture)cap_data<=record_data;
end
endmodule
