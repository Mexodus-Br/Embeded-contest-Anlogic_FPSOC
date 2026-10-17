"""New exact-identity gate; does not weaken any historical release verifier."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'pl_safety'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def gitbytes(name):return subprocess.check_output(['git','show','c9f2e05:'+name],cwd=R)
def commit_blobs(commit,names):
 # One read-only Git batch avoids thousands of Windows process launches.
 data=subprocess.check_output(['git','cat-file','--batch'],cwd=R,input=''.join(commit+':'+n+'\n' for n in names).encode('utf-8'))
 result={};offset=0
 for name in names:
  end=data.index(b'\n',offset);header=data[offset:end].split()
  assert len(header)==3 and header[1]==b'blob',('missing committed file',name)
  size=int(header[2]);start=end+1
  assert data[start+size:start+size+1]==b'\n',name
  result[name]=data[start:start+size];offset=start+size+1
 assert offset==len(data),'Unexpected Git batch output'
 return result
def old_retained(old,new,path=''):
 n=0
 if isinstance(old,dict):
  for k,v in old.items():assert k in new,path+'/'+k;n+=old_retained(v,new[k],path+'/'+k)
 elif isinstance(old,list):
  assert len(old)==len(new),path
  for i,(x,y) in enumerate(zip(old,new)):n+=old_retained(x,y,path+'/'+str(i))
 else:assert old==new,path;n=1
 return n
def baseline():
 old=json.loads(gitbytes('pl_interface/schema.json'));new=json.loads((R/'pl_interface/schema.json').read_text(encoding='utf-8'))
 n=old_retained(old,new)
 assert set(new)-set(old)=={'safety_profiles'}
 for f in ['interface_defs.h','interface_defs.vh','registers.md','errors.md']:
  p='pl_interface/generated/'+f
  assert gitbytes(p).splitlines()[1:]==(R/p).read_bytes().splitlines()[1:],p
 allowed={'pl_motion/rtl/motion_executor.v','pl_motion/rtl/continuous_motion.v','pl_motion/rtl/motion_service.v','pl_motion/rtl/motion_stream_rx.v','pl_interface/schema.json','pl_interface/.gitattributes'}
 allowed|={'pl_interface/generated/'+n for n in ['interface_defs.h','interface_defs.vh','registers.md','errors.md']}
 changes=subprocess.check_output(['git','diff','--name-only','c9f2e05','--'],cwd=R,text=True).splitlines()
 # AGENT.md was amended by the project owner with the threads=16 rule.
 # Preserve it outside this component's commits; it is not a delivered RTL input.
 for p in changes:assert p=='AGENT.md' or p.startswith('pl_safety/') or p in allowed,('unrelated tracked mutation',p)
 audit=json.loads((D/'BASELINE_AUDIT.json').read_text(encoding='utf-8'))
 for p,h in audit['sha256_raw'].items():
  if p not in allowed and p!='AGENT.md':assert sha(R/p)==h,('preserved baseline input',p)
 for c in [['pl_interface/generate.py','--check'],['pl_safety/generate.py','--check'],['pl_safety/generate_top.py','--check']]:subprocess.run([sys.executable,*c],cwd=R,check=True)
 return n
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--seal',action='store_true');ap.add_argument('--source-commit');ap.add_argument('--build',default='rxcarry_top6');a=ap.parse_args()
 n=baseline();manifest=D/'SAFETY_RELEASE.json'
 if a.seal:
  assert not manifest.exists(),'Never overwrite sealed evidence'
  names=['rxcarry_units1','rxcarry_phases1','inputs_freeze1','overflow_frozen1','router_final1','rxcarry_real1','timing_regress1','rxcarry_resource1','rxcarry_equivalence1','cdc_final1']
  for name in names:
   test=json.loads((D/'evidence'/name/'result.json').read_text())
   assert test['passed'],name
   for p,h in test.get('source_sha256',{}).items():assert sha(R/p)==h,('tested source changed',name,p)
  legacy=json.loads((D/'evidence/timing_regress1/result.json').read_text())
  assert len(legacy['tests'])==18 and all(x['exit']==0 for x in legacy['tests']),'Incomplete legacy regressions'
  assert 'pl_motion/rtl/motion_stream_rx.v' in legacy['source_sha256'],'Missing changed receiver identity'
  b=D/'build'/a.build;summary=json.loads((b/'summary.json').read_text())
  assert summary['stages']['route']['setup_ns']>1.0 and summary['stages']['route']['hold_ns']>=0,'Final 100MHz route WNS must exceed 1ns and hold must pass'
  assert summary['threads']==16 and summary['timing_target_pass'],'Missing required threads/timing target'
  run=(b/'run.log').read_text(errors='replace')
  assert 'SAFETY_TD_THREADS 16' in run and 'Number of Thread = 16' in run,'Missing actual thread-count proof'
  assert 'set_param flow thread 16' in (b/'run.tcl').read_text(),'Missing explicit startup thread setting'
  assert 'checking invalid constraint(0)' in (b/'route.check').read_text(),'Invalid timing constraint'
  inputs=json.loads((b/'inputs.json').read_text())
  for p,h in inputs['candidate_inputs_sha256'].items():assert sha(b/p)==h,p
  # Match all actual motion RTL, including the authorized receiver timing cut.
  sources=list((D/'rtl').glob('*.v'))+list((D/'generated').glob('*.v*'))+list((R/'pl_motion/rtl').glob('*.v'))
  for p in sources:assert p.read_bytes()==(b/'gp'/p.name).read_bytes(),p
  files=[p for p in D.rglob('*') if p.is_file() and 'build' not in p.relative_to(D).parts and '__pycache__' not in p.parts and p.suffix not in ['.vvp','.exe','.pyc'] and p.name!='SAFETY_RELEASE.json']
  files += [R/'pl_interface/schema.json',R/'pl_interface/.gitattributes']+[R/'pl_interface/generated'/x for x in ['interface_defs.h','interface_defs.vh','registers.md','errors.md']]+[R/'pl_motion/rtl'/x for x in ['motion_executor.v','continuous_motion.v','motion_service.v','motion_stream_rx.v']]
  assert a.source_commit and subprocess.check_output(['git','rev-parse',a.source_commit],cwd=R,text=True).strip()==a.source_commit
  blob_hashes={};blobs=commit_blobs(a.source_commit,[p.relative_to(R).as_posix() for p in files])
  for p in files:
   name=p.relative_to(R).as_posix()
   blob=blobs[name]
   assert blob.replace(b'\r\n',b'\n')==p.read_bytes().replace(b'\r\n',b'\n'),name
   blob_hashes[name]=hashlib.sha256(blob).hexdigest()
  data={'source_commit':a.source_commit,'source_git_blob_sha256':blob_hashes,'status':'RTL_TESTED_ENGINEERING_CANDIDATE_NOT_DEPLOYABLE','baseline':'c9f2e05','old_schema_values_preserved':n,'files_sha256':{p.relative_to(R).as_posix():sha(p) for p in files},'files_lf_sha256':{p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in files},'checkout_policy':'Raw tested bytes retained; only CRLF/LF checkout conversion permitted during verification','full_project':inputs,'hardware_result':summary,'board_validated':False,'physical_parameters_approved':False,'no_bitgen':True}
  manifest.write_text(json.dumps(data,indent=2)+'\n');print('SEALED safety delivery')
 elif manifest.exists():
  m=json.loads(manifest.read_text())
  converted=0
  for p,h in m['files_sha256'].items():
   if sha(R/p)!=h:
    assert hashlib.sha256((R/p).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==m['files_lf_sha256'][p],p
    converted+=1
  blobs=commit_blobs(m['source_commit'],list(m['source_git_blob_sha256']))
  for p,h in m['source_git_blob_sha256'].items():
   blob=blobs[p]
   assert hashlib.sha256(blob).hexdigest()==h,('source Git blob',p)
  print('PASS safety content/Git blob identity; checkout line-ending conversions',converted,'; board/deployment NOT qualified')
 else:print('PASS safety baseline/old ABI checks; unsealed candidate; old values',n)
if __name__=='__main__':main()
