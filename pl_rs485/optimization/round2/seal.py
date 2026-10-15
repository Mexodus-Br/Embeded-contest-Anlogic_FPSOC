"""Seal round2 independently, retaining both old releases and all failed trials."""
import argparse,hashlib,json,subprocess,zipfile
from pathlib import Path
E=Path(__file__).resolve().parent;O=E.parent;R=E.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def check_sources(hashes):
 for n,h in hashes.items():assert sha(R/n.replace('\\','/'))==h,('source/evidence mismatch',n)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-commit',required=True);ap.add_argument('--verify',action='store_true');ap.add_argument('--preflight',action='store_true');a=ap.parse_args();dest=E/'ROUND2_RELEASE.json';archive=E/'evidence.zip'
 assert not (a.verify and a.preflight)
 if a.verify:
  m=load(dest);assert m['source_commit']==a.source_commit
  for n,h in m['source_sha256_lf'].items():assert hashlib.sha256((R/n).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==h,n
  for n,h in m['git_blob_sha256'].items():assert hashlib.sha256(subprocess.check_output(['git','show',a.source_commit+':'+n],cwd=R)).hexdigest()==h,n
  assert sha(archive)==m['archive_sha256']
  with zipfile.ZipFile(archive) as z:
   for n,h in m['evidence_sha256'].items():
    assert hashlib.sha256(z.read(n)).hexdigest()==h,n
    if (R/n).is_file():
     data=(R/n).read_bytes()
     if hashlib.sha256(data).hexdigest()!=h:
      assert n in m['source_sha256_lf'] and hashlib.sha256(data.replace(b'\r\n',b'\n')).hexdigest()==m['source_sha256_lf'][n],n
  check_sources(m['preserved_release_sha256'])
  subprocess.run(['python',str(R/'bsp/telemetry/verify_input.py'),'--optimization-manifest',str(O/'top_r2main/candidate.json')],check=True,cwd=R,stdout=subprocess.DEVNULL)
  print('PASS round2 source/Git/evidence/IP/schema/constraints identity; user acceptance and signoff remain pending');return
 assert not dest.exists() and not archive.exists(),'Never overwrite a sealed candidate'
 inputs=load(O/'top_r2main/inputs.json');check_sources(inputs['inputs_sha256'])
 comparison=load(E/'TOP_COMPARISON.json');assert comparison['timing_pass'] and not comparison['signoff_pass']
 assert comparison['delta_vs_parent']['slice']<0
 for d in ['control_timing2','ram_cow4','ram_legacy1','identity']:
  assert load(E/d/'result.json')['passed'],d
 check_sources(load(E/'control_timing2/result.json')['source_sha256'])
 for d in ['ram_cow4','ram_legacy1']:check_sources(load(E/d/'transport/result.json')['sources_sha256'])
 assert load(O/'regression_opt2r1/result.json')['passed']
 assert load(O/'actual_system_opt2actual/result.json')['passed']
 assert load(R/'pl_dma/reports/telemetry_regression_opt2r1/result.json')['passed']
 for d in ['telemetry_opt2r1','telemetry_system_opt2r1','telemetry_system_opt2actual']:
  m=load(R/'pl_dma/reports'/d/'result.json');assert m['status']=='PASS';check_sources(m['source_sha256'])
 component=R/'pl_dma/reports/telem_cache_opt2cache2';cm=load(component/'summary.json')
 deps={n.replace('\\','/'):h for n,h in cm['source_sha256'].items()};check_sources({n:deps[n] for n in ['pl_rs485/rtl/rs485_latest_cache.v','pl_rs485/rtl/rs485_light_parse.v']})
 assert min(cm['stages']['route'].values())>=0
 net=(component/'rtl_netlist.v').read_text(encoding='utf-8');assert 'reg [255:0] ram [63:0]' in net and net.count('  ram_w6x256_r6x256 #(')==2
 assert '#eram                      14' in (component/'route.area').read_text(encoding='utf-8')
 subprocess.run(['python',str(R/'bsp/telemetry/verify_input.py'),'--optimization-manifest',str(O/'top_r2main/candidate.json')],check=True,cwd=R,stdout=subprocess.DEVNULL)
 # Validate old releases from their original Git blobs, independently of the
 # intentionally changed current RTL. The frozen default gate is not bypassed.
 preserved={}
 for n in ['pl_rs485/optimization/OPTIMIZATION_RELEASE.json','pl_rs485/optimization/evidence.zip']:
  original=subprocess.check_output(['git','show','5f88d0f:'+n],cwd=R);assert sha(R/n)==hashlib.sha256(original).hexdigest();preserved[n]=sha(R/n)
 old=load(O/'OPTIMIZATION_RELEASE.json')
 for n,h in old['git_source_blob_sha256'].items():assert hashlib.sha256(subprocess.check_output(['git','show',old['source_commit']+':'+n],cwd=R)).hexdigest()==h,n
 assert not list((R/'bsp/work/telemetry_opt_r2main').rglob('*.bit'))
 if a.preflight:
  print('PASS round2 build/test/IP/schema/storage/old-release preflight; no files sealed');return
 source_names=set(inputs['inputs_sha256'])|{'bsp/telemetry/verify_input.py','pl_interface/schema.json'}
 for folder,pattern in [(R/'pl_rs485/generated','*'),(R/'pl_interface/generated','*'),(E,'*.py'),(E,'*.md'),(E,'*.v'),(E/'baseline','*.v')]:
  source_names.update(p.relative_to(R).as_posix() for p in folder.glob(pattern) if p.is_file())
 source_names.add((E/'BASELINE.json').relative_to(R).as_posix())
 source_lf={n:hashlib.sha256((R/n).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for n in sorted(source_names)}
 blobs={n:hashlib.sha256(subprocess.check_output(['git','show',a.source_commit+':'+n],cwd=R)).hexdigest() for n in sorted(source_names)}
 for n,h in source_lf.items():assert hashlib.sha256(subprocess.check_output(['git','show',a.source_commit+':'+n],cwd=R).replace(b'\r\n',b'\n')).hexdigest()==h,n
 roots=[E,O/'top_r2main',O/'regression_opt2r1',O/'actual_system_opt2actual',component,R/'pl_dma/reports/telem_cache_opt2cache1',R/'pl_dma/reports/telemetry_opt2r1',R/'pl_dma/reports/telemetry_system_opt2r1',R/'pl_dma/reports/telemetry_system_opt2actual',R/'pl_dma/reports/telemetry_regression_opt2r1']
 roots += [p for p in (R/'pl_rs485/evidence').iterdir() if p.is_dir() and 'opt2r1' in p.name]
 suffixes={'.py','.v','.vh','.md','.json','.log','.timing','.area','.check','.qor','.tcl','.sdc','.adc','.hex','.txt','.drc','.rpt'}
 evidence={}
 for root in roots:
  for p in root.rglob('*'):
   if p.is_file() and p.suffix in suffixes and p not in [dest,archive] and '__pycache__' not in p.parts:evidence[p.relative_to(R).as_posix()]=sha(p)
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for n in sorted(evidence):z.write(R/n,n)
 manifest={'identity':'pl-resource-optimization-round2-20261015','source_commit':a.source_commit,'start_commit':load(E/'BASELINE.json')['start_commit'],'parent_candidate':'49e8ac6','acceptance_status':'CANDIDATE_PENDING_USER_REVIEW','timing_pass':True,'signoff_pass':False,'allowed_cycle_change':'valid telemetry cache row AR-to-R +1 clock; all other interfaces unchanged','source_sha256_lf':source_lf,'git_blob_sha256':blobs,'preserved_release_sha256':preserved,'candidate':inputs['candidate'],'project_inputs_sha256':inputs['project_inputs_sha256'],'comparison':comparison,'evidence_sha256':evidence,'archive_sha256':sha(archive),'local_checkpoint_sha256':{p.name:sha(p) for p in (R/'bsp/work/telemetry_opt_r2main').glob('*.db')},'no_board_or_deployment':True}
 dest.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8');print('SEALED',len(evidence),'evidence files; archive bytes',archive.stat().st_size)
if __name__=='__main__':main()
