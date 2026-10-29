"""Inspect the actual mapped raw FIFO block RAM and its collision configuration."""
import argparse,json,re,shutil,subprocess,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--build',required=True);p.add_argument('--tag',required=True)
    p.add_argument('--export-netlist',action='store_true')
    a=p.parse_args();assert all(re.fullmatch('[A-Za-z0-9_-]+',s) for s in [a.build,a.tag])
    b=ROOT/'pl_safety/build'/a.build;out=HERE/a.tag;out.mkdir(exist_ok=False)
    t=f'''cd {out.as_posix()}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
set_param flow thread 16
get_num_thread
import_db {(b/'gate.db').as_posix()}
set_param flow thread 16
get_num_thread
if {{[get_param flow thread]!=16}} {{error "Expected sixteen threads"}}
set nr 0
foreach c [get_cells -hier -quiet *raw_fifo*] {{
 if {{[string match *RAM* [get_property REF_NAME $c]]}} {{
  incr nr
  puts "RAW_FIFO_MEMORY $c"
  report_cells [list $c] -connection -attributes
  report_property $c
 }}
}}
puts "RAW_FIFO_MEMORY_COUNT $nr"
if {{$nr!=11}} {{error "Expected all eleven mapped raw FIFO block memories"}}
puts RAW_FIFO_AUDIT_COMPLETE
exit
'''
    if a.export_netlist:t=t.replace('puts RAW_FIFO_AUDIT_COMPLETE','write_verilog mapped.v\nputs RAW_FIFO_AUDIT_COMPLETE')
    (out/'audit.tcl').write_text(t);result={'passed':False,'build':a.build,'hashes_computed':False}
    try:
        before=(b/'gate.db').read_bytes()
        with (out/'audit.log').open('w') as log:
            proc=subprocess.run([shutil.which('td_commands_prompt'),(out/'audit.tcl').as_posix()],cwd=out,
                                stdout=log,stderr=subprocess.STDOUT,timeout=300)
        log=(out/'audit.log').read_text(errors='replace')
        assert proc.returncode==0 and 'RAW_FIFO_AUDIT_COMPLETE' in log and 'Number of Thread = 16' in log
        assert before==(b/'gate.db').read_bytes()
        result.update(passed=True,threads=16,raw_fifo_eram=11,
                      configuration_lines=[line for line in log.splitlines() if re.search('MODE|WIDTH|DEPTH|WRITE|READ|CLK|BYPASS',line)])
        print('PASS actual mapped raw FIFO eleven RAM configurations/connections retained')
    except Exception:
        result['failure']=traceback.format_exc();raise
    finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
