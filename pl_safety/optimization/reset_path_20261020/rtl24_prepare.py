"""Prepare an isolated RTL candidate; retain the exact candidate21 checkpoint."""
import json, re, shutil, subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[3]; E=Path(__file__).resolve().parent

def replace(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)

def main():
    out=E/'rtl24_candidate_r1'; out.mkdir(exist_ok=False)
    before=out/'before'; before.mkdir()
    names=['motion_service.v','motion_stream_rx.v','continuous_motion.v','rs485_gp_regs.v']
    for name in names:
        p=R/('pl_rs485/rtl' if name.startswith('rs485') else 'pl_motion/rtl')/name
        shutil.copyfile(p,before/name)
    for name in names[:3]:
        shutil.copyfile(E/'management_candidate_r3'/name,out/name)
    s=(out/'motion_service.v').read_text()
    reset='captured_opcode<=0;captured_arg<=0;captured_id<=0;captured_generation<=0;captured_session<=0;captured_rebase<=0;captured_maintenance<=0;'
    s=replace(s,reset,'// Private command payload is initialized by its owner capture, not reset.')
    s=replace(s,'last_payload<=0;','')
    capture='''captured_opcode<=opcode;captured_arg<=arg;captured_id<=txn;captured_session<=session_shadow;
      captured_rebase<=rebase_shadow;captured_maintenance<=maintenance[0];captured_generation<=recover_gen;'''
    s=replace(s,capture,'')
    s=replace(s,'last_payload<=shadow_payload;','')
    extra='''
// Unreset private payload. execute/dispatch/requests and command ownership
// remain asynchronously invalidated, including reset pulses between clocks.
// A fresh nonzero transaction captures every dependency before execute.
always @(posedge clk)if(good_write && offset==`PLI_MOTION_GP_MOTION_V1_REG_SUBMIT && txn!=last_id)begin
 captured_opcode<=opcode;captured_arg<=arg;captured_id<=txn;captured_session<=session_shadow;
 captured_rebase<=rebase_shadow;captured_maintenance<=maintenance[0];captured_generation<=recover_gen;
 last_payload<=shadow_payload;
end
'''
    (out/'motion_service.v').write_text(s.replace('endmodule',extra+'endmodule'))
    s=(out/'motion_stream_rx.v').read_text()
    s=replace(s,'held<=0;record_data<=0;','')
    s=replace(s,'state<=IDLE;beat<=0;record_data<=0;crc<=','state<=IDLE;beat<=0;crc<=')
    s=replace(s,'record_data[beat*64+:64]<=s_data;held<=s_data;','')
    extra='''
// All nine words are overwritten before CHECK/PENDING can own a record.
// Only invalid internal payload differs after abort/reset; valid data, CRC,
// TLAST checks and the detecting-edge error/stop remain cycle identical.
always @(posedge clk)if(state==RX && s_valid && s_ready)begin
 record_data[beat*64+:64]<=s_data;held<=s_data;
end
'''
    (out/'motion_stream_rx.v').write_text(s.replace('endmodule',extra+'endmodule'))
    s=(before/'rs485_gp_regs.v').read_text()
    s=replace(s,'reg aw_snapshot,aw_run,w_run_clear,aw_reset,w_reset;',
      'reg aw_snapshot,aw_run,w_run_clear,aw_reset,w_reset;\n reg aw_config,w_full_one;')
    s=replace(s,'INTERLOCK_SUPPORT && control_write && ws==15 && wd==1 &&\n   wa[11:0]==`RG_REG_CFG_SUBMIT',
      'INTERLOCK_SUPPORT && write_fire && aw_config && w_full_one')
    s=replace(s,'aw_snapshot<=0;','aw_config<=0;w_full_one<=0;aw_snapshot<=0;')
    s=replace(s,'ah<=1;wa<=s_awaddr;','ah<=1;wa<=s_awaddr;\n    aw_config<=s_awaddr==BASE+`RG_REG_CFG_SUBMIT;')
    s=replace(s,'wh<=1;wd<=s_wdata;ws<=s_wstrb;',
      'wh<=1;wd<=s_wdata;ws<=s_wstrb;w_full_one<=s_wstrb==15 && s_wdata==1;')
    extra='''
// synthesis translate_off
always @(posedge clk)if(rst_n && write_fire)begin
 if(aw_config !== (write_window && wa[1:0]==0 && wa[11:0]==`RG_REG_CFG_SUBMIT))
  $fatal(1,"CFG address predecode mismatch");
 if(w_full_one !== (ws==15 && wd==1))$fatal(1,"CFG payload predecode mismatch");
end
// synthesis translate_on
'''
    (out/'rs485_gp_regs.v').write_text(s.replace('endmodule',extra+'endmodule'))
    (out/'checkpoint.json').write_text(json.dumps({'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
      'comparison':'reset_path21 final route -1.339/+0.020ns; HIGH run failed by user decision',
      'sources':names,'hashes_computed':False,'internal_cycles_added':0,
      'removed_source_reset_bits':1537,'new_control_registers':3,'status':'module validation pending'},indent=2)+'\n')
    print('Prepared isolated RTL24; original product RTL unchanged')
if __name__=='__main__':main()
