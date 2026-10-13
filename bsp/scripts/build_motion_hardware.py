"""Build the actual PS + GP control board wrapper with fixed 10ns clock."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--work-dir',default='motion_soc_prj')
p.add_argument('--dma',action='store_true')
p.add_argument('--report-only',action='store_true')
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
bitgen -bit system.bit
puts BSP_MOTION_BOARD_BITSTREAM_COMPLETE
exit
'''.replace('@WORK@',WORK.as_posix())
(WORK / 'build_gp.tcl').write_text(script, encoding='utf-8')
if not a.report_only:
    with (WORK / 'build_gp.log').open('w',encoding='utf-8') as log:
        result=subprocess.run([str(TD),(WORK/'build_gp.tcl').as_posix()],cwd=WORK,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
output = (WORK / 'build_gp.log').read_text(encoding='utf-8', errors='replace')
if a.report_only and (WORK/'resume_route.log').exists(): output += (WORK/'resume_route.log').read_text(encoding='utf-8',errors='replace')
if (not a.report_only and result.returncode) or 'BSP_MOTION_BOARD_BITSTREAM_COMPLETE' not in output or re.search(r'\bERROR:|CRITICAL-WARNING', output):
    raise SystemExit('Full GP system build failed; inspect build_gp.log')
stages = {}
for stage in ['gate', 'place', 'route']:
    text = (WORK / ('gp_' + stage + '.timing')).read_text(encoding='utf-8')
    setup = float(re.search(r'SWNS:\s*([-\d.]+)ns', text)[1])
    hold = float(re.search(r'HWNS:\s*([-\d.]+)ns', text)[1])
    if not re.search(r'100\.000\s+\d+\s+gp_clk', text):
        raise SystemExit('100MHz GP clock missing from timing report')
    if not re.search(r'100\.000\s+[1-9]\d*\s+ps/DR1_PHY_PROCESSOR_SYSTEM_Inst.GEN_PL_GP0S', text):
        raise SystemExit('100MHz PS GP0 capture clock missing or no active fanout')
    if a.dma and not re.search(r'100\.000\s+[1-9]\d*\s+ps/DR1_PHY_PROCESSOR_SYSTEM_Inst.GEN_PL_HP0\s',text):
        raise SystemExit('100MHz PS HP0 clock missing or no active fanout')
    stages[stage] = {'setup_wns_ns':setup, 'hold_wns_ns':hold}
    if stage == 'route' and (setup < 0 or hold < 0):
        raise SystemExit('10ns timing not met at ' + stage)
summary = {'status':'FULL_PS_GP_HP_MOTION_TEST_CONFIG_BUILT_NOT_BOARD_TESTED' if a.dma else 'FULL_PS_GP_BUILT_NOT_BOARD_TESTED', 'reference_speed':2,
           'stages':stages, 'bitstream_sha256':hashlib.sha256((WORK / 'system.bit').read_bytes()).hexdigest(),
           'connections':json.loads((WORK / 'connections.json').read_text(encoding='utf-8'))}
(WORK / 'build-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
