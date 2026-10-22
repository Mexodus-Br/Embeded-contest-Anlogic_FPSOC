"""Capture time qualification on the original EMIT edge, against next round."""
import json,shutil
from pathlib import Path
from rtl24_prepare import replace
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 out=E/'rtl36_candidate_r1';out.mkdir(exist_ok=False)
 for f in (E/'rtl35_candidate_r1').glob('*'):
  if f.is_file():shutil.copyfile(f,out/f.name)
 s=(R/'pl_rs485/rtl/rs485_transaction.v').read_text()
 s=replace(s,'output reg [5:0] protection_decoded);',
  'output reg [5:0] protection_decoded,input wire [63:0] next_round_reference,output reg [1:0] protection_time_valid);')
 extra='''
// Capture the SAME existing raw-record edge, with the round value that the
// monitor will hold after this edge. No extra push/detection stage. The two
// private bits need no reset: push already invalidates them asynchronously.
wire [63:0] request_round_age=request_time-next_round_reference;
wire [63:0] event_round_age=event_time-next_round_reference;
always @(posedge clk)if(state==EMIT)
 protection_time_valid<=INTERLOCK_PREDECODE ? {!event_round_age[63],!request_round_age[63]}:2'd0;
'''
 (out/'rs485_transaction.v').write_bytes(s.replace('endmodule',extra+'endmodule').encode())
 s=(out/'rs485_multirate.v').read_text()
 s=replace(s,'output wire observe_stats_ready);',
  'output wire observe_stats_ready,input wire [63:0] next_round_reference,output wire [1:0] observe_time_valid);')
 s=replace(s,'.protection_decoded(observe_protection),',
  '.protection_decoded(observe_protection),.next_round_reference(next_round_reference),.protection_time_valid(observe_time_valid),')
 (out/'rs485_multirate.v').write_bytes(s.encode())
 s=(out/'rs485_gp_bridge.v').read_text()
 s=replace(s,'output wire next_reset,next_config_change);',
  'output wire next_reset,next_config_change,input wire [63:0] next_round_reference,output wire [1:0] completed_time_valid);')
 s=replace(s,'.observe_protection(completed_protection),',
  '.observe_protection(completed_protection),.next_round_reference(next_round_reference),.observe_time_valid(completed_time_valid),')
 (out/'rs485_gp_bridge.v').write_bytes(s.encode())
 s=(out/'safety_interlock.v').read_text()
 s=replace(s,'parameter LOOKAHEAD_WRAP=0)', 'parameter LOOKAHEAD_WRAP=0,parameter LOOKAHEAD_TIME=0)')
 s=replace(s,'input wire next_collector_reset,next_config_change,next_config_apply\n',
  'input wire next_collector_reset,next_config_change,next_config_apply,\n input wire [1:0] feedback_time_valid,output wire [63:0] next_round_start_time\n')
 s=replace(s,'wire [31:0] next_round_generation=restart ?',
  'assign next_round_start_time=restart ? time_us:round_start;\n wire [31:0] next_round_generation=restart ?')
 s=replace(s,'!request_age[63] && !event_age[63] && round_valid &&',
  '(LOOKAHEAD_TIME ? (&feedback_time_valid):(!request_age[63] && !event_age[63])) && round_valid &&')
 extra='''
// synthesis translate_off
always @(posedge clk)if(rst_n && LOOKAHEAD_TIME && feedback_commit)
 if(feedback_time_valid !== {!event_age[63],!request_age[63]})
  $fatal(1,"same-EMIT time qualification differs from current raw/round timestamps");
// synthesis translate_on
'''
 (out/'safety_interlock.v').write_bytes(s.replace('endmodule',extra+'endmodule').encode())
 s=(out/'safety_motion_service.v').read_text()
 s=replace(s,'input wire feedback_commit,input wire [255:0] feedback_raw,input wire [5:0] feedback_predecoded,',
  'input wire feedback_commit,input wire [255:0] feedback_raw,input wire [5:0] feedback_predecoded,\n input wire [1:0] feedback_time_valid,output wire [63:0] feedback_round_reference,')
 s=replace(s,'.LOOKAHEAD_WRAP(1)) monitor(','.LOOKAHEAD_WRAP(1),.LOOKAHEAD_TIME(1)) monitor(.feedback_time_valid(feedback_time_valid),.next_round_start_time(feedback_round_reference),')
 s=replace(s,'assign il_run_permit=1;', 'assign feedback_round_reference=0;assign il_run_permit=1;')
 (out/'safety_motion_service.v').write_bytes(s.encode())
 s=(out/'generate_top.py').read_text()
 s=replace(s,'input wire feedback_commit,input wire [255:0] feedback_raw,input wire [5:0] feedback_predecoded,',
  'input wire feedback_commit,input wire [255:0] feedback_raw,input wire [5:0] feedback_predecoded,\ninput wire [1:0] feedback_time_valid,output wire [63:0] feedback_round_reference,')
 s=s.replace('.feedback_predecoded(feedback_predecoded),', '.feedback_predecoded(feedback_predecoded),.feedback_time_valid(feedback_time_valid),.feedback_round_reference(feedback_round_reference),')
 s=s.replace('.feedback_predecoded(completed_protection),', '.feedback_predecoded(completed_protection),.feedback_time_valid(completed_time_valid),.feedback_round_reference(completed_round_reference),')
 s=replace(s,"events+'\\nwire [5:0] completed_protection;", "events+'\\nwire [63:0] completed_round_reference;wire [1:0] completed_time_valid;\\nwire [5:0] completed_protection;")
 s=replace(s,"'.completed_protection(completed_protection),.interlock_idle", "'.completed_protection(completed_protection),.next_round_reference(completed_round_reference),.completed_time_valid(completed_time_valid),.interlock_idle")
 (out/'generate_top.py').write_bytes(s.encode())
 namespace={'__file__':str(R/'pl_safety/generate_top.py'),'__name__':'isolated_generator'}
 exec(compile(s,str(R/'pl_safety/generate_top.py'),'exec'),namespace)
 for name,text in namespace['render']().items():
  if name.startswith('interlock_'):(out/name).write_bytes(text.encode())
 # Only add bindings for new private ports; all existing monitor assertions stay.
 tests=out/'tests';tests.mkdir()
 tb=(R/'pl_safety/tests/tb_interlock.v').read_text()
 tb=replace(tb,"32'd0,32'd0,6'd0,1'b0,1'b0,1'b0);", "32'd0,32'd0,6'd0,1'b0,1'b0,1'b0,2'd0,unused_next_round);")
 tb=replace(tb,'integer checks=0,i,j;', 'wire [63:0] unused_next_round;integer checks=0,i,j;')
 (tests/'tb_interlock.v').write_bytes(tb.encode())
 (out/'fresh_time_notes.json').write_text(json.dumps({'hashes_computed':False,'external_cycles_added':0,'new_nonreset_bits':2,
  'captured_edge':'Original transaction.EMIT captures raw256/protection6/time2 atomically; monitor consumes the original push edge',
  'reference':'monitor restart ? current time : stored round_start is the exact round_start after EMIT edge',
  'preserved':'complete raw timestamps, signed modulo-age qualification, round/config/generation/RESET competition, original stop edge and FIFO/cache independence',
  'legacy':'LOOKAHEAD_TIME default0; INTERLOCK_PREDECODE default0; no ABI/format/numeric changes',
  'status':'isolated producer/monitor/whole-safety validation pending'},indent=2)+'\n')
 print('Prepared RTL36 same-EMIT time qualification, no added detection cycle')
if __name__=='__main__':main()
