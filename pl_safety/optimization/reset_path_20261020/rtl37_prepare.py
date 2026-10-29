"""Candidate36 -> isolated37: local qualification, direct STEP stop, private data."""
import argparse,json,shutil
from pathlib import Path
from rtl24_prepare import replace
R=Path(__file__).resolve().parents[3]; E=Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser();p.add_argument('--tag',default='rtl37_candidate_r5');a=p.parse_args()
 o=E/a.tag;o.mkdir(exist_ok=False)
 for f in (E/'rtl36_candidate_r1').iterdir():
  if f.is_file():shutil.copyfile(f,o/f.name)
  elif f.name=='tests':shutil.copytree(f,o/f.name)
 def edit(name,fn):
  p=o/name;p.write_bytes(fn(p.read_text()).encode())
 def collector(s):
  s=replace(s,'output wire observe_stats_ready,','output reg protection_query_ok,output wire observe_stats_ready,')
  s=replace(s,'active_period_us<=0;active_mask<=0;','active_period_us<=0;active_mask<=0;protection_query_ok<=0;')
  s=replace(s,'active_period_us<=shadow_period;active_mask<=shadow_mask;',
   'active_period_us<=shadow_period;active_mask<=shadow_mask;protection_query_ok<=shadow_mask[4] && (|shadow_period[159:128]);')
  assertion='''
// synthesis translate_off
always @(posedge clk)if(rst_n)
 if(protection_query_ok !== (active_mask[4] && (|active_period_us[159:128])))
  $fatal(1,"query qualification must name CURRENT active configuration");
// synthesis translate_on
'''
  return s.replace('endmodule',assertion+'endmodule')
 edit('rs485_multirate.v',collector)
 edit('rs485_gp_bridge.v',lambda s:replace(replace(s,'output wire next_reset,next_config_change,','output wire protection_query_ok,output wire next_reset,next_config_change,'),'.observe_protection(completed_protection),', '.protection_query_ok(protection_query_ok),.observe_protection(completed_protection),'))
 def monitor(s):
  s=replace(s,'parameter LOOKAHEAD_TIME=0)', 'parameter LOOKAHEAD_TIME=0,parameter LOCAL_QUERY_QUAL=0)')
  s=replace(s,'output wire [63:0] next_round_start_time\n', 'output wire [63:0] next_round_start_time,input wire collector_query_ok\n')
  return replace(s,'wire polling_config_ok=collector_mask[4] && collector_periods[128+:32]!=0;',
   'wire polling_config_ok=LOCAL_QUERY_QUAL ? collector_query_ok:(collector_mask[4] && (|collector_periods[128+:32]));')
 edit('safety_interlock.v',monitor)
 edit('safety_motion_service.v',lambda s:replace(replace(s,'input wire [1:0] feedback_time_valid,','input wire collector_query_ok,input wire [1:0] feedback_time_valid,'),'.LOOKAHEAD_TIME(1)) monitor(','.LOOKAHEAD_TIME(1),.LOCAL_QUERY_QUAL(1)) monitor(.collector_query_ok(collector_query_ok),'))
 def generator(s):
  s=s.replace('input wire [1:0] feedback_time_valid,','input wire collector_query_ok,input wire [1:0] feedback_time_valid,')
  s=s.replace('.feedback_time_valid(feedback_time_valid),','.collector_query_ok(collector_query_ok),.feedback_time_valid(feedback_time_valid),')
  s=s.replace('wire [1:0] completed_time_valid;', 'wire [1:0] completed_time_valid;wire collector_query_ok;')
  s=s.replace('.feedback_time_valid(completed_time_valid),','.collector_query_ok(collector_query_ok),.feedback_time_valid(completed_time_valid),')
  return s.replace('.completed_protection(completed_protection),','.protection_query_ok(collector_query_ok),.completed_protection(completed_protection),')
 edit('generate_top.py',generator)
 # Exact modulo-u64 subtraction SIGN, without constructing all64 result bits.
 def time_logic(s):
  s=replace(s,'wire [63:0] request_round_age=request_time-next_round_reference;\nwire [63:0] event_round_age=event_time-next_round_reference;', '''wire request_before=request_time[63] ^ next_round_reference[63] ^
 (request_time[62:0]<next_round_reference[62:0]);
wire event_before=event_time[63] ^ next_round_reference[63] ^
 (event_time[62:0]<next_round_reference[62:0]);''')
  return replace(s,'{!event_round_age[63],!request_round_age[63]}','{!event_before,!request_before}')
 edit('rs485_transaction.v',time_logic)
 edit('rs485_telemetry.v',lambda s:replace(s,'''function [31:0] sat;input [31:0] x;input [63:0] add;reg [64:0] n;
  begin n={33'd0,x}+{1'b0,add};sat=n>65'hffffffff ? 32'hffffffff:n[31:0];end''', '''function [31:0] sat;input [31:0] x;input [63:0] add;reg [32:0] n;
  begin n={1'b0,x}+{1'b0,add[31:0]};
   sat=(|add[63:32]) || n[32] ? 32'hffffffff:n[31:0];end'''))
 def gp(s):
  for token in ['cfg_period_us<=0;cfg_mask<=0;','last_period<=0;last_mask<=0;','cap_data<=0;']:
   s=replace(s,token,'')
  for token in ['last_period<=shadow_period;last_mask<=shadow_mask;', 'cfg_period_us<=shadow_period;cfg_mask<=shadow_mask;', 'cap_data<=record_data;']:
   s=replace(s,token,'')
  extra='''
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
'''
  return s.replace('endmodule',extra+'endmodule')
 edit('rs485_gp_regs.v',gp)
 # The existing state/transport cancellation and notifications remain exact.
 # A separate local cofactor controls only STEP rise; existing high pulse drain
 # stays unconditional. No additional register or stopping edge is introduced.
 edit('motion_service.v',lambda s:replace(replace(s,'.PRIVATE_RX(1)) kernel(','.PRIVATE_RX(1),.FAST_STEP_STOP(1)) kernel(.fast_step_stop(fast_step_stop),'),
  'wire sequence_violation=', '''wire fast_step_stop=(private_stop && !safety_stop_seen && occupied) || private_disable ||
 stop_write || (|fault) || dma_error || req_disable || (!reset_ok && occupied) ||
 (!(HOME_SUPPORT && home_enable) && !private_stop && rst_n && reset_ok && !cancelled && !session_done && rx_error_candidate);
 wire sequence_violation='''))
 def continuous(s):
  s=replace(s,'PRIVATE_RX=0','PRIVATE_RX=0,FAST_STEP_STOP=0')
  s=replace(s,'input wire point_pending\n','input wire point_pending,input wire fast_step_stop\n')
  s=replace(s,'.HOME_SUPPORT(HOME_SUPPORT)) executor(','.HOME_SUPPORT(HOME_SUPPORT),.FAST_STEP_STOP(FAST_STEP_STOP)) executor(.fast_step_stop(fast_step_stop || (session_valid && (protocol_error || missing_next))),')
  # Declare before its first port binding. Questa rejects the earlier implicit
  # net followed by a second net declaration with an initializer.
  s=replace(s,'wire prepared_valid,prepared_push_ready,prepared_pop;', 'wire prepared_valid,prepared_push_ready,prepared_pop,prepared_storage_ready;')
  s=replace(s,'wire prepared_storage_ready=!own', 'assign prepared_storage_ready=!own')
  return s
 edit('continuous_motion.v',continuous)
 def executor(s):
  s=replace(s,'parameter HOME_SUPPORT=0','parameter HOME_SUPPORT=0,FAST_STEP_STOP=0')
  s=replace(s,'output wire plan_available\n','output wire plan_available,input wire fast_step_stop\n')
  s=replace(s,'step<=0;','')
  s=replace(s,'step[i]<=0;','')
  assert s.count('step[i]<=1;')==2;s=s.replace('step[i]<=1;','')
  extra='''
// Sole STEP register owner. Current safety sources bypass receiver abort/error
// and management feedback. Already-high pulses keep their original drain edge.
wire step_block=FAST_STEP_STOP ? fast_step_stop:safety;
integer step_lane;
always @(posedge clk or negedge rst_n)begin
 if(!rst_n)step<=0;
 else for(step_lane=0;step_lane<4;step_lane=step_lane+1)begin
  if(step[step_lane] && high_left[step_lane]==1)step[step_lane]<=0;
  if(!step_block)begin
   if(step_lane<3 && (own || (HOME_SUPPORT && home_enable)) && !(|home_bad) &&
      home_candidate[step_lane] && hr[step_lane] && state==IDLE &&
      !(|disabling) && !(|fault_latched) && enabled[step_lane] && !step[step_lane] &&
      !(dir[step_lane]!=home_direction[step_lane] && reached(edge_age[step_lane],q[step_lane])))
    step[step_lane]<=1;
   if(state==RUN && slot_due && emission_ok && moving[step_lane] && emit[step_lane])
    step[step_lane]<=1;
  end
 end
end
// synthesis translate_off
always @(posedge clk)if(rst_n && FAST_STEP_STOP &&
 ((state==RUN && slot_due && emission_ok && (|(moving & emit))) ||
  ((own || (HOME_SUPPORT && home_enable)) && !(|home_bad) && (|home_candidate))))
 if(step_block !== safety)$fatal(1,"direct STEP stop cofactor differs: block=%b safety=%b state=%d own=%b hr=%b home_candidate=%b fast=%b",step_block,safety,state,own,hr,home_candidate,fast_step_stop);
// synthesis translate_on
'''
  return s.replace('endmodule',extra+'endmodule')
 edit('motion_executor.v',executor)
 namespace={'__file__':str(R/'pl_safety/generate_top.py'),'__name__':'candidate_generator'}
 exec(compile((o/'generate_top.py').read_text(),str(o/'generate_top.py'),'exec'),namespace)
 for name,text in namespace['render']().items():
  if name.startswith('interlock_'):(o/name).write_bytes(text.encode())
 tb=o/'tests/tb_interlock.v';tb.write_bytes(replace(tb.read_text(),'2\'d0,unused_next_round);','2\'d0,unused_next_round,1\'b0);').encode())
 (o/'local_stop_notes.json').write_text(json.dumps(dict(hashes_computed=False,external_cycles_added=0,
  private_payload_source_reset_bits_removed=586,new_async_query_flag_bits=1,
  changes=['atomic current config qualification','direct STEP rise stop cofactor; original high pulse drain',
   'modulo timestamp sign via XOR/borrow','33bit saturating add','GP private captured/config/replay payload noreset'],
  status='isolated; validation pending'),indent=2)+'\n')
 print('Prepared isolated RTL37')
if __name__=='__main__':main()
