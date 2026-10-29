"""Serial real vendor-IP system validation of isolated RTL; no stubs/hashes."""
import argparse,json,sys,traceback
from pathlib import Path
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);a=p.parse_args()
 candidate=Path(a.candidate).resolve();out=E/a.tag;out.mkdir(exist_ok=False)
 path=R/'pl_safety/tests/interlock_real_system.py';s=path.read_text()
 old="    for source in sources:\n        target = out / 'source' / source.relative_to(ROOT)"
 assert s.count(old)==1
 s=s.replace(old,"    for source in sources:\n        original_source = source\n        override = Path("+repr(candidate.as_posix())+") / source.name\n        if override.is_file(): source = override\n        target = out / 'source' / original_source.relative_to(ROOT)")
 s=s.replace("if __name__ == '__main__':\n    main()",'')
 namespace={'__file__':str(path),'__name__':'isolated_real_runner'};exec(compile(s,str(path),'exec'),namespace)
 result={'passed':False,'hashes_computed':False,'cases':[]};previous=sys.argv
 try:
  for scenario in ['protection','watchdog','feedback_timeout']:
   tag=a.tag+'_'+scenario
   sys.argv=[str(path),'--tag',tag,'--scenario',scenario,'--accepted-overlap'];namespace['main']()
   record=json.loads((R/'pl_safety/evidence'/tag/'result.json').read_text());assert record['passed']
   result['cases'].append({'scenario':scenario,'tag':tag,'passed':True,'output':record['output']})
   (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS isolated real system',scenario,flush=True)
  result['passed']=True
 except Exception:result['failure']=traceback.format_exc();raise
 finally:sys.argv=previous;(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
