"""Apply the same proven clocked queue to raw records with exact private cofactors."""
import argparse,json,re,shutil
from pathlib import Path
from rtl24_prepare import replace
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--tag',default='rtl32_candidate_r2');a=p.parse_args();assert re.fullmatch('[A-Za-z0-9_-]+',a.tag)
 out=E/a.tag;out.mkdir(exist_ok=False)
 for f in (E/'rtl31_candidate_r1').glob('*'):
  if f.is_file():shutil.copyfile(f,out/f.name)
 s=(out/'motion_stream_rx.v').read_text()
 s=replace(s,'output reg next_packet_empty','output reg next_packet_empty,output wire point_pending')
 s=replace(s,'assign point_valid=rst_n && link_ready && !abort && state==PENDING;',
  'assign point_pending=rst_n && link_ready && state==PENDING;\n assign point_valid=point_pending && !abort;')
 (out/'motion_stream_rx.v').write_bytes(s.encode())
 s=(out/'motion_planner.v').read_text()
 s=replace(s,'output wire plan_pending','output wire plan_pending,output wire req_available')
 s=replace(s,'assign req_ready=state==IDLE && !cancel;', 'assign req_available=state==IDLE;\nassign req_ready=req_available && !cancel;')
 (out/'motion_planner.v').write_bytes(s.encode())
 s=(out/'continuous_motion.v').read_text()
 s=replace(s,'parameter HOME_SUPPORT=0','parameter HOME_SUPPORT=0,PRIVATE_RX=0')
 s=replace(s,'output reg next_session_empty','output reg next_session_empty,input wire point_pending')
 s=replace(s,'wire planner_ready,planner_busy,planner_valid,planner_pending,planner_error,executor_error;',
  'wire planner_available,planner_ready,planner_busy,planner_valid,planner_pending,planner_error,executor_error;')
 s=replace(s,'motion_fifo #(.WIDTH(421),.DEPTH(FIFO_DEPTH),.SPARE_SLOT(1)) raw_fifo(',
  '''// A source ownership bit is valid independently of current abort.
 // On every non-flushing cycle this equals the original raw_push request;
 // speculative writes while flushing cannot publish a record or an event.
 wire raw_storage_request=(PRIVATE_RX ? point_pending:point_valid) && !old_record && !invalid_order;
 wire raw_storage_ready=planner_available && session_valid;
 motion_plan_fifo #(.WIDTH(421),.DEPTH(FIFO_DEPTH)) raw_fifo(''')
 s=replace(s,'.flush(flush_all),.in_valid(raw_push),.in_ready(raw_ready)',
  '.flush(flush_all),.in_valid(raw_storage_request),.in_ready(raw_ready)')
 s=replace(s,'.out_valid(raw_valid),.out_ready(raw_pop),.out_data(raw_data),.level(fifo_level));',
  '.out_valid(raw_valid),.out_ready(raw_pop),.out_data(raw_data),.level(fifo_level),.storage_out_ready(raw_storage_ready),.storage_valid());')
 s=replace(s,'.req_ready(planner_ready),.busy(planner_busy)', '.req_ready(planner_ready),.req_available(planner_available),.busy(planner_busy)')
 extra='''
// synthesis translate_off
always @(posedge clk)if(rst_n && !flush_all)begin
 if(raw_storage_request !== raw_push)$fatal(1,"raw private producer cofactor mismatch");
 if(raw_storage_ready !== raw_pop)$fatal(1,"raw private consumer cofactor mismatch");
end
// synthesis translate_on
'''
 (out/'continuous_motion.v').write_bytes(s.replace('endmodule',extra+'endmodule').encode())
 s=(out/'motion_service.v').read_text()
 s=replace(s,'wire rx_error,rx_error_candidate,rx_arm_ready,packet_busy,partial_empty,packet_closed;',
  'wire rx_pending,rx_error,rx_error_candidate,rx_arm_ready,packet_busy,partial_empty,packet_closed;')
 s=replace(s,'.next_packet_empty(next_packet_empty));','.next_packet_empty(next_packet_empty),.point_pending(rx_pending));')
 s=replace(s,'.EN_ACTIVE_LEVEL(EN_ACTIVE_LEVEL),.HOME_SUPPORT(HOME_SUPPORT)) kernel(',
  '.EN_ACTIVE_LEVEL(EN_ACTIVE_LEVEL),.HOME_SUPPORT(HOME_SUPPORT),.PRIVATE_RX(1)) kernel(')
 prefix,kernel=s.split('continuous_motion #(',1)
 kernel=replace(kernel,'.point_valid(rx_valid),.point_ready(rx_ready),.point_session(rx_session),.duration_tick(rx_duration),',
  '.point_valid(rx_valid),.point_pending(rx_pending),.point_ready(rx_ready),.point_session(rx_session),.duration_tick(rx_duration),')
 s=prefix+'continuous_motion #('+kernel
 (out/'motion_service.v').write_bytes(s.encode())
 (out/'raw_clocked_notes.json').write_text(json.dumps({'hashes_computed':False,'external_cycles_added':0,
  'raw_capacity':64,'prepared_capacity':8,'record_widths':[421,1197],
  'cofactor':'FIFO physical push/pop consume source/consumer ownership before current abort gates; public valid/ready/count still match original',
  'memory':'same prefetch+forward module as31, full capacity and same-address forwarding retained',
  'status':'isolated module validation pending'},indent=2)+'\n')
 print('Prepared isolated RTL32 raw and prepared clocked queues; product remains29')
if __name__=='__main__':main()
