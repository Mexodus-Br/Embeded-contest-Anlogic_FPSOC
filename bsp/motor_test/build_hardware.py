"""Full isolated PS/HP0/J12 build; gate bitgen on actual routed reports."""
from pathlib import Path
import json,re,subprocess
R=Path(__file__).resolve().parents[2]; W=R/'bsp/work/motor3125_soc_prj'
script='''set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
puts "MOTOR_THREADS [get_param flow thread]"
cd @W@
import_device dr1_90.db -package DR1M90GEG400 -speed 2
open_project -single_run system.al
set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16 after project load"}
puts "MOTOR_PROJECT_THREADS [get_param flow thread]"
get_num_thread
elaborate -top system_wrapper
read_adc -file gp/gp.adc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl
optimize_rtl
optimize_gate -maparea gate.area
report_timing_summary -file gate.timing -path_num 10
export_db gate.db
legalize_phy_inst
place
update_timing -mode manhattan
report_timing_summary -file place.timing -path_num 10
export_db place.db
route
update_timing -mode final
report_timing_summary -file route.timing -path_num 10
report_area -io_info -file route.area
check_timing -verbose -file route.check
report_route_status -drc -file route.drc
export_db route.db
puts MOTOR3125_ROUTE_COMPLETE
exit
'''.replace('@W@',W.as_posix())
tcl=W/'build.tcl';tcl.write_text(script)
td='D:/Anlogic/TD_Release_2026.1_SP2.200.067/bin/td_commands_prompt.exe'
if (W/'build.log').exists():
    from datetime import datetime
    (W/('attempt_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.log')).write_bytes((W/'build.log').read_bytes())
with (W/'build.log').open('w') as f:
    p=subprocess.run([td,tcl.as_posix()],cwd=W,stdout=f,stderr=subprocess.STDOUT,timeout=7200)
log=(W/'build.log').read_text(errors='replace')
assert p.returncode==0 and 'MOTOR3125_ROUTE_COMPLETE' in log
assert 'MOTOR_THREADS 16' in log and 'Number of Thread = 16' in log
critical=[x for x in log.splitlines() if 'CRITICAL-WARNING' in x or 'ERROR:' in x]
stages={}
for stage in ['gate','place','route']:
    t=(W/(stage+'.timing')).read_text()
    stages[stage]={k:float(re.search(token+r':\s*([-\d.]+)ns',t)[1]) for k,token in [('setup_ns','SWNS'),('hold_ns','HWNS')]}
    if stage=='route':
        assert '99.99%' in t and 'Both (Slow and Fast)' in t
        for c in ['board_100m','ps/DR1_PHY_PROCESSOR_SYSTEM_Inst.GEN_PL_GP0S','ps/DR1_PHY_PROCESSOR_SYSTEM_Inst.GEN_PL_HP0']:
            assert re.search(r'100\.000\s+[1-9]\d*\s+'+re.escape(c)+r'\s',t),c
check=(W/'route.check').read_text()
for n in ['no clock','no input delay','no output delay','combinational loops','invalid constraint']:
    assert all(int(x)==0 for x in re.findall('checking '+re.escape(n)+r'\((\d+)\)',check)),n
area=(W/'route.area').read_text()
resources={k:int(re.search(r'^#'+k+r'\s+(\d+)',area,re.M)[1]) for k in ['lut6','reg','slice','eram','dsp','gclk','sclk']}
for axis in range(3):
    for signal in ['step','dir','en']:
        assert re.search(r'^\s*a'+str(axis)+'_'+signal+r'\s+OUTPUT\s+\S+\s+LVCMOS33\s+HRIO\s+8\s+NONE\s+OREG',area,re.M)
result={'stages':stages,'resources':resources,'critical':critical,'reference_speed':2,'threads':16,
        'timing_pass':min(stages['route'].values())>=0,'board_validated':False}
(W/'review.json').write_text(json.dumps(result,indent=2)+'\n')
assert result['timing_pass'] and not critical,'Do not generate bitstream before resolving routed failures'
bit=W/'bitgen.tcl'
bit.write_text('set_param flow thread 16\ncd '+W.as_posix()+'\nimport_device dr1_90.db -package DR1M90GEG400 -speed 2\nimport_db route.db\nbitgen -bit system.bit\nputs MOTOR3125_BIT_COMPLETE\nexit\n')
with (W/'bitgen.log').open('w') as f:subprocess.run([td,bit.as_posix()],cwd=W,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
assert 'MOTOR3125_BIT_COMPLETE' in (W/'bitgen.log').read_text()
print(json.dumps(result,indent=2))
