"""Validate clocks on existing gate databases and place the smallest tested preset.

The virtual-interface placement is capacity evidence only. It does not model
native PS/HP arbitration, external clock/reset fabric, package IO or integration.
"""
from pathlib import Path
import json,time,subprocess
from run_resources import ROOT,BIN,THREADS,CLOCK_SDC,run_tcl

if __name__=='__main__':
    full=ROOT/'ip_full_native'
    for _ in range(180):
        if (full/'synth.log').exists() and 'NPU_SYNTH_DONE' in (full/'synth.log').read_text(errors='replace'):
            break
        time.sleep(5)
    else:
        raise RuntimeError('Full reference incomplete; no subsequent TD job launched')
    for name in ['full_native','whole_no_video','tiny_no_video','mbface_no_video','v3_no_video']:
        source=ROOT/('ip_'+name);out=ROOT/('audit100_'+name);out.mkdir(exist_ok=True)
        (out/'fixture.sdc').write_text(CLOCK_SDC)
        before=(source/'gate.db').read_bytes()
        text=f'''cd {{{out.as_posix()}}}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db {{{(source/'gate.db').as_posix()}}}
''' + THREADS + '''clear_user_sdc
read_sdc fixture.sdc
update_timing
if {[llength [get_clocks *]] != 2} {error "Expected two clocks"}
puts "CLOCKS [get_clocks *]"
report_timing_summary -file gate_100m.timing -path_num 5
puts "NPU_CLOCK_AUDIT_DONE"
exit
'''
        log=run_tcl(out,'audit',text)
        assert 'NPU_CLOCK_AUDIT_DONE' in log and 'CRITICAL-WARNING' not in log
        timing=(out/'gate_100m.timing').read_text()
        import re
        active=re.findall(r'^\s*clk\d+:\s+([\d.]+)\s+\d+\s+(npu_\w+)',timing,re.M)
        assert sorted(active)==[('100.000','npu_config'),('100.000','npu_data')],active
        assert 'DeriveClock' not in timing
        assert before==(source/'gate.db').read_bytes(), 'Input database changed'
        (out/'status.json').write_text(json.dumps(dict(threads=16,period_ns=10,input_db_unchanged=True,
            disclaimer='synthesized timing only; ideal external same-source/same-frequency clock contract'),indent=2)+'\n')
        print('AUDITED',name,flush=True)
    source=ROOT/'ip_tiny_no_video';out=ROOT/'physical_tiny_100m';out.mkdir(exist_ok=True)
    (out/'fixture.sdc').write_text(CLOCK_SDC)
    text=f'''cd {{{out.as_posix()}}}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db {{{(source/'gate.db').as_posix()}}}
''' + THREADS + '''clear_user_sdc
read_sdc fixture.sdc
update_timing
if {[llength [get_clocks *]] != 2} {error "Expected two clocks"}
legalize_phy_inst
place
report_area -file place.area
report_timing_summary -file place.timing -path_num 5
export_db place.db
puts "NPU_PLACE_DONE"
exit
'''
    log=run_tcl(out,'place',text)
    assert 'NPU_PLACE_DONE' in log
    print('PLACED tiny_no_video',flush=True)
