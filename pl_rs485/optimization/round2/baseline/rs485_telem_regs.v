module rs485_telem_regs(
 input wire clk,rst_n,input wire [63:0] time_us,input wire [31:0] collector_generation,cfg_revision,input wire [4:0] active_mask,
 input wire [32:0] s_awaddr,s_araddr,input wire [31:0] s_wdata,input wire [3:0] s_wstrb,
 input wire s_awvalid,s_wvalid,s_bready,s_arvalid,s_rready,
 output wire s_awready,s_wready,s_arready,output reg s_bvalid,s_rvalid,output reg [1:0] s_bresp,s_rresp,output reg [31:0] s_rdata,output wire irq,
 output wire enable_write,enable_value,recover,cancel,arm,complete,snapshot_capture,
 output reg [31:0] recover_generation,arm_id,arm_generation,arm_bytes,complete_id,complete_generation,complete_result,
 input wire [31:0] command_error,input wire command_result,
 input wire [31:0] status,transport_generation,packet_id,packet_generation,packet_count,packet_bytes,
 input wire [31:0] fifo_level,full_drop,disabled_drop,cancel_drop,stream_records,stream_packets,dma_ok,dma_failed,parse_errors,
 input wire [63:0] completion_serial,input wire [31:0] wait_arm_max_us,backpressure_max_cycles,ready_lateness_max_us,
 input wire [4:0] events,output wire [8:0] cache_word,input wire [31:0] cache_data);
 `include "telem_defs.vh"
 localparam [32:0] BASE={1'b0,`RT_BASE};
 reg ah,wh,waiting;reg [32:0] wa;reg [31:0] wd;reg [3:0] ws;
 reg [31:0] pending,mask,access_error,snap_req,snap_id,snap_watermark,observed_gen;reg snap_valid;
 reg [31:0] snapshot[0:`RT_SNAPSHOT_WORDS-1];
 wire wf=ah && wh && !s_bvalid && !waiting;
 wire address_ok=wa[32:12]==BASE[32:12] && wa[1:0]==0;
 wire door=wf && address_ok && ws==15 && wd==1;
 function [31:0] merge;input [31:0] a,b;input [3:0] st;integer i;
  begin merge=a;for(i=0;i<4;i=i+1) if(st[i]) merge[i*8+:8]=b[i*8+:8];end
 endfunction
 wire [31:0] en_merged=merge((status&`RT_STATUS_ENABLE)!=0?1:0,wd,ws);
 assign enable_write=wf && address_ok && wa[11:0]==`RT_REG_ENABLE && ws!=0 && en_merged<=1;
 assign enable_value=en_merged[0];
 assign recover=door && wa[11:0]==`RT_REG_RECOVER;
 assign cancel=door && wa[11:0]==`RT_REG_CANCEL;
 assign arm=door && wa[11:0]==`RT_REG_ARM;
 assign complete=door && wa[11:0]==`RT_REG_COMPLETE;
 assign snapshot_capture=door && wa[11:0]==`RT_REG_SNAP_SUBMIT && snap_req!=0 && snap_req>snap_watermark;
 assign cache_word=(s_araddr[11:0]-`RT_ROW_BASE)>>2;
 assign s_awready=rst_n && !ah && !s_bvalid && !waiting;
 assign s_wready=rst_n && !wh && !s_bvalid && !waiting;
 assign s_arready=rst_n && !s_rvalid;
 assign irq=|(pending & mask);
 reg [31:0] err,v,clear,combined;reg [1:0] response;integer i;
 wire [4:0] extra_events={(full_drop!=0), (parse_errors!=0),1'b0,1'b0,1'b0};
 // Drop/parse IRQs are event driven, not permanently asserted by counters.
 reg [31:0] old_drop,old_parse;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   ah<=0;wh<=0;waiting<=0;wa<=0;wd<=0;ws<=0;s_bvalid<=0;s_bresp<=0;s_rvalid<=0;s_rresp<=0;s_rdata<=0;
   pending<=0;mask<=0;access_error<=0;snap_req<=0;snap_id<=0;snap_watermark<=0;snap_valid<=0;observed_gen<=0;old_drop<=0;old_parse<=0;
   recover_generation<=0;arm_id<=0;arm_generation<=0;arm_bytes<=0;complete_id<=0;complete_generation<=0;complete_result<=0;
  end else begin
   clear=0;old_drop<=full_drop;old_parse<=parse_errors;observed_gen<=collector_generation;
   if(observed_gen!=collector_generation) snap_valid<=0;
   if(s_bvalid && s_bready) s_bvalid<=0;
   if(s_rvalid && s_rready) s_rvalid<=0;
   if(s_awvalid && s_awready) begin ah<=1;wa<=s_awaddr;end
   if(s_wvalid && s_wready) begin wh<=1;wd<=s_wdata;ws<=s_wstrb;end
   if(waiting && command_result) begin
    waiting<=0;s_bvalid<=1;s_bresp<=command_error==0?0:2;if(command_error!=0) access_error<=command_error;
   end
   if(wf) begin
    ah<=0;wh<=0;err=0;response=0;
    if(wa[32:12]!=BASE[32:12]) begin response=3;err=`RT_ERR_ADDRESS;end
    else if(wa[1:0]!=0) begin response=2;err=`RT_ERR_ALIGN;end
    else case(wa[11:0])
     `RT_REG_IRQ_MASK:begin combined=merge(mask,wd,ws);if(combined>31) err=`RT_ERR_RESERVED;else mask<=combined;end
     `RT_REG_RECOVER_GEN:recover_generation<=merge(recover_generation,wd,ws);
     `RT_REG_ARM_ID:arm_id<=merge(arm_id,wd,ws);
     `RT_REG_ARM_GEN:arm_generation<=merge(arm_generation,wd,ws);
     `RT_REG_ARM_BYTES:arm_bytes<=merge(arm_bytes,wd,ws);
     `RT_REG_COMPLETE_ID:complete_id<=merge(complete_id,wd,ws);
     `RT_REG_COMPLETE_GEN:complete_generation<=merge(complete_generation,wd,ws);
     `RT_REG_COMPLETE_RESULT:complete_result<=merge(complete_result,wd,ws);
     `RT_REG_SNAP_REQ_ID:snap_req<=merge(snap_req,wd,ws);
     `RT_REG_ENABLE:if(en_merged>1) err=`RT_ERR_RESERVED;
     `RT_REG_IRQ_PENDING,`RT_REG_RECOVER,`RT_REG_CANCEL,`RT_REG_ARM,`RT_REG_COMPLETE,`RT_REG_SNAP_SUBMIT:begin
      if(ws==0) begin end
      else if(ws!=15) err=`RT_ERR_STROBE;
      else if(wa[11:0]==`RT_REG_IRQ_PENDING) begin if(wd>31) err=`RT_ERR_RESERVED;else clear=wd;end
      else if(wd!=1) err=`RT_ERR_RESERVED;
      else if(wa[11:0]==`RT_REG_SNAP_SUBMIT) begin
       if(snap_req==0 || snap_req<snap_watermark || (snap_req==snap_watermark && !snap_valid)) err=`RT_ERR_ID;
       else if(snap_req>snap_watermark) begin snap_id<=snap_req;snap_watermark<=snap_req;snap_valid<=1;end
      end
     end
     default:err=`RT_ERR_ACCESS;
    endcase
    if(err!=0 && response==0) response=2;
    if(enable_write || recover || cancel || arm || complete) waiting<=1;
    else begin s_bvalid<=1;s_bresp<=response;end
    if(err!=0) access_error<=err;
   end
   if(snapshot_capture) begin
    for(i=0;i<`RT_SNAPSHOT_WORDS;i=i+1) snapshot[i]<=0;
    snapshot[`RT_SNAP_TIME_LO]<=time_us[31:0];snapshot[`RT_SNAP_TIME_HI]<=time_us[63:32];snapshot[`RT_SNAP_GENERATION]<=collector_generation;
    snapshot[`RT_SNAP_REVISION]<=cfg_revision;snapshot[`RT_SNAP_MASK]<={27'd0,active_mask};snapshot[`RT_SNAP_TRANSPORT_GEN]<=transport_generation;snapshot[`RT_SNAP_STATUS]<=status;
    snapshot[`RT_SNAP_FIFO_LEVEL]<=fifo_level;snapshot[`RT_SNAP_FULL_DROP]<=full_drop;snapshot[`RT_SNAP_DISABLED_DROP]<=disabled_drop;snapshot[`RT_SNAP_CANCEL_DROP]<=cancel_drop;
    snapshot[`RT_SNAP_STREAM_RECORDS]<=stream_records;snapshot[`RT_SNAP_STREAM_PACKETS]<=stream_packets;snapshot[`RT_SNAP_DMA_OK]<=dma_ok;snapshot[`RT_SNAP_DMA_FAILED]<=dma_failed;snapshot[`RT_SNAP_PARSE_ERRORS]<=parse_errors;
    snapshot[`RT_SNAP_SERIAL_LO]<=completion_serial[31:0];snapshot[`RT_SNAP_SERIAL_HI]<=completion_serial[63:32];snapshot[`RT_SNAP_PACKET_ID]<=packet_id;snapshot[`RT_SNAP_PACKET_GEN]<=packet_generation;
    snapshot[`RT_SNAP_PACKET_COUNT]<=packet_count;snapshot[`RT_SNAP_PACKET_BYTES]<=packet_bytes;snapshot[`RT_SNAP_WAIT_ARM_MAX_US]<=wait_arm_max_us;snapshot[`RT_SNAP_BACKPRESSURE_CYCLES_MAX]<=backpressure_max_cycles;snapshot[`RT_SNAP_READY_LATENESS_MAX_US]<=ready_lateness_max_us;
   end
   if(s_arvalid && s_arready) begin
    response=0;err=0;v=0;
    if(s_araddr[32:12]!=BASE[32:12]) begin response=3;err=`RT_ERR_ADDRESS;end
    else if(s_araddr[1:0]!=0) begin response=2;err=`RT_ERR_ALIGN;end
    else if(s_araddr[11:0]>=`RT_ROW_BASE && s_araddr[11:0]<`RT_ROW_BASE+`RT_ROWS*`RT_ROW_STRIDE) begin
     if(!snap_valid) err=`RT_ERR_STATE;else v=cache_data;
    end else if(s_araddr[11:0]>=`RT_SNAPSHOT_BASE && s_araddr[11:0]<`RT_SNAPSHOT_BASE+`RT_SNAPSHOT_WORDS*4) begin
     if(!snap_valid) err=`RT_ERR_STATE;else v=snapshot[(s_araddr[11:0]-`RT_SNAPSHOT_BASE)>>2];
    end else case(s_araddr[11:0])
     `RT_REG_VERSION:v=`RT_VERSION;`RT_REG_PROFILE:v=`RT_PROFILE;`RT_REG_CAPS:v=`RT_CAPS;`RT_REG_FEATURES:v=`RT_FEATURES;
     `RT_REG_STATUS:v=status;`RT_REG_IRQ_PENDING:v=pending;`RT_REG_IRQ_MASK:v=mask;`RT_REG_ACCESS_ERROR:v=access_error;
     `RT_REG_ENABLE:v=(status&`RT_STATUS_ENABLE)!=0;`RT_REG_RECOVER_GEN:v=recover_generation;
     `RT_REG_PACKET_ID:v=packet_id;`RT_REG_PACKET_GEN:v=packet_generation;`RT_REG_PACKET_COUNT:v=packet_count;`RT_REG_PACKET_BYTES:v=packet_bytes;
     `RT_REG_ARM_ID:v=arm_id;`RT_REG_ARM_GEN:v=arm_generation;`RT_REG_ARM_BYTES:v=arm_bytes;
     `RT_REG_COMPLETE_ID:v=complete_id;`RT_REG_COMPLETE_GEN:v=complete_generation;`RT_REG_COMPLETE_RESULT:v=complete_result;
     `RT_REG_SNAP_REQ_ID:v=snap_req;`RT_REG_SNAP_STATUS:v={31'd0,snap_valid};`RT_REG_SNAP_ID:v=snap_id;
     `RT_REG_FIFO_LEVEL:v=fifo_level;`RT_REG_FULL_DROP:v=full_drop;`RT_REG_DISABLED_DROP:v=disabled_drop;`RT_REG_CANCEL_DROP:v=cancel_drop;
     `RT_REG_STREAM_RECORDS:v=stream_records;`RT_REG_STREAM_PACKETS:v=stream_packets;`RT_REG_DMA_OK:v=dma_ok;`RT_REG_DMA_FAILED:v=dma_failed;`RT_REG_PARSE_ERRORS:v=parse_errors;
     `RT_REG_SERIAL_LO:v=completion_serial[31:0];`RT_REG_SERIAL_HI:v=completion_serial[63:32];`RT_REG_TRANSPORT_GEN:v=transport_generation;
     default:err=`RT_ERR_ACCESS;
    endcase
    if(err!=0 && response==0) response=2;
    s_rdata<=v;s_rresp<=response;s_rvalid<=1;if(err!=0) access_error<=err;
   end
   pending<=(pending & ~clear)|{27'd0,events}|(full_drop!=old_drop?`RT_IRQ_FIFO_DROP:0)|(parse_errors!=old_parse?`RT_IRQ_PARSE_ERROR:0);
  end
 end
endmodule
