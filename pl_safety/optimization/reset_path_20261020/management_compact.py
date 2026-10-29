"""Readable equivalent of the mechanically verified management projection."""
import argparse,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--tag',required=True);a=p.parse_args();assert re.fullmatch('[A-Za-z0-9_-]+',a.tag)
 out=HERE/a.tag;out.mkdir(exist_ok=False)
 s=(ROOT/'pl_motion/rtl/motion_stream_rx.v').read_text()
 s=s.replace('output reg [31:0] packet_count','output reg [31:0] packet_count,output reg next_packet_empty')
 extra='''
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
'''
 (out/'motion_stream_rx.v').write_text(s.replace('endmodule',extra+'endmodule'))
 s=(ROOT/'pl_motion/rtl/continuous_motion.v').read_text()
 s=s.replace('output wire [2:0] home_fault','output wire [2:0] home_fault,output reg next_session_empty')
 extra='''
// Project the original session-valid assignments with their original priority.
always @*begin
 next_session_empty=!session_valid;
 if(!rst_n)next_session_empty=1;
 else if(cancel_now || finish_now)next_session_empty=1;
 else if(open_req)begin
  if(maintenance_ok && !(|fault_latched) && open_session_id!=0 && open_session_id!=session_id &&
     !rebase_req && !enable_req && !start_req && !resume_req)next_session_empty=0;
 end
end
'''
 (out/'continuous_motion.v').write_text(s.replace('endmodule',extra+'endmodule'))
 s=(ROOT/'pl_motion/rtl/motion_service.v').read_text()
 old='wire idle_admission_fence=!session_valid && !command_busy && !ah && !wh &&\n  !packet_busy &&\n  !(HOME_SUPPORT && home_owner);';assert s.count(old)==1
 s=s.replace(old,'''wire next_session_empty,next_packet_empty;
 reg management_clear_q;
 wire idle_admission_fence=management_clear_q && !(HOME_SUPPORT && home_owner);''')
 old='.packet_closed(packet_closed),.packet_count(packet_count));';assert s.count(old)==1
 s=s.replace(old,'.packet_closed(packet_closed),.packet_count(packet_count),.next_packet_empty(next_packet_empty));')
 old='.safety_invalidate(safety_invalidate),.safety_pulse_safe(safety_pulse_safe),.home_fault(home_fault));';assert s.count(old)==1
 s=s.replace(old,old[:-2]+',.next_session_empty(next_session_empty));')
 extra='''
// Project AH/WH/command ownership using the original assignment priorities.
// Combining NEXT source values makes this a CURRENT qualification register,
// rather than a delayed idle grant. All safety/contact/STOP controls stay direct.
reg management_ah_next,management_wh_next,management_command_next;
always @*begin
 management_ah_next=ah;management_wh_next=wh;management_command_next=command_busy;
 if(!rst_n)begin management_ah_next=0;management_wh_next=0;management_command_next=0;end
 else begin
  if(s_awvalid && s_awready)management_ah_next=1;
  if(s_wvalid && s_wready)management_wh_next=1;
  if(write_fire)begin
   management_ah_next=0;management_wh_next=0;
   if(good_write && offset==`PLI_MOTION_GP_MOTION_V1_REG_SUBMIT && txn!=last_id)management_command_next=1;
  end
  if(execute)begin
   management_command_next=0;
   if(guarded_command_ok && !(stop_write || (|fault) || dma_error || !reset_ok || rx_error))
    management_command_next=1;
  end else if(dispatch_pending)begin
   management_command_next=req_pause || req_disable;
   if(stop_write || rx_error || (|fault) || dma_error || !reset_ok)management_command_next=0;
  end else if(command_busy)begin
   if((captured_opcode==`PLI_CMD_PAUSE && paused) ||
      (captured_opcode==`PLI_CMD_DISABLE && !core_busy && !(|(enabled & captured_arg[3:0]))))management_command_next=0;
   else if(stop_write || rx_error || (|fault) || dma_error || !reset_ok ||
           (session_done && captured_opcode==`PLI_CMD_PAUSE))management_command_next=0;
  end
 end
end
always @(posedge clk or negedge rst_n)
 if(!rst_n)management_clear_q<=1;
 else management_clear_q<=next_session_empty && next_packet_empty &&
      !management_ah_next && !management_wh_next && !management_command_next;
// synthesis translate_off
always @(posedge clk)if(rst_n)
 if(management_clear_q !== (!session_valid && !packet_busy && !ah && !wh && !command_busy))
  $fatal(1,"management current-state projection mismatch");
// synthesis translate_on
'''
 (out/'motion_service.v').write_text(s.replace('endmodule',extra+'endmodule'))
 print('PASS compact management projection candidate, one FF')
if __name__=='__main__':main()
