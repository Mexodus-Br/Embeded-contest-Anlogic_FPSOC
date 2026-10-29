"""Read-only final routed path/net audit; no optimization and no file hashes."""
import argparse,json,re,shutil,subprocess,traceback
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[2]

def main():
 p=argparse.ArgumentParser();p.add_argument('--tag',required=True);a=p.parse_args()
 assert re.fullmatch('[A-Za-z0-9_-]+',a.tag)
 o=E/a.tag;o.mkdir(exist_ok=False);b=R/'pl_safety/build/rtl_path38'
 db=b/'route.db';before=db.read_bytes()
 tcl=f'''cd {o.as_posix()}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
set_param flow thread 16
get_num_thread
import_db {db.as_posix()}
set_param flow thread 16
if {{[get_param flow thread]!=16}} {{error "Expected16threads"}}
puts "ROUTE38_AUDIT_THREADS [get_param flow thread]"
get_num_thread
clear_user_sdc
read_sdc {(b/'gp/gp.sdc').as_posix()}
read_sdc {(b/'gp/ps-generated-properties.tcl').as_posix()}
update_timing -mode final
report_timing_summary -path_num 100 -file expanded.timing
foreach axis {{0 1 2}} {{
 foreach kind {{step dir en}} {{
  set pins [get_pins -hier -quiet *a${{axis}}_${{kind}}*.ce]
  puts "ENDPOINT_SELECTED $axis $kind [llength $pins] $pins"
  if {{[llength $pins]==1}} {{
   report_timing_path -to $pins -path_num 20 -file axis${{axis}}_${{kind}}_ce.timing
  }}
 }}
}}
set f [open nets.tsv w]
puts $f "name\tflat_pins\tdrivers\tclock"
set high_count 0
foreach n [get_nets -hier -quiet *] {{
 set d [get_property DRIVER_COUNT $n]
 if {{$d==0}} {{continue}}
 set flat [get_property FLAT_CELL_PIN_COUNT $n]
 set clock [get_property CLOCK $n]
 puts $f "$n\t$flat\t$d\t$clock"
 if {{$flat-$d>=64}} {{
  incr high_count
  puts "NET_AUDIT_BEGIN $n"
  report_nets [list $n] -connection -pin_display_limit 50000
  puts "NET_AUDIT_END $n"
 }}
}}
close $f
puts "HIGH_NET_COUNT $high_count"
puts ROUTE38_ANALYSIS_COMPLETE
exit
'''
 (o/'audit.tcl').write_text(tcl)
 result=dict(passed=False,build='rtl_path38',hashes_computed=False,read_only=True)
 try:
  with (o/'audit.log').open('w') as log:
   proc=subprocess.run([shutil.which('td_commands_prompt'),(o/'audit.tcl').as_posix()],cwd=o,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
  log=(o/'audit.log').read_text(errors='replace')
  assert proc.returncode==0 and 'ROUTE38_ANALYSIS_COMPLETE' in log
  assert 'ROUTE38_AUDIT_THREADS 16' in log and 'Number of Thread = 16' in log
  assert db.read_bytes()==before,'Original DB changed'
  original=(b/'route.timing').read_text();replay=(o/'expanded.timing').read_text()
  for pattern in [r'SWNS:\s*([-\d.]+)ns',r'HWNS:\s*([-\d.]+)ns']:
   assert re.search(pattern,original)[1]==re.search(pattern,replay)[1]
  result.update(passed=True,threads=16,original_database_direct_byte_unchanged=True,
   original_nominal_timing_reproduced=True,high_net_count=int(re.search(r'HIGH_NET_COUNT (\d+)',log)[1]))
  print(json.dumps(result,indent=2))
 except BaseException:
  result['failure']=traceback.format_exc();raise
 finally:(o/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
