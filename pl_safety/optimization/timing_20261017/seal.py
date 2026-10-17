"""Independent strict timing candidate identity; never overwrites old releases."""
import argparse,hashlib,json,re,subprocess,zipfile,sys
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[2];D=R/'pl_safety';sys.path[:0]=[str(E),str(D)]
from identity import check
from verify_delivery import commit_blobs

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def verify_hashes(hashes):
 for name,h in hashes.items():assert sha(R/name.replace('\\','/'))==h,('tested/built bytes changed',name)
def input_identity(b):
 m=load(b/'inputs.json');verify_hashes({(b/p).relative_to(R).as_posix():h for p,h in m['candidate_inputs_sha256'].items()})
 before=load(D/'evidence/predecode_top7_paused/inputs.json')['candidate_inputs_sha256'];after=m['candidate_inputs_sha256']
 before={n.replace('\\','/'):h for n,h in before.items()};after={n.replace('\\','/'):h for n,h in after.items()}
 assert set(before)==set(after),'Full-top input file set/capacity changed'
 allowed={'gp/safety_controller.v','gp/motion_stream_rx.v','gp/motion_service.v','system.al'}
 for n,h in before.items():
  if n not in allowed:assert after[n]==h,('unchanged PS/IP/RTL/constraint input',n)
 def normalize_project(p):return re.sub(r'(<Project [^>]*Path=")[^"]*',r'\1<WORKSPACE>',p.read_text(encoding='utf-8'))
 assert normalize_project(b/'system.al')==normalize_project(D/'evidence/predecode_top7_paused/system.al')
 for folder in ['pl_motion/rtl','pl_safety/rtl','pl_safety/generated']:
  for p in (R/folder).glob('*.v*'):assert p.read_bytes()==(b/'gp'/p.name).read_bytes(),('stale full-top source',p)
 return m

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--build',required=True);ap.add_argument('--prefix',required=True);ap.add_argument('--cdc',required=True);ap.add_argument('--nets',required=True);ap.add_argument('--pins',required=True);ap.add_argument('--source-commit');ap.add_argument('--controller-eq',default='counter_eq1');ap.add_argument('--telemetry-system',default='closure_perf1');ap.add_argument('--verify',action='store_true');ap.add_argument('--preflight',action='store_true');a=ap.parse_args();dest=E/'TIMING_RELEASE.json';archive=E/'evidence.zip'
 if a.verify:
  m=load(dest);assert sha(archive)==m['archive_sha256']
  blobs=commit_blobs(m['source_commit'],list(m['git_blob_sha256']))
  for n,h in m['git_blob_sha256'].items():assert hashlib.sha256(blobs[n]).hexdigest()==h,n
  for n,h in m['source_lf_sha256'].items():assert hashlib.sha256((R/n).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==h,n
  with zipfile.ZipFile(archive) as z:
   for n,h in m['evidence_sha256'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
  check();print('PASS source/Git/archive/old-ABI identity; not a deployment release');return
 assert not dest.exists() and not archive.exists(),'Never overwrite sealed evidence'
 abi=check();b=D/'build'/a.build;inputs=input_identity(b);summary=load(b/'summary.json')
 assert summary['threads']==16 and summary['stages']['route']['setup_ns']>1.0 and summary['stages']['route']['hold_ns']>=0
 assert summary['timing_target_pass'] and not summary['signoff_pass'] and not summary['bitgen']
 assert 'checking invalid constraint(0)' in (b/'route.check').read_text()
 assert all(float(v)==0 for v in re.findall(r'sdc uncertainty:\s*([-\d.]+)ns',(b/'route.timing').read_text())),'Final report retains an optimization budget'
 if (b/'nominal_route.sdc').exists():
  commands=lambda p:[x.strip() for x in p.read_text().splitlines() if x.strip() and not x.lstrip().startswith('#')]
  assert commands(b/'nominal_route.sdc')==commands(b/'gp/gp.sdc'),'Effective final constraint commands changed'
 compare=load(E/('comparison_'+a.build+'.json'));assert compare['target_pass'] and compare['original_constraints_byte_equal']
 if compare['new_warning_codes']:
  review=compare['warning_review'];assert review['passed'] and review['route_db_sha256']==sha(b/'route.db') and set(compare['new_warning_codes'])<=set(review['reviewed_codes'])
 cdc=load(E/a.cdc/'result.json');assert cdc['passed'] and cdc['build']==a.build and cdc['threads']==16 and cdc['route_db_sha256']==sha(b/'route.db')
 for tag in [a.nets,a.pins]:assert load(E/tag/'result.json')['passed'] and load(E/tag/'result.json')['build']==a.build and load(E/tag/'result.json')['route_db_sha256']==sha(b/'route.db')
 assert load(E/a.pins/'result.json')['source_net_table_sha256']==sha(E/a.nets/'nets.tsv')
 for name in ['checking no clock','checking clock definition','checking invalid constraint','checking combinational loops','checking no path constraints','checking shadowed/ignored timing exception constraints']:
  assert name+'(0)' in (b/'route.check').read_text(),('Unexplained essential constraint/clock/loop issue',name)
 tests=[a.prefix+'_'+s for s in ['units1','phases1','overflow1','resource1','real1','regress1']]+['inputs_freeze1','router_final1','predecode_equivalence1']
 for tag in tests:
  m=load(D/'evidence'/tag/'result.json');assert m['passed'],tag;verify_hashes(m.get('source_sha256',{}))
 assert len(load(D/'evidence'/(a.prefix+'_regress1')/'result.json')['tests'])==18
 m=load(E/a.controller_eq/'result.json');assert m['passed'];verify_hashes(m['source_sha256'])
 if (R/'pl_motion/rtl/motion_service.v').read_bytes().replace(b'\r\n',b'\n')!=(E/'baseline/motion_service.v').read_bytes().replace(b'\r\n',b'\n'):
  m=load(E/'cofactor_production_eq1/result.json');assert m['passed'] and m['cofactor_exhaustive_checks']==65536;verify_hashes(m['source_sha256'])
 assert load(E/'telemetry_regress1/result.json')['passed']
 telem=load(R/'pl_dma/reports'/('telemetry_system_'+a.telemetry_system)/'result.json');assert telem['status']=='PASS';verify_hashes(telem['source_sha256'])
 if (R/'pl_motion/rtl/motion_stream_rx.v').read_bytes().replace(b'\r\n',b'\n')!=(E/'baseline/motion_stream_rx.v').read_bytes().replace(b'\r\n',b'\n'):
  m=load(D/'evidence'/(a.prefix+'_equivalence1')/'result.json');assert m['passed'];verify_hashes(m['source_sha256']);tests.append(a.prefix+'_equivalence1')
 else:
  m=load(D/'evidence/rxcarry_equivalence1/result.json');assert m['passed'];verify_hashes(m['source_sha256'])
 assert load(E/'deadline_math2/result.json')['passed']
 if a.preflight:print('PASS strict timing/full-top/functional/CDC/ABI preflight');return
 assert a.source_commit
 sources=set()
 for folder,pattern in [(D/'rtl','*.v'),(D/'generated','*'),(R/'pl_motion/rtl','*.v'),(E,'*.py'),(E,'*.md'),(E,'*.v'),(E/'baseline','*.v')]:
  sources.update(p.relative_to(R).as_posix() for p in folder.glob(pattern) if p.is_file())
 sources|={'pl_interface/schema.json','PHASE0_CONSTRAINTS.md','pl_safety/CONTRACT.md','pl_safety/SAFETY_HANDOFF.md','pl_safety/VALIDATION.md','pl_safety/FAILURES.md','pl_safety/build_td.py','pl_safety/archive_reports.py','pl_safety/verify_delivery.py','pl_safety/config/production.json','pl_safety/config/simulation.json','pl_safety/config/resource_fixture.json',E.relative_to(R).as_posix()+'/BASELINE.json'}
 sources|={'pl_interface/generated/'+n for n in ['interface_defs.h','interface_defs.vh','registers.md','errors.md']}
 blobs=commit_blobs(a.source_commit,sorted(sources));source_lf={}
 for n in sources:
  data=(R/n).read_bytes().replace(b'\r\n',b'\n');assert data==blobs[n].replace(b'\r\n',b'\n'),n;source_lf[n]=hashlib.sha256(data).hexdigest()
 roots=[E,D/'evidence'/a.build]+[D/'evidence'/tag for tag in tests]
 roots += [p for p in (R/'pl_rs485/evidence').glob('*closure_perf1') if p.is_dir()]
 roots += [R/'pl_dma/reports'/('telemetry_system_'+a.telemetry_system)]
 extensions={'.py','.v','.vh','.h','.md','.json','.log','.logw','.tcl','.timing','.check','.area','.qor','.rpt','.tsv','.sdc','.adc','.al','.hex','.txt'}
 evidence={}
 for root in roots:
  for p in root.rglob('*'):
   if p.is_file() and p.suffix in extensions and p not in [dest,archive] and '__pycache__' not in p.parts:evidence[p.relative_to(R).as_posix()]=sha(p)
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for n in sorted(evidence):z.write(R/n,n)
 m={'identity':'PL-control-path-closure-20261017','source_commit':a.source_commit,'status':'PERFORMANCE_VALIDATED_ENGINEERING_CANDIDATE_NOT_DEPLOYABLE','baseline_commit':'5ccd875','authorization_commit':'2f09a56','old_abi':abi,'build':a.build,'full_project':inputs,'hardware':summary,'comparison':compare,'tests':tests,'source_lf_sha256':source_lf,'git_blob_sha256':{n:hashlib.sha256(v).hexdigest() for n,v in blobs.items()},'evidence_sha256':evidence,'archive_sha256':sha(archive),'route_db_sha256':sha(b/'route.db'),'no_board_no_images':True,'signoff_pass':False}
 dest.write_text(json.dumps(m,indent=2)+'\n');print('SEALED',len(evidence),'files',archive.stat().st_size,'bytes')
if __name__=='__main__':main()
