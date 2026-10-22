`timescale 1ns/1ps
`include "generated/interface_defs.vh"
// Store one complete record. CRC runs one byte/cycle, never in the STEP path.
// abort invalidates transport ownership, not the motion/time reset domain.
module motion_stream_rx(
 input wire clk,rst_n,abort,link_ready,
 input wire arm,input wire [31:0] arm_count,
 output wire arm_ready,packet_busy,partial_empty,
 input wire [63:0] s_data,input wire [7:0] s_keep,input wire s_last,s_valid,
 output wire s_ready,
 output wire point_valid,input wire point_ready,
 output wire [63:0] point_session,duration_tick,
 output wire [31:0] point_sequence,output wire point_end,
 output wire [3:0] point_mask,output wire [255:0] point_target,
 output wire error,output wire error_candidate,output reg packet_closed,output reg [31:0] packet_count,output reg next_packet_empty
);
 localparam IDLE=0,RX=1,CRC=2,CHECK=3,PENDING=4;
 reg [2:0] state;reg [3:0] beat;reg [3:0] byte_index,byte_limit;
 reg [63:0] held;reg [575:0] record_data;reg [31:0] crc,last_index,completed;
 reg final_record;
 reg checked_bad;
 function [31:0] crc_byte;
  input [31:0] c;input [7:0] b;integer k;reg [31:0] x;
  begin x=c^{24'd0,b};for(k=0;k<8;k=k+1) x=x[0] ? (x>>1)^`PLI_MOTION_GP_MOTION_V1_CRC_REFLECTED_POLYNOMIAL : x>>1;crc_byte=x;end
 endfunction
 assign point_session=record_data[`PLI_MOTION_STREAM_V2_SESSION_ID_OFFSET*8+:64];
 assign point_sequence=record_data[`PLI_MOTION_STREAM_V2_SEQUENCE_OFFSET*8+:32];
 assign duration_tick=record_data[`PLI_MOTION_STREAM_V2_DURATION_TICK_OFFSET*8+:64];
 assign point_end=record_data[`PLI_MOTION_STREAM_V2_FLAGS_OFFSET*8];
 assign point_mask=record_data[`PLI_MOTION_STREAM_V2_AXIS_MASK_OFFSET*8+:4];
 assign point_target=record_data[`PLI_MOTION_STREAM_V2_TARGET0_OFFSET*8+:256];
 wire bad_format=record_data[`PLI_MOTION_STREAM_V2_MAGIC_OFFSET*8+:32]!=`PLI_MOTION_STREAM_V2_MAGIC_VALUE ||
  record_data[`PLI_MOTION_STREAM_V2_VERSION_OFFSET*8+:16]!=`PLI_MOTION_STREAM_V2_VERSION_VALUE ||
  record_data[`PLI_MOTION_STREAM_V2_LENGTH_OFFSET*8+:16]!=`PLI_MOTION_STREAM_V2_LENGTH_VALUE ||
  record_data[`PLI_MOTION_STREAM_V2_RESERVED_OFFSET*8+:32]!=0 ||
  record_data[`PLI_MOTION_STREAM_V2_FLAGS_OFFSET*8+:16]>1 ||
  record_data[`PLI_MOTION_STREAM_V2_AXIS_MASK_OFFSET*8+:16]>15 || point_session==0 ||
  duration_tick==0 || duration_tick>(64'hffffffffffffffff/`PLI_MOTION_GP_MOTION_V1_CYCLES_PER_TICK) ||
  (!point_mask[0] && point_target[0+:64]!=0) || (!point_mask[1] && point_target[64+:64]!=0) ||
  (!point_mask[2] && point_target[128+:64]!=0) || (!point_mask[3] && point_target[192+:64]!=0);
 wire [31:0] next_crc=crc_byte(crc,held[byte_index*8+:8]);
 assign packet_busy=state!=IDLE;
 assign partial_empty=state==IDLE;
 assign arm_ready=rst_n && link_ready && !abort && state==IDLE;
 assign s_ready=rst_n && link_ready && !abort && state==RX;
 // Precompute the terminal index at ARM. The modulo-32 identity
 // completed+1==count <=> completed==count-1 also preserves count==0.
 // Keep the detecting-edge error path free of a 32-bit carry chain.
 wire is_final_record=completed==last_index;
 // Raw predicate is private: the service applies the exact abort cofactor.
 wire bad_shape=s_keep!=8'hff || s_last!=(beat==8 && is_final_record);
 assign error_candidate=(s_valid && link_ready && state==RX && bad_shape) || (state==CHECK && checked_bad);
 // Error is visible on the detecting edge, so the kernel cannot launch STEP.
 assign error=rst_n && !abort && error_candidate;
 assign point_valid=rst_n && link_ready && !abort && state==PENDING;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin checked_bad<=0;state<=IDLE;beat<=0;byte_index<=0;byte_limit<=0;crc<=32'hffffffff;last_index<=0;completed<=0;final_record<=0;packet_closed<=0;packet_count<=0;end
  else begin
   packet_closed<=0;
   if(abort || error || !link_ready)begin state<=IDLE;beat<=0;crc<=32'hffffffff;completed<=0;last_index<=0;end
   else case(state)
    IDLE:if(arm && arm_ready)begin last_index<=arm_count-32'd1;completed<=0;beat<=0;crc<=32'hffffffff;state<=RX;end
    RX:if(s_valid && s_ready)begin
     byte_index<=0;byte_limit<=beat==8 ? 4:8;
     final_record<=is_final_record;state<=CRC;
    end
    CRC:begin
     crc<=next_crc;byte_index<=byte_index+1'b1;
     if(byte_index+1==byte_limit)begin if(beat==8)begin checked_bad<=bad_format || ((~next_crc)!=record_data[`PLI_MOTION_STREAM_V2_CRC_OFFSET*8+:32]);state<=CHECK;end else begin beat<=beat+1'b1;state<=RX;end end
    end
    CHECK:state<=PENDING;
    PENDING:if(point_ready)begin
     completed<=completed+1;beat<=0;crc<=32'hffffffff;
     if(final_record)begin state<=IDLE;packet_closed<=1;packet_count<=packet_count+1;end else state<=RX;
    end
    default:state<=IDLE;
   endcase
  end
 end

// Exact next packet-empty predicate, sampled with the mailbox qualification.
// It describes the SAME edge as the source state; error/abort stay direct.
always @*begin
 next_packet_empty=state==IDLE;
 if(!rst_n)next_packet_empty=1;
 else if(abort || error || !link_ready)next_packet_empty=1;
 else case(state)
  IDLE:if(arm && arm_ready)next_packet_empty=0;
  RX,CRC,CHECK:next_packet_empty=0;
  PENDING:if(point_ready)next_packet_empty=final_record;
  default:next_packet_empty=1;
 endcase
end

// All nine words are overwritten before CHECK/PENDING can own a record.
// Only invalid internal payload differs after abort/reset; valid data, CRC,
// TLAST checks and the detecting-edge error/stop remain cycle identical.
always @(posedge clk)if(state==RX && s_valid && s_ready)begin
 record_data[beat*64+:64]<=s_data;held<=s_data;
end
endmodule
