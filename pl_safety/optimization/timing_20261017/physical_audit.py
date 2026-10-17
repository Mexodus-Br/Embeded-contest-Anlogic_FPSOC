"""Read-only 16-thread routed net and timing inventory, no constraint changes."""
import argparse,json,hashlib,subprocess,shutil,re
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
if {{[get_param flow thread]!=16}} {{error "Expected threads16"}}
puts "TIMING_OPT_THREADS [get_param flow thread]"
get_num_thread
clear_user_sdc
read_sdc {(b/'gp/gp.sdc').as_posix()}
read_sdc {(b/'gp/ps-generated-properties.tcl').as_posix()}
set f [open nets.tsv w]
puts $f "name\tflat_pins\tdrivers\tclock"
set orphans {{}}
foreach n [get_nets -hier -quiet *] {{
 set drivers [get_property DRIVER_COUNT $n]
 set clock [get_property CLOCK $n]
 if {{$drivers==0}} {{
  if {{$clock!=0}} {{error "Unexpected undriven clock"}}
  lappend orphans $n
  # Provisional zero is accepted only after the complete report below is
  # independently checked to have Pins=Drivers=Loads=InOuts=0.
  puts $f "$n\t0\t0\t0"
 }} else {{puts $f "$n\t[get_property FLAT_CELL_PIN_COUNT $n]\t$drivers\t$clock"}}
}}
close $f
foreach n $orphans {{
 puts "ORPHAN_NET_BEGIN $n"
 report_nets [list $n] -connection -pin_display_limit 50000
 puts "ORPHAN_NET_END $n"
}}
# Full load classification is handled by pin_inventory.py using report_nets.
# This TD build does not implement get_pins -of net as a load-pin query.
update_timing -mode final
report_timing_summary -path_num 10 -file replay.timing
set pulses [get_regs -hier -quiet *pulse_event*]
puts "PULSE_REGISTER_SELECTION [llength $pulses] $pulses"
if {{[llength $pulses]<3}} {{error "Missing three real axis pulse registers"}}
report_timing_path -from $pulses -path_num 10 -file pulse_event.timing
set dir_ce {{}}
foreach axis {{0 1 2}} {{
 set one [get_pins -hier -quiet *a${{axis}}_dir*.ce]
 if {{[llength $one]!=1}} {{error "Expected exactly one real axis DIR CE"}}
 lappend dir_ce [lindex $one 0]
 set data [get_pins -hier -quiet *a${{axis}}_dir*.doq*]
 if {{[llength $data]<1}} {{error "Missing real DIR PAD data pins"}}
 foreach pin $data {{lappend dir_ce $pin}}
}}
puts "DIR_CE_SELECTION [llength $dir_ce] $dir_ce"
if {{[llength $dir_ce]<6}} {{error "Expected CE and data coverage for all three actual DIR registers"}}
report_timing_path -from $pulses -to $dir_ce -path_num 10 -file pulse_to_dir.timing
set fd [open pulse_event.timing r]
set content [read $fd]
close $fd
set physical {{}}
foreach line [split $content [format %c 10]] {{
 if {{[regexp {{^Begin Point\s*:\s*(\S+)}} $line unused pin]}} {{
  set cell [string range $pin 0 [expr {{[string last . $pin]-1}}]]
  if {{[lsearch -exact $physical $cell]<0}} {{lappend physical $cell}}
 }}
}}
if {{[llength $physical]<1}} {{error "Missing timed physical pulse source"}}
foreach cell $physical {{
 set one [get_cells -quiet $cell]
 if {{[llength $one]!=1}} {{error "Missing exact physical pulse source cell"}}
 report_cells $one -connection -attributes
}}
check_timing -verbose -file replay.check
puts TIMING_OPT_PHYSICAL_COMPLETE
exit
"""
 (o/'audit.tcl').write_text(tcl)
 with (o/'audit.log').open('w',encoding='utf-8') as f:p=subprocess.run([shutil.which('td_commands_prompt'),(o/'audit.tcl').as_posix()],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=600)
 log=(o/'audit.log').read_text(errors='replace');passed=p.returncode==0 and 'TIMING_OPT_PHYSICAL_COMPLETE' in log and 'Number of Thread = 16' in log and not 'ERROR:' in log
 orphans=[]
 for block in log.split('ORPHAN_NET_BEGIN ')[1:]:
  name,body=block.split('\n',1);body=body.split('ORPHAN_NET_END ')[0]
  counts={k:int(re.search(r'\b'+k+r'\s*\|\s*(\d+)',body)[1]) for k in ['Pins','Drivers','Loads','InOuts']}
  assert all(v==0 for v in counts.values()),('Active undriven physical net',name,counts)
  orphans.append({'name':name.strip(),'verified_report_counts':counts})
 timing=lambda path:{k:float(re.search(pattern,path.read_text())[1]) for k,pattern in [('setup_ns',r'SWNS:\s*([-\d.]+)ns'),('hold_ns',r'HWNS:\s*([-\d.]+)ns')]}
 expected=timing(b/'route.timing');actual=timing(o/'replay.timing');passed=passed and actual==expected
 (o/'result.json').write_text(json.dumps({'passed':passed,'build':a.build,'route_db_sha256':hashlib.sha256((b/'route.db').read_bytes()).hexdigest(),'threads':16,'expected_original_timing':expected,'replayed_original_timing':actual,'net_table_sha256':hashlib.sha256((o/'nets.tsv').read_bytes()).hexdigest(),'all_net_count':len((o/'nets.tsv').read_text().splitlines())-1,'verified_zero_pin_orphans':orphans},indent=2)+'\n');assert passed,log[-4000:]
 print('PASS physical inventory',o)
if __name__=='__main__':main()
