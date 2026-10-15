// Complete-record queue and exact-byte packet transport. No DMA buffer pointers.
module rs485_telemetry #(parameter integer DEPTH=256)(
 input wire clk,rst_n,dma_ready,dma_quiescent,input wire [63:0] time_us,
 input wire event_valid,input wire [255:0] event_raw,input wire [31:0] event_generation,event_revision,
 input wire enable_write,enable_value,recover,cancel,arm,complete,
 input wire [31:0] recover_generation,arm_id,arm_generation,arm_bytes,complete_id,complete_generation,complete_result,
 output reg [31:0] command_error,output reg command_result,
 output wire [31:0] status,output reg [31:0] transport_generation,packet_id,packet_generation,packet_count,packet_bytes,
 output reg [31:0] full_drop,disabled_drop,cancel_drop,stream_records,stream_packets,dma_ok,dma_failed,
 output reg [63:0] completion_serial,output wire [31:0] fifo_level,
 output reg [31:0] wait_arm_max_us,backpressure_max_cycles,ready_lateness_max_us,
 output wire [63:0] m_data,output wire [7:0] m_keep,output wire m_last,m_valid,input wire m_ready,
 output wire [4:0] events);
 `include "telem_defs.vh"
 localparam integer PB=(DEPTH<=2) ? 1:$clog2(DEPTH);
 localparam [2:0] EMPTY=0,READY=1,LOAD=2,CRC=3,SEND=4,DONE=5;
 reg [2:0] state;reg opened,enabled,cancel_pending,exhausted,old_dma_ready;
 reg [PB-1:0] wr,rd;reg [PB:0] count;
 // A clocked read enables true ERAM mapping. Read the next queue head on the
 // pop edge; explicit forwarding defines same-address read/write behavior.
 (* ram_style="block" *) reg [543:0] memory[0:DEPTH-1];
 reg [543:0] ram_head,forward_data;reg forward_valid;
 wire [543:0] head=forward_valid ? forward_data:ram_head;
 reg [511:0] frame;reg [31:0] crc;reg [5:0] byte_index;reg [2:0] beat;
 reg [31:0] remaining,last_complete_id;reg [31:0] last_complete_generation,last_complete_result;
 reg [63:0] ready_us;reg [31:0] blocked_cycles;reg completion_event,in_flight;
 wire accept=event_valid && opened && enabled && !cancel_pending && dma_ready && !exhausted && !cancel && !recover;
 wire pop=state==SEND && m_valid && m_ready && beat==7;
 wire put=accept && ((count<DEPTH)||pop);
 wire reset_transport=old_dma_ready && !dma_ready;
 wire [PB-1:0] read_address=pop ? ((rd==DEPTH-1) ? {PB{1'b0}}:rd+1'b1):rd;
 wire [543:0] queue_record={time_us,event_raw,completion_serial,transport_generation,event_revision,event_generation,16'd64,16'd1,`RT_RECORD_MAGIC};
 // Storage has no reset; count/state/generation fence every uninitialized word.
 // For a first enqueue or a one-record pop/push, bypass the just-written data.
 always @(posedge clk) begin
  if(rst_n && put) memory[wr]<=queue_record;
  ram_head<=memory[read_address];
  forward_valid<=rst_n && put && wr==read_address;
  if(rst_n && put && wr==read_address) forward_data<=queue_record;
 end
 wire [63:0] oldest_age=time_us-head[543:480];
 wire [63:0] wait_age=time_us-ready_us;
 assign fifo_level=count;
 assign m_data=frame[beat*64+:64];assign m_keep=8'hff;
 assign m_valid=rst_n && dma_ready && state==SEND;
 assign m_last=remaining==1 && beat==7;
 assign status=(opened ? `RT_STATUS_OPEN:0)|(enabled ? `RT_STATUS_ENABLE:0)|
  (state==READY ? `RT_STATUS_PACKET_READY:0)|((state==LOAD || state==CRC || state==SEND) ? `RT_STATUS_SENDING:0)|
  (state==DONE ? `RT_STATUS_STREAM_DONE:0)|(cancel_pending ? `RT_STATUS_CANCEL_PENDING:0)|
  (dma_ready ? `RT_STATUS_DMA_READY:0)|(exhausted ? `RT_STATUS_EXHAUSTED:0);
 assign events={(accept && !put),1'b0,(reset_transport || (complete && complete_result!=0)),completion_event,state==READY};
 function [31:0] sat;input [31:0] x;input [63:0] add;reg [64:0] n;
  begin n={33'd0,x}+{1'b0,add};sat=n>65'hffffffff ? 32'hffffffff:n[31:0];end
 endfunction
 function [31:0] crc_byte;input [31:0] c;input [7:0] b;integer k;reg [31:0] t;
  begin t=c^{24'd0,b};for(k=0;k<8;k=k+1) t=t[0] ? (t>>1)^`RT_CRC_POLY : t>>1;crc_byte=t;end
 endfunction
 reg [31:0] err;reg [63:0] latency;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   state<=EMPTY;opened<=0;enabled<=0;cancel_pending<=0;exhausted<=0;old_dma_ready<=0;
   wr<=0;rd<=0;count<=0;frame<=0;crc<=0;byte_index<=0;beat<=0;remaining<=0;
   transport_generation<=0;packet_id<=0;packet_generation<=0;packet_count<=0;packet_bytes<=0;completion_serial<=0;
   command_error<=0;command_result<=0;completion_event<=0;in_flight<=0;last_complete_id<=0;last_complete_generation<=0;last_complete_result<=0;
   full_drop<=0;disabled_drop<=0;cancel_drop<=0;stream_records<=0;stream_packets<=0;dma_ok<=0;dma_failed<=0;
   wait_arm_max_us<=0;backpressure_max_cycles<=0;ready_lateness_max_us<=0;ready_us<=0;blocked_cycles<=0;
  end else begin
   command_result<=0;completion_event<=0;old_dma_ready<=dma_ready;err=0;
   if(event_valid) begin
    if(completion_serial==64'hffffffffffffffff) exhausted<=1;
    else completion_serial<=completion_serial+1'b1;
    if(!accept) disabled_drop<=sat(disabled_drop,1);else if(!put) full_drop<=sat(full_drop,1);
   end
   if(put) begin
    wr<=(wr==DEPTH-1) ? 0:wr+1'b1;
   end
   if(pop) rd<=(rd==DEPTH-1) ? 0:rd+1'b1;
   case({put,pop}) 2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;endcase
   if(state==EMPTY && opened && !cancel_pending && count!=0 && (count>=`RT_BATCH_MAX || oldest_age>=`RT_FLUSH_US)) begin
    if(packet_id==32'hffffffff) begin exhausted<=1;opened<=0;enabled<=0;end
    else begin
     packet_id<=packet_id+1'b1;packet_generation<=transport_generation;
     packet_count<=count>`RT_BATCH_MAX  ?  `RT_BATCH_MAX : count;
     packet_bytes<=(count>`RT_BATCH_MAX  ?  `RT_BATCH_MAX : count)*`RT_RECORD_BYTES;
     ready_us<=time_us;state<=READY;
     latency=oldest_age>`RT_FLUSH_US ? oldest_age-`RT_FLUSH_US:0;
     if(latency>ready_lateness_max_us) ready_lateness_max_us<=sat(0,latency);
    end
   end
   if(state==READY && wait_age>wait_arm_max_us) wait_arm_max_us<=sat(0,wait_age);
   if(m_valid && !m_ready) begin blocked_cycles<=sat(blocked_cycles,1);if(blocked_cycles>=backpressure_max_cycles) backpressure_max_cycles<=sat(blocked_cycles,1);end else blocked_cycles<=0;
   case(state)
    LOAD:begin frame<={32'd0,head[479:0]};crc<=`RT_CRC_INIT;byte_index<=0;state<=CRC;end
    CRC:begin crc<=crc_byte(crc,frame[byte_index*8+:8]);
     if(byte_index==`RT_CRC_BYTES-1) begin frame[511:480]<=crc_byte(crc,frame[byte_index*8+:8])^`RT_CRC_XOROUT;beat<=0;state<=SEND;end
     else byte_index<=byte_index+1'b1;
    end
    SEND:if(m_valid && m_ready) begin
     if(beat==7) begin
      stream_records<=sat(stream_records,1);
      if(remaining==1) begin state<=DONE;stream_packets<=sat(stream_packets,1);end
      else begin remaining<=remaining-1'b1;state<=LOAD;end
     end else beat<=beat+1'b1;
    end
   endcase
   if(enable_write) begin
    command_result<=1;
    if(enable_value && (!opened || cancel_pending || !dma_ready || exhausted)) err=`RT_ERR_STATE;
    else enabled<=enable_value;
   end
   if(arm) begin
    command_result<=1;
    if(arm_id!=packet_id || arm_id==0) err=`RT_ERR_ID;
    else if(arm_generation!=packet_generation || arm_generation!=transport_generation) err=`RT_ERR_GENERATION;
    else if(arm_bytes!=packet_bytes) err=`RT_ERR_LENGTH;
    else if(state==READY && opened && !cancel_pending && dma_ready) begin remaining<=packet_count;state<=LOAD;in_flight<=1;end
    else if(state!=LOAD && state!=CRC && state!=SEND && state!=DONE) err=`RT_ERR_STATE;
    // Same current packet ID/gen/bytes in flight or DONE is idempotent.
   end
   if(complete) begin
    command_result<=1;
    if(complete_id==last_complete_id && complete_generation==last_complete_generation && complete_id!=0) begin
     if(complete_result!=last_complete_result) err=`RT_ERR_STATE;
    end
    else if(complete_id!=packet_id || complete_id==0) err=`RT_ERR_ID;
    else if(complete_generation!=packet_generation) err=`RT_ERR_GENERATION;
    else if(complete_result>1) err=`RT_ERR_RESERVED;
    else if((complete_result==0 && state!=DONE) || (complete_result==1 && state!=LOAD && state!=CRC && state!=SEND && state!=DONE)) err=`RT_ERR_STATE;
    else begin
     completion_event<=1;in_flight<=0;last_complete_id<=complete_id;last_complete_generation<=complete_generation;last_complete_result<=complete_result;
     if(complete_result==0) begin dma_ok<=sat(dma_ok,1);state<=EMPTY;end
     else begin dma_failed<=sat(dma_failed,1);cancel_pending<=1;enabled<=0;opened<=0;end
    end
   end
   if(cancel) begin
    command_result<=1;cancel_pending<=1;enabled<=0;opened<=0;
    if(state==EMPTY || state==READY) begin cancel_drop<=sat(cancel_drop,count);count<=0;wr<=0;rd<=0;state<=EMPTY;end
   end
   if(recover) begin
    command_result<=1;
    if(recover_generation==0 || recover_generation<=transport_generation) err=`RT_ERR_GENERATION;
    else if(!dma_ready || !dma_quiescent || (state==LOAD || state==CRC || state==SEND || state==DONE)) err=`RT_ERR_BUSY;
    else begin
     cancel_drop<=sat(cancel_drop,count);count<=0;wr<=0;rd<=0;state<=EMPTY;
     transport_generation<=recover_generation;opened<=1;enabled<=0;cancel_pending<=0;last_complete_id<=0;
    end
   end
   if(enable_write || arm || complete || cancel || recover) command_error<=err;
   // Only this independent controller's primary reset fences the stream.
   if(!dma_ready) begin
    opened<=0;enabled<=0;cancel_pending<=1;state<=EMPTY;wr<=0;rd<=0;count<=0;
    if(reset_transport) begin cancel_drop<=sat(cancel_drop,count);if(in_flight) dma_failed<=sat(dma_failed,1);end
    in_flight<=0;
   end
  end
 end
endmodule
