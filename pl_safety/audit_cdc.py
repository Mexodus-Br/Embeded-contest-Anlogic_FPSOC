"""Audit exact first/second synchronizer pin selections in the routed database."""
import argparse,json,shutil,subprocess,hashlib
from pathlib import Path
from build_td import THREADS_TCL
R=Path(__file__).resolve().parents[1];D=R/'pl_safety'
ap=argparse.ArgumentParser();ap.add_argument('--build',required=True);ap.add_argument('--tag',required=True);a=ap.parse_args()
b=D/'build'/a.build;out=D/'evidence'/a.tag;out.mkdir(exist_ok=False)
assert (b/'route.db').exists()
p='control/core/fabric/dma_core/motion/inputs/'
sdc=(b/'gp/gp.sdc').read_text()
sdc='\n'.join('set_false_path -from [get_ports {safety_limit_n[*] safety_estop_n}]' if x.startswith('set_false_path -from [get_ports {safety_limit_n') else x for x in sdc.splitlines())+'\n'
(out/'replay.sdc').write_text(sdc)
tcl=f'''cd {out.as_posix()}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db {(b/'route.db').as_posix()}
{THREADS_TCL}
read_adc -file {(b/'gp/gp.adc').as_posix()}
read_sdc {(out/'replay.sdc').as_posix()}
read_sdc {(b/'gp/ps-generated-properties.tcl').as_posix()}
report_route_status -fanout_stat -file routed_fanout.rpt
update_timing -mode final
set pads [get_ports {{safety_limit_n[*] safety_estop_n}}]
set all [get_regs -hier -quiet *inputs*]
set first {{}}
set second {{}}
foreach item $all {{
 if {{[string match {{*{p}meta*}} $item]}} {{lappend first $item}}
 if {{[string match {{*{p}sync*}} $item]}} {{lappend second $item}}
}}
foreach group [list $pads $first $second] {{
 puts "CDC_SELECTION_COUNT [llength $group] $group"
 if {{[llength $group]!=4}} {{error "Expected exactly four synchronizer pins"}}
}}
report_timing_path -from $first -to $second -path_num 10 -file synchronizer_internal.timing
check_timing -verbose -file replay.check
puts SAFETY_CDC_SELECTION_AUDIT_COMPLETE
exit
'''
(out/'audit.tcl').write_text(tcl)
with (out/'audit.log').open('w') as f:r=subprocess.run([shutil.which('td_commands_prompt'),(out/'audit.tcl').as_posix()],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
log=(out/'audit.log').read_text(errors='replace');report=out/'synchronizer_internal.timing'
clean=(out/'replay.check').exists() and 'checking invalid constraint(0)' in (out/'replay.check').read_text(errors='replace')
passed=r.returncode==0 and 'SAFETY_TD_THREADS 16' in log and 'Number of Thread = 16' in log and 'SAFETY_CDC_SELECTION_AUDIT_COMPLETE' in log and report.exists() and 'Slack' in report.read_text(errors='replace') and clean
(out/'result.json').write_text(json.dumps({'passed':passed,'build':a.build,'threads':16,'route_db_sha256':hashlib.sha256((b/'route.db').read_bytes()).hexdigest(),'replay_sdc_sha256':hashlib.sha256((out/'replay.sdc').read_bytes()).hexdigest(),'purpose':'Only asynchronous pad->meta path excepted; meta->sync remains clocked','physical_cdc_signoff':False},indent=2)+'\n')
assert passed,log[-4000:]
print('PASS routed synchronizer pin selections; physical CDC/MTBF not qualified')
