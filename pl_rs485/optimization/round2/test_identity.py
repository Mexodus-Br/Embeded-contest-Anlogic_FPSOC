"""Positive and fail-closed negative cases for the second candidate identity."""
import argparse,json,subprocess,sys
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[2]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);a=ap.parse_args();D=E/'identity';D.mkdir(exist_ok=False)
 good=json.loads((E.parent/('top_'+a.tag)/'candidate.json').read_text(encoding='utf-8'))
 cases=[('candidate',good,False),('frozen_default',None,True)]
 for label,edit in [
  ('wrong_hash',lambda m:m['changed_source_sha256'].__setitem__('pl_rs485/rtl/rs485_latest_cache.v','0'*64)),
  ('unapproved_parser',lambda m:m['changed_source_sha256'].__setitem__('pl_rs485/rtl/rs485_light_parse.v','0'*64)),
  ('wrong_baseline',lambda m:m.__setitem__('baseline_commit','f447116')),
  ('wrong_parent',lambda m:m.__setitem__('parent_candidate_commit','7681c69')),
  ('old_round_cannot_extend_allowlist',lambda m:m.__setitem__('optimization_round',1)),
 ]:
  m=json.loads(json.dumps(good));edit(m);cases.append((label,m,True))
 results=[]
 for label,m,reject in cases:
  cmd=[sys.executable,str(R/'bsp/telemetry/verify_input.py')]
  if m is not None:
   p=D/(label+'.json');p.write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8');cmd+=['--optimization-manifest',str(p)]
  p=subprocess.run(cmd,cwd=R,capture_output=True,text=True,encoding='utf-8');(D/(label+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8')
  assert bool(p.returncode)==reject,(label,p.stdout,p.stderr)
  results.append({'case':label,'expected_rejection':reject,'exit':p.returncode})
 (D/'result.json').write_text(json.dumps({'passed':True,'tests':results},indent=2)+'\n',encoding='utf-8');print('PASS 7 candidate/frozen/hash/path/parent/round identity cases')
if __name__=='__main__':main()
