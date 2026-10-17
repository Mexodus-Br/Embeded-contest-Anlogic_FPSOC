"""Reconcile new PHY-5010 unloaded-net warnings against the final physical DB."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[2]
from report import pnr_logs

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--build',required=True);ap.add_argument('--tag',required=True);a=ap.parse_args();b=R/'pl_safety/build'/a.build;o=E/a.tag;o.mkdir(exist_ok=False)
 source='\n'.join(t for p,t in pnr_logs(b))
 names=sorted(set(re.findall(r'PHY-5010 WARNING: Net (\S+) is skipped due to 0 input or output',source)));assert names,'No matching new warning to reconcile'
 overrides=[line for line in source.splitlines() if 'RUN-6001 WARNING:' in line]
 assert all('Step parameter thread has undefault value (16)' in line for line in overrides),'Unexpected database override warning'
 assert 'Number of Thread = 16' in source
 ns=' '.join('{'+n+'}' for n in names)
 tcl=f'''cd {o.as_posix()}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
set_param flow thread 16
get_num_thread
import_db {(b/'route.db').as_posix()}
set_param flow thread 16
get_num_thread
set all [get_nets -hier -quiet *]
foreach name {{{ns}}} {{
 set pos [lsearch -exact $all $name]
 if {{$pos<0}} {{puts "WARNING_NET $name ABSENT"}} else {{
  set n [list [lindex $all $pos]]
  puts "WARNING_NET_BEGIN $name"
  report_nets $n -connection -pin_display_limit 10000
  puts "WARNING_NET_END $name"
 }}
}}
puts WARNING_NET_AUDIT_COMPLETE
exit
'''
 (o/'audit.tcl').write_text(tcl)
 with (o/'audit.log').open('w',encoding='utf-8') as f:p=subprocess.run([shutil.which('td_commands_prompt'),(o/'audit.tcl').as_posix()],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=600)
 log=(o/'audit.log').read_text(errors='replace');assert p.returncode==0 and 'WARNING_NET_AUDIT_COMPLETE' in log and 'Number of Thread = 16' in log and not re.search(r'\bERROR:',log)
 rows=[]
 for n in re.findall(r'^WARNING_NET (\S+) ABSENT$',log,re.M):rows.append({'name':n,'status':'ABSENT','flat_pins':0,'drivers':0,'loads':0})
 for block in log.split('WARNING_NET_BEGIN ')[1:]:
  name,body=block.split('\n',1);body=body.split('WARNING_NET_END ')[0]
  counts={k:int(re.search(r'\b'+k+r'\s*\|\s*(\d+)',body)[1]) for k in ['Pins','Drivers','Loads']}
  assert counts['Loads']==0 or counts['Drivers']==1,('Unresolved active warning net driver',name,counts)
  rows.append({'name':name.strip(),'status':'PRESENT','flat_pins':counts['Pins'],'drivers':counts['Drivers'],'loads':counts['Loads']})
 assert len(rows)==len(names)
 result={'passed':True,'build':a.build,'threads':16,'route_db_sha256':hashlib.sha256((b/'route.db').read_bytes()).hexdigest(),'reviewed_codes':['PHY-5010']+(['RUN-6001'] if overrides else []),'thread_override_warnings':overrides,'nets':rows,'meaning':'PHY-5010: optimization-created aliases/copies; absent nets or nets without consumers are inactive, remaining active nets require one driver. RUN-6001: DB import warns about an explicit 16-thread setting; parent DB and post-import readback are 16. All original warnings retained.'}
 (o/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
