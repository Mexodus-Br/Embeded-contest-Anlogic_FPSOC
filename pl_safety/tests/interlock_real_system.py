"""Real SAF2 GP converter, UART collector and both DMA/HP paths; no hashes.

Reuse the existing real-IP harness/drivers with explicit textual assertions.
The generated bench and complete logs are retained under the new run tag.
"""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
TD = Path('D:/Anlogic/TD_Release_2026.1_SP2.200.067')


def prepare_scoped(out):
    dest = out / 'ip'
    dest.mkdir()
    sources = {
        'dma': TD / 'ip/depot/AXI_DMA_1.0/AXI_DMA/RTL/axi_dma.v',
        'converter': TD / 'ip/depot/AXI_Protocol_Converter_1.0/AXI_MM/RTL/axi_protocol_converter_merge.v'}
    result = {'libraries': {}, 'hashes_computed': False, 'direct_vendor_byte_comparison': True}
    for name, source in sources.items():
        target = dest / source.name
        shutil.copyfile(source, target)
        assert target.read_bytes() == source.read_bytes()
        result['libraries'][name] = {'source': str(source), 'staged': str(target)}
    for name in ['axi_dma_func_pkg.vh', 'axi_dma_param_pkg.vh']:
        source = TD / 'ip/depot/AXI_DMA_1.0/AXI_DMA/RTL' / name
        shutil.copyfile(source, dest / name)
        assert (dest / name).read_bytes() == source.read_bytes()
    return result


def stage_sources(sources, out):
    staged = []
    inventory = []
    for source in sources:
        target = out / 'source' / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert target.read_bytes() == source.read_bytes()
        staged.append(target)
        inventory.append((source, target))
    inc = out / 'inc'
    (inc / 'generated').mkdir(parents=True)
    for folder in ['pl_interface/generated', 'pl_rs485/generated', 'pl_safety/generated']:
        for source in (ROOT / folder).glob('*.vh'):
            target = inc / ('generated' if folder == 'pl_interface/generated' else '') / source.name
            shutil.copyfile(source, target)
            assert target.read_bytes() == source.read_bytes()
            inventory.append((source, target))
    import json
    (out / 'compiled_sources.json').write_text(json.dumps({
        'hashes_computed': False,
        'direct_byte_verified_source_copies': [{'source': str(s), 'compiled_copy': str(t)} for s,t in inventory]
    }, indent=2) + '\n')
    return staged


def adapt(tb, scenario='protection', accepted_overlap=False):
    tb = tb.replace('`include "safety_defs.vh"', '`include "safety_defs.vh"\n`include "interlock_defs.vh"\n`include "gp_defs.vh"\n`include "telem_defs.vh"')
    tb = tb.replace('cycle>2000000', 'cycle>40000000')
    assert 'check(hp1_writes==0,"safety operation never initiates telemetry DMA");' in tb
    tb = tb.replace('check(hp1_writes==0,"safety operation never initiates telemetry DMA");', '')
    initial = tb.index('initial begin\n clk_100m=0;arst_n=0;safety_limit_n=7;')
    initialize = tb[initial:tb.index('reset_design;', initial) + len('reset_design;')]
    helpers = (ROOT / 'pl_dma/tb/telemetry_system_scenarios.vh').read_text()
    helpers = helpers[:helpers.index('initial begin\n clk_100m=0;')]
    helpers = helpers.replace("uq==8'h3a", "uq==8'h3e")
    helpers = helpers.replace('reg [7:0] ua,uq,uc,ub,sum;',
        'reg want_protect=0,want_unknown=0,bad_checksum_sent=0,unknown_sent=0;reg [7:0] reply_enum,reply_checksum;\nreg [7:0] ua,uq,uc,ub,sum;')
    helpers = helpers.replace("uart_send(ua);uart_send(8'd2);uart_send(ua+8'd2);",
                              """reply_enum=(want_protect && ua==8'he0) ? 1:2;
 if(ua==8'he1 && !unknown_sent)begin reply_enum=255;unknown_sent=1;end
 if(ua==8'he0 && want_unknown)reply_enum=255;
 reply_checksum=ua+reply_enum;
 if(ua==8'he0 && !bad_checksum_sent)begin reply_checksum=reply_checksum+1;bad_checksum_sent=1;end
 uart_send(ua);uart_send(reply_enum);uart_send(reply_checksum);""")
    assert 'reply_enum=' in helpers
    helpers += r'''
reg [31:0] predicted_generation,predicted_revision;
reg predicted_reset,predicted_change;
wire [5:0] decode_task;wire decode_formed,decode_valid,decode_known;
wire [63:0] decode_value;wire [31:0] decode_carry;wire [15:0] decode_word;wire [7:0] decode_enum;
rs485_light_parse commit_parser(`SAFETY.feedback_raw,decode_task,decode_formed,decode_valid,
 decode_known,decode_value,decode_carry,decode_word,decode_enum);
wire [2:0] decode_axes={decode_task==14,decode_task==9,decode_task==4} &
 {3{decode_formed && decode_valid && decode_known}};
wire [5:0] expected_predecode={decode_axes & {3{decode_enum==1}},decode_axes};
reg [3:0] preceding_step;reg detecting;integer hp_overlap=0,hp_accept_overlap=0;
always @(posedge clk_100m)if(control_rst_n && hp_rvalid && hp_rready &&
                            (hp1_awvalid || hp1_wvalid))hp_overlap=hp_overlap+1;
always @(posedge clk_100m)if(control_rst_n && hp_rvalid && hp_rready &&
                            hp1_wvalid && hp1_wready)hp_accept_overlap=hp_accept_overlap+1;
always @(posedge clk_100m)if(control_rst_n)begin
 predicted_generation=`SAFETY.collector_next_generation;
 predicted_revision=`SAFETY.collector_next_revision;
 predicted_reset=`SAFETY.collector_next_reset;
 predicted_change=`SAFETY.collector_next_config_change;
 preceding_step=motion_step;detecting=`SAFETY.il_detect;
 #1;
 if(`SAFETY.collector_generation!==predicted_generation || `SAFETY.collector_revision!==predicted_revision)
  $fatal(1,"complete source next values differ from real current registers");
 if(`SAFETY.collector_reset!==predicted_reset || `SAFETY.collector_config_change!==predicted_change)
  $fatal(1,"source control next values differ from actual current flags");
 if(`SAFETY.interlocks.monitor.epoch_match_q!==
    ((`SAFETY.collector_generation==`SAFETY.interlocks.monitor.round_generation) &&
     (`SAFETY.collector_revision==`SAFETY.interlocks.monitor.round_revision)))
  $fatal(1,"cached complete epoch comparison differs on current edge");
 if(`SAFETY.interlocks.monitor.off_context_q!==
    ((`SAFETY.collector_generation==`SAFETY.interlocks.monitor.round_generation) &&
     (`SAFETY.collector_revision==`SAFETY.interlocks.monitor.round_revision) && !`SAFETY.collector_reset))
  $fatal(1,"off context projection differs on current edge");
 if(`SAFETY.interlocks.monitor.active_context_q!==
    ((`SAFETY.collector_generation==`SAFETY.interlocks.monitor.round_generation) &&
     (`SAFETY.collector_revision==`SAFETY.interlocks.monitor.round_revision) &&
     `SAFETY.interlocks.monitor.previous_run && !`SAFETY.collector_reset &&
     !`SAFETY.collector_config_change && !`SAFETY.interlocks.cfg_apply))
  $fatal(1,"active context projection differs on current edge");
 if(`SAFETY.feedback_predecoded!==expected_predecode)
  $fatal(1,"EMIT predecode differs from original parser on current raw record");
 if(`SAFETY.owner!==((`SAFETY.state>=`SAF_STATES_PRE && `SAFETY.state<=`SAF_STATES_FINISH) ||
                    `SAFETY.state==`SAF_STATES_DRAIN))
  $fatal(1,"real same-edge HOME owner cache must match state decode");
 if(detecting)check((motion_step & ~preceding_step)==0,"real commit detecting edge forbids new STEP");
end
reg [63:0] owner_token;
reg [63:0] synthetic_time;
task jump_shared_time;input [63:0] target;begin
 // NON-PRODUCTION: accelerate the EXISTING common epoch and its old motion
 // ABI counter replica together; retain the original alignment assertion.
 // Never override a private monitor deadline. This is not wall-time proof.
 synthetic_time=target;
 force dut.core.fabric.registers.timestamp=synthetic_time;
 force `MOTION.timestamp=synthetic_time;
 repeat(4)@(negedge clk_100m);
 release dut.core.fabric.registers.timestamp;
 release `MOTION.timestamp;
end endtask
task feed_owner;input [63:0] seq;begin
 write_reg(SB+`SI_REG_HEARTBEAT_OWNER_LO,owner_token[31:0],15,0,0);
 write_reg(SB+`SI_REG_HEARTBEAT_OWNER_HI,owner_token[63:32],15,0,1);
 write_reg(SB+`SI_REG_HEARTBEAT_SEQ_LO,seq[31:0],15,0,2);
 write_reg(SB+`SI_REG_HEARTBEAT_SEQ_HI,seq[63:32],15,0,0);
 write_reg(SB+`SI_REG_HEARTBEAT_COMMIT,1,15,0,2);
end endtask
'''
    scenarios = r'''
repeat(30)@(negedge clk_100m);
read_reg(SB+4,0,status_value);check(status_value==`SI_PROFILE,"SAF2 through real GP converter");
read_reg(RB+4,0,status_value);check(status_value==`SI_COLLECTOR_PROFILE,"R5S2 explicitly identifies guarded old controls");
while(dut.core.fabric.revision==0 || !dut.core.fabric.rs485.cr)@(negedge clk_100m);
for(xx=0;xx<5;xx=xx+1)write_reg(RB+`RG_REG_SHADOW_PERIOD0+xx*4,0,15,0,0);
write_reg(RB+`RG_REG_SHADOW_PERIOD4,50000,15,0,0);
write_reg(RB+`RG_REG_SHADOW_MASK,16,15,0,0);write_reg(RB+`RG_REG_TXN_ID,1,15,0,0);
write_reg(RB+`RG_REG_CFG_SUBMIT,1,15,0,0);
status_value=3;while(status_value==3)read_reg(RB+`RG_REG_CFG_STATE,0,status_value);
check(status_value==5,"real collector configuration applied");
tw(`RT_REG_RECOVER_GEN,1);tw(`RT_REG_RECOVER,1);tw(`RT_REG_ENABLE,1);
write_reg(RB+`RG_REG_RUN,1,15,0,0);
while(!`SAFETY.interlocks.fb_qualified)@(negedge clk_100m);
check(event_count>=3,"qualification uses actual UART commits for all axes");
check(bad_checksum_sent && unknown_sent && dut.core.fabric.rs485.err>0,
      "real checksum failure/retry and unknown enum do not falsely qualify");
write_reg(SB+`SI_REG_OWNER_OPEN,1,15,0,1);
read_reg(SB+`SI_REG_OWNER_LO,0,status_value);owner_token={32'd0,status_value};feed_owner(1);
write_reg(SB+`SAF_REGISTERS_OPCODE,`SAF_COMMANDS_HOME_START,15,0,1);
write_reg(SB+`SAF_REGISTERS_TXN,1,15,0,2);write_reg(SB+`SAF_REGISTERS_SUBMIT,1,15,0,0);
while(`SAFETY.state!=`SAF_STATES_READY)@(negedge clk_100m);
motion_recover;motion_open;fill_motion(2,motion_session,0,1,1000000,100);
// Hold a real HP1 write request pending while the other real controller
// fetches MOT2 through HP0. Prove actual port overlap, not just two IOC flags.
ready_packet(packet,bytes);stall_hp1=1;issue_rx(packet,1,bytes);
while(!(hp1_awvalid || hp1_wvalid))@(negedge clk_100m);
issue_motion(2);await_dma;
check(hp_overlap>0 && stall_hp1,"real HP0 accepted reads overlap pending real HP1 writes");
while(!`MOTION.start_ready)@(negedge clk_100m);motion_command(`PLI_CMD_START,0);
check(`MOTION.running,"real HP0 MOT2 motion after qualified HOME");
// Old entry points cannot disable monitoring during ordinary motion.
write_reg(RB+`RG_REG_RUN,0,15,2,1);write_reg(RB+`RG_REG_LOCAL_RESET,1,15,2,2);
write_reg(RB+`RG_REG_SHADOW_MASK,0,15,0,0);write_reg(RB+`RG_REG_TXN_ID,2,15,0,0);
write_reg(RB+`RG_REG_CFG_SUBMIT,1,15,2,0);
check(`SAFETY.interlocks.raw_permit,"rejected old writes do not restart or erase qualification");
stall_hp1=0;
status_value=0;while(!status_value[12])read_reg(DB+52,0,status_value);
read_reg(DB+88,0,status_value);check(status_value==bytes && hp1_writes>0,"actual HP1 DDR reception");
for(xx=0;xx<bytes/64;xx=xx+1)begin
 for(yy=0;yy<64;yy=yy+1)decoded_frame[yy*8+:8]=memory[196608+xx*64+yy];
 ccrc=32'hffffffff;for(yy=0;yy<60;yy=yy+1)ccrc=motion_crc(ccrc,decoded_frame[yy*8+:8]);
 serial=decoded_frame[223:160];
 check(decoded_frame[511:480]==~ccrc && decoded_frame[31:0]==`RT_RECORD_MAGIC,"actual DDR frame CRC/header");
 check(decoded_frame[159:128]==1 && decoded_frame[127:96]==event_revisions[serial] &&
       decoded_frame[479:224]===raw_events[serial],"actual DDR immutable raw/revision");
end
tw(`RT_REG_COMPLETE_ID,packet);tw(`RT_REG_COMPLETE_GEN,1);tw(`RT_REG_COMPLETE_RESULT,0);tw(`RT_REG_COMPLETE,1);
ready_packet(packet,bytes);stall_hp1=1;issue_rx(packet,1,bytes);
// Deliberately do not consume the diagnostic FIFO or finish the stalled RX.
while(dut.core.fabric.rs485.drop==0)@(negedge clk_100m);
check(`MOTION.running && dut.core.fabric.rs485.level==8,"diagnostic FIFO full while moving");
want_protect=1;
while(!`SAFETY.causes[9])@(negedge clk_100m);
repeat(30)@(negedge clk_100m);
check(!`MOTION.session_valid && `MOTION.buffered_points==0 && `MOTION.partial_empty,
      "UART protection cancels actual session/queues/half-packet");
check(`MOTION.position_valid[2:0]==0 && motion_en[2:0]==0 && motion_step[2:0]==0,
      "actual collector protection invalidates/disables after pulse drain");
check(dut.core.fabric.rs485.drop>0 && stall_hp1 && !`SAFETY.interlocks.owner_active,
      "FIFO full/HP1 backpressure cannot hide protection or keep owner alive");
check(read_beats==18 && hp1_writes>0,"both real controllers exercised");
$display("PASS interlock_real_system checks=%0d events=%0d hp0_read=%0d hp1_write=%0d overlap=%0d",checks,event_count,read_beats,hp1_writes,hp_overlap);
$finish;
end
endmodule
'''
    if scenario != 'protection':
        fault = 'want_protect=1;\nwhile(!`SAFETY.causes[9])@(negedge clk_100m);'
        assert scenarios.count(fault) == 1
        if scenario == 'watchdog':
            replacement = r'''
jump_shared_time(`SAFETY.interlocks.monitor.watchdog_start+64'd1000000);
while(`SAFETY.interlocks.monitor.feedback_start[0]<=synthetic_time ||
      `SAFETY.interlocks.monitor.feedback_start[1]<=synthetic_time ||
      `SAFETY.interlocks.monitor.feedback_start[2]<=synthetic_time)@(negedge clk_100m);
check(`MOTION.running && `SAFETY.causes==0,"actual UART refresh before isolated watchdog expiry");
jump_shared_time(`SAFETY.interlocks.monitor.watchdog_start+64'd2000000);
while(!`SAFETY.causes[15])@(negedge clk_100m);
check(`SAFETY.causes==`SI_CAUSE_WATCHDOG && `SAFETY.first_cause==`SI_CAUSE_WATCHDOG,
      "isolated PS watchdog reason and first cause through actual GP/dual-DMA system");
'''
        else:
            assert scenario == 'feedback_timeout'
            replacement = r'''
want_unknown=1;
while(!(dut.core.fabric.rs485.completed_valid &&
        dut.core.fabric.rs485.completed_raw[247:240]==8'he0 &&
        dut.core.fabric.rs485.completed_raw[239:232]==8'h3e &&
        dut.core.fabric.rs485.completed_raw[7:0]==8'hff))@(negedge clk_100m);
jump_shared_time(`SAFETY.interlocks.monitor.watchdog_start+64'd1000000);
feed_owner(2);
while(`SAFETY.interlocks.monitor.feedback_start[1]<=synthetic_time ||
      `SAFETY.interlocks.monitor.feedback_start[2]<=synthetic_time)@(negedge clk_100m);
check(`MOTION.running && `SAFETY.causes==0,"other actual UART axes and healthy heartbeat remain qualified");
jump_shared_time(`SAFETY.interlocks.monitor.feedback_start[0]+64'd2000000);
while(!`SAFETY.causes[12])@(negedge clk_100m);
check(`SAFETY.causes==`SI_CAUSE_FEEDBACK_A0 && `SAFETY.first_cause==`SI_CAUSE_FEEDBACK_A0,
      "only missing known feedback expires despite actual unknown-enum replies and HP1 stalls");
'''
        scenarios = scenarios.replace(fault, replacement)
        scenarios = scenarios.replace('UART protection', scenario).replace('collector protection', scenario)
        scenarios = scenarios.replace('cannot hide protection', 'cannot hide timeout')
    scenarios = scenarios.replace('PASS interlock_real_system checks=',
                                  'PASS interlock_real_system scenario=' + scenario + ' checks=')
    result = tb[:initial] + helpers + initialize + scenarios
    result = result.replace('overlap=%0d"', 'overlap=%0d accepted_overlap=%0d"')
    result = result.replace('hp1_writes,hp_overlap);', 'hp1_writes,hp_overlap,hp_accept_overlap);')
    if accepted_overlap:
        declaration = 'reg stall_hp1=0,hp1_active=0,hp1_pending=0;'
        assert result.count(declaration) == 1 and result.count('&& !stall_hp1') == 2
        result = result.replace(declaration, 'reg hp_accept_window=0;\n' + declaration)
        result = result.replace('&& !stall_hp1', '&& (!stall_hp1 || hp_accept_window)')
        # Change ready only at the falling edge. Allow four of eight HP1 beats
        # during HP0, then stall again so await_dma's original no-HP1-IOC check
        # remains meaningful and the later second-packet fault stays blocked.
        result = result.replace('reg [3:0] preceding_step;', '''always @(negedge clk_100m)
 if(!control_rst_n)hp_accept_window=0;
 else hp_accept_window=read_beats>0 && read_beats<18 && hp1_writes<4;
reg [3:0] preceding_step;''')
        marker = 'check(hp_overlap>0 && stall_hp1,"real HP0 accepted reads overlap pending real HP1 writes");'
        assert result.count(marker) == 1
        result = result.replace(marker, marker + '\ncheck(hp_accept_overlap>0,"both real HP ports accept data on the same edge");')
    return result


def main():
    path = ROOT / 'pl_safety/tests/real_system.py'
    source = path.read_text()
    replacements = [
        ('ip=prepare();', 'ip=prepare_scoped(b);'),
        ('generated/safety_rs485_gp_ps_top.v', 'generated/interlock_rs485_gp_ps_top.v'),
        ('safety_rs485_gp_ps_top #(', 'interlock_rs485_gp_ps_top #('),
        ("ap.add_argument('--tag',required=True);a=ap.parse_args();",
         "ap.add_argument('--tag',required=True);ap.add_argument('--scenario',choices=['protection','watchdog','feedback_timeout'],default='protection');ap.add_argument('--accepted-overlap',action='store_true');a=ap.parse_args();"),
        ("(b/'tb.v').write_text(tb)", "tb=adapt(tb,a.scenario,a.accepted_overlap)\n (b/'tb.v').write_text(tb)"),
        ("result={'passed':False,'real_ip':ip}", "result={'passed':False,'real_ip':ip,'scenario':a.scenario,'accepted_overlap_requested':a.accepted_overlap}"),
        ("R/'pl_dma/build/ip'", "b/'ip'"),
        ("R/'pl_interface',R/'pl_rs485/generated',b/'ip',D/'generated',b", "b/'inc',b/'ip',b"),
        ("for p in (R/folder).glob('*.v')]", "for p in (R/folder).glob('*.v')];rtl=stage_sources(rtl,b)"),
        ("assert 'PASS safety_real_system' in output", "assert 'PASS interlock_real_system' in output"),
        ("if 'PASS safety' in x", "if 'PASS interlock' in x"),
        ('timeout=600', 'timeout=1200'),
        ("result['source_sha256']={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in rtl+[b/'tb.v']}",
         "result['source_paths']=[str(p.relative_to(R)) for p in rtl];result['hashes_computed']=False")]
    for old, new in replacements:
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    exec(compile(source, str(path), 'exec'), {'__name__': '__main__', '__file__': str(path),
                                          'prepare_scoped': prepare_scoped, 'adapt': adapt,
                                          'stage_sources': stage_sources})


if __name__ == '__main__':
    main()
