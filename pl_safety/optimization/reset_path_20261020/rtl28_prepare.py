"""Move reset masking to narrow read ports and remove serial abort cofactors."""
import json,shutil
from pathlib import Path
from rtl24_prepare import replace
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 out=E/'rtl28_candidate_r1';out.mkdir(exist_ok=False)
 for f in (E/'rtl27_candidate_r1').glob('*'):
  if f.is_file():shutil.copyfile(f,out/f.name)
 s=(out/'rs485_latest_cache.v').read_text()
 s=replace(s,"{flags,updates[i],(last_written[i] ? last_rev[i]:32'd0),(last_written[i] ? last_gen[i]:32'd0),(good_written[i] ? good_rev[i]:32'd0),(good_written[i] ? good_gen[i]:32'd0),last_written[i],good_written[i],last_pointer[i],good_pointer[i]}",
  '{flags,updates[i],last_rev[i],last_gen[i],good_rev[i],good_gen[i],last_written[i],good_written[i],last_pointer[i],good_pointer[i]}')
 s=replace(s,'2,3,4,5,6:snapshot_data=read_meta[6+(word_index-2)*32+:32];',
  "2,3:snapshot_data=read_meta[4] ? read_meta[6+(word_index-2)*32+:32]:32'd0;\n    4,5:snapshot_data=read_meta[5] ? read_meta[6+(word_index-2)*32+:32]:32'd0;\n    6:snapshot_data=read_meta[134+:32];")
 (out/'rs485_latest_cache.v').write_text(s)
 s=(out/'rs485_multirate.v').read_text()
 s=replace(s,'output wire next_config_change);','output wire next_config_change,output wire observe_stats_ready);')
 s=replace(s,"if(view<TASKS) assign observe_tasks[view*160 +:160]=initialized ? {max_late[view],missed[view],valid_count[view],sent[view],scheduled[view]}:160'd0;",
  'if(view<TASKS) assign observe_tasks[view*160 +:160]={max_late[view],missed[view],valid_count[view],sent[view],scheduled[view]};')
 s=replace(s,'assign observe_push=push;','assign observe_stats_ready=initialized;\n assign observe_push=push;')
 (out/'rs485_multirate.v').write_text(s)
 s=(out/'rs485_gp_regs.v').read_text()
 s=replace(s,'SLAVE_COUNT=3,INTERLOCK_SUPPORT=0)', 'SLAVE_COUNT=3,INTERLOCK_SUPPORT=0,STATS_VALID_SUPPORT=0)')
 s=replace(s,'output wire reset_commit,output wire next_reset);','output wire reset_commit,output wire next_reset,input wire observe_stats_ready);')
 s=replace(s,'reg r_record;', 'reg snapshot_stats_ready;\n reg r_record;')
 s=replace(s,'snap_valid<=0;r_record<=0;', 'snap_valid<=0;snapshot_stats_ready<=0;r_record<=0;')
 s=replace(s,'else value=snapshot[(s_araddr[11:0]-`RG_SNAPSHOT_BASE)>>2];',
  "else if(STATS_VALID_SUPPORT && !snapshot_stats_ready && s_araddr[11:0]>=`RG_TASK_BASE) value=0;\n     else value=snapshot[(s_araddr[11:0]-`RG_SNAPSHOT_BASE)>>2];")
 s=replace(s,'if(snapshot_fire) begin','if(snapshot_fire) begin\n    snapshot_stats_ready<=observe_stats_ready;')
 (out/'rs485_gp_regs.v').write_text(s)
 s=(out/'rs485_gp_bridge.v').read_text()
 s=replace(s,'wire run,collector_rst_n,','wire observe_stats_ready;\nwire run,collector_rst_n,')
 s=replace(s,'.observe_tasks(tasks),.observe_nodes(nodes));', '.observe_stats_ready(observe_stats_ready),.observe_tasks(tasks),.observe_nodes(nodes));') if s.count('.observe_tasks(tasks),.observe_nodes(nodes));')==1 else s
 # The same named views connect both producer and consumer.
 s=s.replace('.observe_tasks(tasks),.observe_nodes(nodes));','.observe_stats_ready(observe_stats_ready),.observe_tasks(tasks),.observe_nodes(nodes));')
 s=replace(s,'rs485_gp_regs #(.FIFO_DEPTH(FIFO_DEPTH),','rs485_gp_regs #(.STATS_VALID_SUPPORT(1),.FIFO_DEPTH(FIFO_DEPTH),')
 (out/'rs485_gp_bridge.v').write_text(s)
 s=(out/'motion_service.v').read_text()
 s=replace(s,'wire cancel_transport=external_cancel || rx_error || cancelled || session_done;',
 '''// receiver.error = rst_n && !abort && candidate; abort is already in
 // this OR. Apply the exact cofactor instead of routing stop through the
 // receiver error gate and back into transport cancellation.
 wire cancel_transport=external_cancel || cancelled || session_done || (rst_n && rx_error_candidate);''')
 s=replace(s,'link_ready<=0;link_generation<=0;software_generation<=0;', '')
 s=replace(s,'link_ready<=0;\n    if(link_ready)link_generation<=link_generation+1\'b1;', '')
 s=replace(s,'if(cmd_recover)begin link_ready<=1;link_generation<=link_generation+1\'b1;software_generation<=captured_generation;end','')
 extra='''
// Recovery's maintenance predicate includes receiver.IDLE (partial_empty).
// Therefore receiver.error is identically zero for this opcode. Keep the
// original detection edge and last-assignment priority over cancellation,
// without dragging unrelated START/executor-ready muxes into generation CE.
wire recover_commit=cmd_recover && maintenance_ok && !link_ready && reset_ok &&
 !(|fault) && !dma_error && captured_generation>software_generation && !stop_write;
always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin link_ready<=0;link_generation<=0;software_generation<=0;end
 else begin
  if(cancel_transport)begin link_ready<=0;if(link_ready)link_generation<=link_generation+1'b1;end
  if(recover_commit)begin link_ready<=1;link_generation<=link_generation+1'b1;software_generation<=captured_generation;end
 end
end
// synthesis translate_off
always @(posedge clk)if(rst_n)begin
 if(cancel_transport !== (external_cancel || rx_error || cancelled || session_done))
  $fatal(1,"transport cancel cofactor mismatch");
 if(recover_commit !== (cmd_recover && guarded_command_ok &&
   !(stop_write || (|fault) || dma_error || !reset_ok || rx_error)))
  $fatal(1,"recovery qualification cofactor mismatch");
end
// synthesis translate_on
'''
 (out/'motion_service.v').write_text(s.replace('endmodule',extra+'endmodule'))
 (out/'narrow_read_notes.json').write_text(json.dumps({'hashes_computed':False,'internal_cycles_added':0,
  'reason':'rtl27 broad zero masks added 2437 mapped LUT6 equivalents; gate -3.652ns, rejected without P&R',
  'change':'cache identity masks only selected 32bit output; GP freezes statistics validity and masks only selected 32bit read',
  'control':'exact OR abort cofactor plus opcode-local recovery generation ownership; no new safety pipeline'},indent=2)+'\n')
 print('Prepared RTL28 narrow read masking and local cancellation/recovery')
if __name__=='__main__':main()
