"""Read mapped reset modes and connections; one TD audit, explicit 16 threads."""
import argparse, collections, csv, json, re, shutil, subprocess, traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--build',required=True);p.add_argument('--tag',required=True)
    a=p.parse_args();assert all(re.fullmatch('[A-Za-z0-9_-]+',s) for s in [a.build,a.tag])
    out=HERE/a.tag;out.mkdir(exist_ok=False);b=ROOT/'pl_safety/build'/a.build
    tcl=f'''cd {out.as_posix()}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
set_param flow thread 16
get_num_thread
import_db {(b/'gate.db').as_posix()}
set_param flow thread 16
if {{[get_param flow thread]!=16}} {{error "Expected sixteen threads"}}
get_num_thread
set f [open reset_cells.tsv w]
puts $f "name\tmode\tmux\tset"
set n 0
set examples {{}}
foreach c [get_cells -hier -quiet *] {{
 if {{[get_property REF_NAME $c] eq "AL_MAP_SEQ"}} {{
  incr n
  set mode [get_property SRMODE $c]
  set mux [get_property SRMUX $c]
  puts $f "$c\t$mode\t$mux\t[get_property REGSET $c]"
  set key "$mode/$mux"
  if {{[lsearch -exact $examples $key]<0}} {{
   lappend examples $key
   puts "RESET_EXAMPLE $key"
   report_cells [list $c] -connection -attributes
  }}
 }}
}}
close $f
puts "RESET_SEQ_COUNT $n"
if {{$n<30000}} {{error "Incomplete mapped FF selection"}}
puts RESET_INVENTORY_COMPLETE
exit
'''
    (out/'audit.tcl').write_text(tcl)
    result={'passed':False,'build':a.build,'hashes_computed':False}
    try:
        before=(b/'gate.db').read_bytes()
        with (out/'audit.log').open('w') as log:
            proc=subprocess.run([shutil.which('td_commands_prompt'),(out/'audit.tcl').as_posix()],cwd=out,
                                stdout=log,stderr=subprocess.STDOUT,timeout=600)
        log=(out/'audit.log').read_text(errors='replace')
        assert proc.returncode==0 and 'RESET_INVENTORY_COMPLETE' in log and 'Number of Thread = 16' in log
        assert (b/'gate.db').read_bytes()==before
        rows=list(csv.DictReader((out/'reset_cells.tsv').open(),delimiter='\t'))
        groups=collections.Counter((r['mode'],r['mux'],r['set']) for r in rows)
        hierarchy=collections.Counter('/'.join(r['name'].split('/')[:-1]) for r in rows if r['mode']=='ASYNC' and r['mux'] in ['SIG','INV'])
        result.update(passed=True,threads=16,ff_count=len(rows),groups=[{'mode':k[0],'mux':k[1],'set':k[2],'count':v} for k,v in sorted(groups.items())],
                      connected_async_ff=sum(hierarchy.values()),async_by_hierarchy=dict(hierarchy.most_common()))
        print(json.dumps({k:v for k,v in result.items() if k!='async_by_hierarchy'},indent=2))
    except Exception:
        result['failure']=traceback.format_exc();raise
    finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
