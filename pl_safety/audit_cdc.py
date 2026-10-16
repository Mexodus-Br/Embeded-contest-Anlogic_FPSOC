"""Audit exact first/second synchronizer pin selections in the routed database."""
import argparse,json,shutil,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'pl_safety'
ap=argparse.ArgumentParser();ap.add_argument('--build',required=True);ap.add_argument('--tag',required=True);a=ap.parse_args()
b=D/'build'/a.build;out=D/'evidence'/a.tag;out.mkdir(exist_ok=False)
assert (b/'route.db').exists()
p='control/core/fabric/dma_core/motion/inputs/'
tcl=f'''cd {out.as_posix()}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db {(b/'route.db').as_posix()}
read_adc -file {(b/'gp/gp.adc').as_posix()}
read_sdc {(b/'gp/gp.sdc').as_posix()}
read_sdc {(b/'gp/ps-generated-properties.tcl').as_posix()}
update_timing -mode final
set pads [get_ports {{safety_limit_n[*] safety_estop_n}}]
set first [get_pins {{{p}meta_reg[*].d}}]
set launch [get_pins {{{p}meta_reg[*].q}}]
set second [get_pins {{{p}sync_reg[*].d}}]
foreach group [list $pads $first $launch $second] {{
 puts "CDC_SELECTION_COUNT [llength $group] $group"
 if {{[llength $group]!=4}} {{error "Expected exactly four synchronizer pins"}}
}}
report_timing_path -from $launch -to $second -path_num 10 -file synchronizer_internal.timing
puts SAFETY_CDC_SELECTION_AUDIT_COMPLETE
exit
'''
(out/'audit.tcl').write_text(tcl)
with (out/'audit.log').open('w') as f:r=subprocess.run([shutil.which('td_commands_prompt'),(out/'audit.tcl').as_posix()],stdout=f,stderr=subprocess.STDOUT,timeout=300)
log=(out/'audit.log').read_text(errors='replace');passed=r.returncode==0 and 'SAFETY_CDC_SELECTION_AUDIT_COMPLETE' in log
(out/'result.json').write_text(json.dumps({'passed':passed,'build':a.build,'purpose':'Only asynchronous pad->meta path excepted; meta->sync remains clocked','physical_cdc_signoff':False},indent=2)+'\n')
assert passed,log[-4000:]
print('PASS routed synchronizer pin selections; physical CDC/MTBF not qualified')
