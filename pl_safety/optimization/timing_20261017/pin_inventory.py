"""Classify high fanout using connected pin types, never the DataNet table alone."""
import argparse,json,hashlib,subprocess,shutil,re
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[2]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--build',required=True);ap.add_argument('--nets',required=True);ap.add_argument('--tag',required=True);a=ap.parse_args();b=R/'pl_safety/build'/a.build;csv=E/a.nets/'nets.tsv';o=E/a.tag;o.mkdir(exist_ok=False)
 parent=json.loads((E/a.nets/'result.json').read_text());assert parent['passed'] and parent['build']==a.build and parent['route_db_sha256']==hashlib.sha256((b/'route.db').read_bytes()).hexdigest()
 rows=[x.split('\t') for x in csv.read_text().splitlines()[1:]];high=[x for x in rows if int(x[1])-int(x[2])>=64]
 names=' '.join('{'+x[0]+'}' for x in high)
 tcl=f"""cd {o.as_posix()}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
set_param flow thread 16
get_num_thread
import_db {(b/'route.db').as_posix()}
set_param flow thread 16
puts "TIMING_OPT_THREADS [get_param flow thread]"
get_num_thread
foreach n {{{names}}} {{
 puts "NET_AUDIT_BEGIN $n"
 report_nets [list $n] -connection -pin_display_limit 50000
 puts "NET_AUDIT_END $n"
}}
puts TIMING_OPT_PIN_INVENTORY_COMPLETE
exit
"""
 (o/'audit.tcl').write_text(tcl)
 with (o/'audit.log').open('w',encoding='utf-8') as f:p=subprocess.run([shutil.which('td_commands_prompt'),(o/'audit.tcl').as_posix()],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=600)
 log=(o/'audit.log').read_text(errors='replace');assert p.returncode==0 and 'TIMING_OPT_PIN_INVENTORY_COMPLETE' in log and 'Number of Thread = 16' in log
 result=[]
 blocks={}
 for block in log.split('NET_AUDIT_BEGIN ')[1:]:
  n,body=block.split('\n',1);body=body.split('NET_AUDIT_END ')[0];blocks[n.strip()]=body
 for n,flat,drivers,clock in high:
  body=blocks[n];assert 'Load pin(s):' in body,('missing net report',n)
  ps=re.findall(r'RUN-1001 :\s+\d+\s+\|\s+(\S+)\s+\|',body.split('Load pin(s):')[1])
  assert len(ps)==int(flat)-int(drivers),('incomplete load inventory',n,len(ps),flat,drivers)
  cats={'ce':0,'reset':0,'clock':0,'other':0}
  for pin in ps:
   terminal=pin.rsplit('.',1)[-1].lower()
   k='clock' if re.fullmatch(r'(clk|clkin(?:\[.*)?|ck)',terminal) else 'ce' if re.fullmatch(r'(ce[a-d]?|en[a-d]?)',terminal) else 'reset' if re.fullmatch(r'(asr|arst|sr|rst|reset|rstn|rst_n|srst|clear|rsta|rstb)',terminal) else 'other'
   cats[k]+=1
  driver_body=body.split('Driver pin(s):')[1].split('Load pin(s):')[0]
  driver_pins=re.findall(r'RUN-1001 :\s+\d+\s+\|\s+(\S+)\s+\|',driver_body)
  assert len(driver_pins)==int(drivers),('incomplete driver inventory',n)
  category='clock' if clock=='1' else 'constant' if re.search(r'is_(?:const0|const1|tielow)\s+\|\s+True',body) else 'reset' if cats['reset'] else 'ce' if cats['ce'] else 'ordinary_data'
  result.append({'name':n,'loads':int(flat)-int(drivers),'flat_pins':int(flat),'drivers':int(drivers),'returned_load_pins':len(ps),'driver_pins':driver_pins,'category':category,'pin_types':cats})
 result.sort(key=lambda x:x['loads'],reverse=True)
 (o/'result.json').write_text(json.dumps({'passed':True,'build':a.build,'route_db_sha256':hashlib.sha256((b/'route.db').read_bytes()).hexdigest(),'threshold_loads_inclusive':64,'nets':result,'source_net_table_sha256':hashlib.sha256(csv.read_bytes()).hexdigest(),'threads':16},indent=2)+'\n')
 print('PASS pin inventory',len(result),'nets');print(json.dumps(result[:8],indent=2))
if __name__=='__main__':main()
