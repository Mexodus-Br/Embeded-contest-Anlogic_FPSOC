"""Durable local TD + serial real-IP workflow, explicitly requested by user.

Start with Windows Start-Process -WindowStyle Hidden, independent of chat/tool
sessions. No deployment, bitstream, hashes, recurring scheduler, or other chats.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta
import json,os,subprocess,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
OUT=HERE/'launch_r1';BUILD='interlock_route16'
def stamp():return datetime.now(timezone(timedelta(hours=8))).isoformat()
def write(name,data):
 target=OUT/name;temp=OUT/(name+'.tmp')
 temp.write_text(json.dumps(data,indent=2)+'\n');temp.replace(target)
def execute(argv,log):
 return subprocess.run([sys.executable,'-u',*map(str,argv)],cwd=ROOT,stdout=log,
  stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW).returncode
def td():
 with (OUT/'td_driver.log').open('w') as log:
  code=execute([ROOT/'pl_safety/build_interlock.py','--tag',BUILD,'--margin','1.25'],log)
 path=ROOT/'pl_safety/build'/BUILD/'summary.json'
 result=json.loads(path.read_text()) if path.exists() else {'passed':False,'failure':'No TD summary; inspect driver log'}
 result['exit_code']=code;result['completed_at']=stamp();write('td_result.json',result)
 return result
def real():
 result={'passed':False,'completed':False,'cases':[],'started_at':stamp(),'hashes_computed':False}
 with (OUT/'real_driver.log').open('w') as log:
  for label,scenario in [('protection','protection'),('watchdog','watchdog'),('feedback','feedback_timeout')]:
   tag=f'interlock_real_{label}16_20261020_r1'
   code=execute([ROOT/'pl_safety/tests/interlock_real_system.py','--tag',tag,
     '--scenario',scenario,'--accepted-overlap'],log)
   path=ROOT/'pl_safety/evidence'/tag/'result.json'
   passed=code==0 and path.exists() and json.loads(path.read_text())['passed']
   result['cases'].append({'tag':tag,'scenario':scenario,'passed':passed,'exit_code':code})
   write('real_result.json',result)
   if not passed:
    result.update(completed=True,completed_at=stamp());write('real_result.json',result)
    return result
 result.update(passed=True,completed=True,completed_at=stamp());write('real_result.json',result)
 return result
def main():
 assert OUT.is_dir() and not (OUT/'workflow_result.json').exists()
 for name,count in [('interlock_suite_route16_20261020_r1',375),('interlock_regressions_route16_20261020_r1',33)]:
  r=json.loads((ROOT/'pl_safety/evidence'/name/'result.json').read_text())
  assert r['passed'] and len(r['cases'])==count,name
 os.environ['PATH']='D:/Anlogic/TD_Release_2026.1_SP2.200.067/bin;D:/altera_lite/25.1std/questa_fse/win64;D:/iverilog/bin;'+os.environ['PATH']
 result={'passed':False,'signoff_pass':False,'started_at':stamp(),'hashes_computed':False,'build':BUILD}
 write('workflow_started.json',result)
 try:
  with ThreadPoolExecutor(max_workers=2) as pool:
   td_future=pool.submit(td);real_future=pool.submit(real)
   result['td']=td_future.result();result['real']=real_future.result()
  result['flow_completed']=result['td'].get('passed',False)
  result['timing_pass']=result['td'].get('timing_pass',False)
  result['passed']=result['flow_completed'] and result['timing_pass'] and result['real']['passed']
 except Exception:result['failure']=traceback.format_exc();raise
 finally:
  result['completed_at']=stamp();write('workflow_result.json',result)
if __name__=='__main__':main()
