"""Build the actual PS + GP control board wrapper with fixed 10ns clock."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--work-dir',default='telemetry_soc_prj')
p.add_argument('--dma',action='store_true')
p.add_argument('--report-only',action='store_true')
p.add_argument('--resume-gate',action='store_true')
a=p.parse_args()
WORK = (ROOT / 'work' / a.work_dir).resolve()
assert WORK.parent == (ROOT/'work').resolve()
TD = Path('D:/Anlogic/TD_Release_2026.1_SP2.200.067/bin/td_commands_prompt.exe')
script = '''cd @WORK@
import_device dr1_90.db -package DR1M90GEG400 -speed 2
open_project system.al
elaborate -top system_wrapper
read_adc -file gp/gp.adc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl
optimize_rtl
optimize_gate -maparea gp_gate.area
report_timing_summary -file gp_gate.timing -path_num 5
export_db gp_gate.db
legalize_phy_inst
place
update_timing -mode manhattan
report_timing_summary -file gp_place.timing -path_num 5
export_db gp_place.db
route
update_timing -mode final
report_timing_summary -file gp_route.timing -path_num 5
report_area -io_info -file gp_route.area
check_timing -verbose -file gp_route.check
report_route_status -drc -file gp_route.drc
export_db gp_route.db
puts BSP_TELEMETRY_RESOURCE_BUILD_COMPLETE
exit
'''.replace('@WORK@',WORK.as_posix())
(WORK / 'build_gp.tcl').write_text(script, encoding='utf-8')
if a.resume_gate:
    assert (WORK/'gp_gate.db').is_file()
    import shutil
    if not (WORK/'initial-timeout.log').exists():shutil.copyfile(WORK/'build_gp.log',WORK/'initial-timeout.log')
    script='cd '+WORK.as_posix()+'\nimport_device dr1_90.db -package DR1M90GEG400 -speed 2\nimport_db gp_gate.db\nread_adc -file gp/gp.adc\nread_sdc gp/gp.sdc\nread_sdc gp/ps-generated-properties.tcl\n'+script.split('export_db gp_gate.db\n',1)[1]
    (WORK/'resume_gate.tcl').write_text(script,encoding='utf-8')
if not a.report_only:
    if (WORK/'build_gp.log').exists():
        from datetime import datetime
        import shutil
        shutil.copyfile(WORK/'build_gp.log',WORK/('attempt_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.log'))
    name='resume_gate' if a.resume_gate else 'build_gp'
    with (WORK / (name+'.log')).open('w',encoding='utf-8') as log:
        result=subprocess.run([str(TD),(WORK/(name+'.tcl')).as_posix()],cwd=WORK,stdout=log,stderr=subprocess.STDOUT,timeout=7200)
output = (WORK / 'build_gp.log').read_text(encoding='utf-8', errors='replace')
if (WORK/'resume_gate.log').exists():output+='\n'+(WORK/'resume_gate.log').read_text(encoding='utf-8',errors='replace')
if a.report_only and (WORK/'resume_route.log').exists(): output += (WORK/'resume_route.log').read_text(encoding='utf-8',errors='replace')
if (not a.report_only and result.returncode) or 'BSP_TELEMETRY_RESOURCE_BUILD_COMPLETE' not in output or re.search(r'\bERROR:',output):
    raise SystemExit('Resource build failed; keep all logs/checkpoints')
critical=[line for line in output.splitlines() if 'CRITICAL-WARNING' in line]
stages={}
for stage in ['gate','place','route']:
    t=(WORK/('gp_'+stage+'.timing')).read_text(encoding='utf-8')
    stages[stage]={'setup_wns_ns':float(re.search(r'SWNS:\s*([-\d.]+)ns',t)[1]),'hold_wns_ns':float(re.search(r'HWNS:\s*([-\d.]+)ns',t)[1])}
summary={'status':'RESOURCE_BUILD_ONLY_NO_BITSTREAM','reference_speed':2,'stages':stages,'critical_warnings':critical,'not_deployable':True,'connections':json.loads((WORK/'connections.json').read_text(encoding='utf-8'))}
(WORK/'build-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'stages':stages,'critical_warnings':critical,'bitgen':'NOT_EXECUTED'},indent=2))
