"""Final routed CDC topology/exception audit; preserves original constraints."""
import argparse,hashlib,json,subprocess,shutil,re
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[2]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--build',required=True);ap.add_argument('--tag',required=True);a=ap.parse_args();b=R/'pl_safety/build'/a.build;o=E/a.tag;o.mkdir(exist_ok=False)
 tcl=f"""cd {o.as_posix()}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
set_param flow thread 16
get_num_thread
import_db {(b/'route.db').as_posix()}
set_param flow thread 16
puts "TIMING_OPT_THREADS [get_param flow thread]"
get_num_thread
clear_user_sdc
read_adc -file {(b/'gp/gp.adc').as_posix()}
read_sdc {(b/'gp/gp.sdc').as_posix()}
read_sdc {(b/'gp/ps-generated-properties.tcl').as_posix()}
update_timing -mode final
set first {{}}
set second {{}}
foreach r [get_regs -hier -quiet *inputs*] {{
 if {{[string match {{*motion/inputs/meta*}} $r]}} {{lappend first $r}}
 if {{[string match {{*motion/inputs/sync*}} $r]}} {{lappend second $r}}
}}
puts "CDC_FIRST [llength $first] $first"
puts "CDC_SECOND [llength $second] $second"
if {{[llength $first]!=4 || [llength $second]!=4}} {{error "Expected four meta and four sync registers"}}
report_timing_path -from $first -to $second -path_num 10 -file meta_to_sync.timing
# Logical meta/sync may share a Slice named after unrelated logic. Derive
# every actual source/destination cell from the timed paths, not its name.
set fd [open meta_to_sync.timing r]
set contents [read $fd]
close $fd
set physical {{}}
foreach line [split $contents [format %c 10]] {{
 if {{[regexp {{^(Begin Point|End Point)\s*:\s*(\S+)}} $line unused kind pin]}} {{
  set cell [string range $pin 0 [expr {{[string last . $pin]-1}}]]
  if {{[lsearch -exact $physical $cell]<0}} {{lappend physical $cell}}
 }}
}}
puts "CDC_PHYSICAL_CHAIN_CELLS [llength $physical] $physical"
if {{[llength $physical]<4 || [llength $physical]>8}} {{error "Unexpected physical synchronizer cell coverage"}}
foreach cell $physical {{
 set one [get_cells -quiet $cell]
 if {{[llength $one]!=1}} {{error "Missing exact physical synchronizer cell"}}
 report_cells $one -connection -attributes
 report_property [lindex $one 0]
}}
report_timing_exception -path_num 4 -file exceptions.timing
report_nets [get_nets -hier -quiet *inputs/meta*] -connection -pin_display_limit 32
report_nets [get_nets -hier -quiet *inputs/contact_n*] -connection -pin_display_limit 32
set cells [get_cells -hier -quiet *inputs/meta_reg*]
puts "CDC_META_CELLS [llength $cells] $cells"
foreach c $cells {{report_cells [list $c] -connection -attributes;report_property $c}}
set cells [get_cells -hier -quiet *inputs/sync_reg*]
puts "CDC_SYNC_CELLS [llength $cells] $cells"
foreach c $cells {{report_cells [list $c] -connection -attributes;report_property $c}}
check_timing -verbose -file replay.check
report_timing_summary -path_num 1 -file replay.timing
puts TIMING_OPT_CDC_COMPLETE
exit
"""
 (o/'audit.tcl').write_text(tcl)
 with (o/'audit.log').open('w',encoding='utf-8') as f:p=subprocess.run([shutil.which('td_commands_prompt'),(o/'audit.tcl').as_posix()],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=600)
 log=(o/'audit.log').read_text(errors='replace');timing=(o/'meta_to_sync.timing').read_text() if (o/'meta_to_sync.timing').exists() else ''
 assert p.returncode==0 and 'TIMING_OPT_CDC_COMPLETE' in log and 'Number of Thread = 16' in log
 assert 'Check Type          : setup' in timing and 'inputs/meta' in timing and 'inputs/sync' in timing,'Internal synchronizer path must remain timed'
 assert 'checking invalid constraint(0)' in (o/'replay.check').read_text()
 original=(R/'pl_safety/evidence/predecode_top7_paused/gp/gp.sdc').read_bytes();assert (b/'gp/gp.sdc').read_bytes()==original,'Constraint bytes changed'
 timing=lambda p:{k:float(re.search(pattern,p.read_text())[1]) for k,pattern in [('setup_ns',r'SWNS:\s*([-\d.]+)ns'),('hold_ns',r'HWNS:\s*([-\d.]+)ns')]}
 assert timing(b/'route.timing')==timing(o/'replay.timing'),'CDC audit changed final nominal STA'
 (o/'result.json').write_text(json.dumps({'passed':True,'build':a.build,'route_db_sha256':hashlib.sha256((b/'route.db').read_bytes()).hexdigest(),'original_sdc_sha256':hashlib.sha256(original).hexdigest(),'threads':16,'meta_to_sync_timed':True,'physical_mtbf_qualified':False,'notes':'Actual cell properties/connections retained; async_reg recognition and device MTBF are reported separately, never inferred from positive slack.'},indent=2)+'\n')
 print('PASS exact routed CDC/constraint audit',a.build)
if __name__=='__main__':main()
