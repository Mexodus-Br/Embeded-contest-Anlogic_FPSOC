"""Exercise candidate migration and rejection without modifying frozen files."""
import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'pl_rs485/optimization'
def main():
 E=O/'identity_check';E.mkdir(exist_ok=False)
 good=json.loads((O/'top_r1/candidate.json').read_text(encoding='utf-8'))
 vectors=[('candidate',good,0),('old_current_tree',None,1)]
 bad=json.loads(json.dumps(good));bad['changed_source_sha256']['pl_rs485/rtl/rs485_latest_cache.v']='0'*64;vectors.append(('wrong_hash',bad,1))
 bad=json.loads(json.dumps(good));bad['changed_source_sha256']['pl_rs485/rtl/rs485_light_parse.v']='0'*64;vectors.append(('unapproved_file',bad,1))
 bad=json.loads(json.dumps(good));bad['baseline_commit']='f447116';vectors.append(('wrong_baseline',bad,1))
 results=[]
 for name,manifest,failed in vectors:
  cmd=[sys.executable,str(R/'bsp/telemetry/verify_input.py')]
  if manifest is not None:
   p=E/(name+'.json');p.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8');cmd+=['--optimization-manifest',str(p)]
  p=subprocess.run(cmd,cwd=R,capture_output=True,text=True,encoding='utf-8')
  (E/(name+'.log')).write_text('EXIT '+str(p.returncode)+'\n'+p.stdout+p.stderr,encoding='utf-8')
  assert bool(p.returncode)==bool(failed),(name,p.stdout+p.stderr)
  results.append({'case':name,'expected_rejection':bool(failed),'observed_exit':p.returncode})
 (E/'result.json').write_text(json.dumps({'passed':True,'old_assertions_preserved':True,'tests':results},indent=2)+'\n',encoding='utf-8')
 print('PASS candidate migration, old frozen current-tree rejection, wrong hash/file/baseline rejection')
if __name__=='__main__':main()
