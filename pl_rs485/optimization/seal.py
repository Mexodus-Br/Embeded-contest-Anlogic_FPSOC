"""Seal the optimized candidate separately; never refresh frozen deliveries."""
import argparse,hashlib,json,re,subprocess,zipfile
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'pl_rs485/optimization'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def check(base,hashes):
 for n,h in hashes.items():assert sha(base/n.replace('\\','/'))==h,('evidence/source identity',n)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-commit',required=True);ap.add_argument('--verify',action='store_true');a=ap.parse_args()
 dest=O/'OPTIMIZATION_RELEASE.json'
 if a.verify:
  m=load(dest);assert m['source_commit']==a.source_commit
  for n,h in m['source_sha256_lf'].items():assert hashlib.sha256((R/n).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==h,('canonical source identity',n)
  archive=O/'evidence.zip';assert sha(archive)==m['evidence_sha256'][archive.relative_to(R).as_posix()]
  with zipfile.ZipFile(archive) as z:
   for n,h in m['evidence_sha256'].items():
    if (R/n).exists():assert sha(R/n)==h,('evidence file changed',n)
    else:assert hashlib.sha256(z.read(n)).hexdigest()==h,('archived evidence',n)
  for n,h in m['git_source_blob_sha256'].items():
   assert hashlib.sha256(subprocess.check_output(['git','show',a.source_commit+':'+n],cwd=R)).hexdigest()==h,('source commit blob',n)
  subprocess.run(['python',str(R/'bsp/telemetry/verify_input.py'),'--optimization-manifest',str(O/'top_r1/candidate.json')],check=True,cwd=R,stdout=subprocess.DEVNULL)
  print('PASS optimized candidate source commit / preserved old identity / IP / constraints / evidence');return
 assert not dest.exists(),'Do not overwrite an existing sealed candidate'
 base=load(O/'baseline/manifest.json');check(O/'baseline',base['reports_sha256'])
 check(O/'baseline/project',load(O/'baseline/project_identity.json'))
 comparison=load(O/'top_r1/comparison.json');assert comparison['timing_pass'] and comparison['slice_saved']>0
 assert not comparison['signoff_pass'],'Known independent release blockers must remain visible'
 subprocess.run(['python',str(R/'bsp/telemetry/verify_input.py'),'--optimization-manifest',str(O/'top_r1/candidate.json')],check=True,cwd=R,stdout=subprocess.DEVNULL)
 simdirs=['telemetry_opt20261015r1','telem_parse_opt20261015r1','telem_results_opt20261015r1','telem_irq_opt20261015r1','telem_software_opt20261015r1','software_opt20261015r1','sim_opt20261015r1','sim_opt20261015r2','sim_opt20261015gp_final']
 for name in sorted(set(simdirs)):
  m=load(R/'pl_rs485/evidence'/name/'manifest.json');assert m.get('passed'),name
  check(R/'pl_rs485',m.get('source_sha256',{}))
 assert load(O/'regression_opt20261015r2/result.json')['passed']
 assert load(R/'pl_dma/reports/telemetry_regression_opt20261015r2/result.json')['passed']
 for name in ('telemetry_opt20261015r1','telemetry_system_opt20261015r2','telemetry_system_opt20261015actual'):
  m=load(R/'pl_dma/reports'/name/'result.json');assert m['status']=='PASS';check(R,m['source_sha256'])
 assert load(O/'actual_system_opt20261015actual/result.json')['passed']
 assert load(O/'diff_final4/result.json')['passed'];check(R,load(O/'diff_final4/result.json')['sources_sha256'])
 components=[]
 for name in ('telem_cache_opt20261015_cache1','telem_packet_opt20261015_fifo1'):
  E=R/'pl_dma/reports'/name;m=load(E/'summary.json')
  # The cache run preceded the FIFO change; other collected sources were
  # unused in that fixture. Bind every actual core dependency, not unrelated RTL.
  deps=['pl_rs485/rtl/rs485_latest_cache.v','pl_rs485/rtl/rs485_light_parse.v'] if 'cache' in name else ['pl_rs485/rtl/rs485_telemetry.v']
  hashes={k.replace('\\','/'):v for k,v in m['source_sha256'].items()};check(R,{n:hashes[n] for n in deps})
  assert min(m['stages']['route'].values())>=0
  assert sha(E/'top.v')==m['fixture_sha256'] and sha(E/'clock.sdc')==m['constraint_sha256']
  components.append(E)
 packet=(components[1]/'rtl_netlist.v').read_text()
 assert 'reg [479:0] ram [255:0]' in packet and '#eram                      12' in (components[1]/'route.area').read_text()
 cache=(components[0]/'rtl_netlist.v').read_text()
 assert 'wire [10139:0] \\dut/frozen' in cache,'15*676 frozen bits must survive RTL optimization'
 assert not list((R/'bsp/work/telemetry_opt_r1').rglob('*.bit')),'No bitgen allowed'
 # Archive logs/reports/vectors only, excluding simulator executables/databases.
 files=set()
 files.update(p for p in (O/'baseline/project').rglob('*') if p.is_file())
 for p in O.rglob('*'):
  if p.is_file() and p.suffix in ('.json','.log','.v','.py','.xml','.al','.tcl','.adc','.sdc','.timing','.area','.check','.qor','.txt','.hex') and p.name not in ('OPTIMIZATION_RELEASE.json',):files.add(p)
 for E in components+[R/'pl_dma/reports'/x for x in ('telemetry_opt20261015r1','telemetry_system_opt20261015r2','telemetry_system_opt20261015actual','telemetry_regression_opt20261015r2')]+[R/'pl_rs485/evidence'/x for x in sorted(set(simdirs))]:
  for p in E.rglob('*'):
   if p.is_file() and p.suffix in ('.json','.log','.v','.vh','.tcl','.sdc','.timing','.area','.check','.qor','.hex'):files.add(p)
 # Explicitly retain all completed new GP/software manifests, not just legacy.
 for E in (R/'pl_rs485/evidence').glob('*opt20261015r1'):
  for p in E.iterdir():
   if p.is_file() and p.suffix in ('.json','.log','.hex','.v'):files.add(p)
 sources=set((R/n) for n in base['inputs_sha256'] if '/rtl/' in n or '/generated/' in n or n.endswith(('schema.json','rate_design.json')))
 sources.update(p for p in O.glob('*') if p.suffix in ('.py','.v','.md'))
 sources.add(R/'bsp/telemetry/verify_input.py')
 source_hashes={p.relative_to(R).as_posix():sha(p) for p in sorted(sources)}
 source_lf={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in sorted(sources)}
 blobs={}
 for n,h in source_lf.items():
  blob=subprocess.check_output(['git','show',a.source_commit+':'+n],cwd=R)
  assert hashlib.sha256(blob.replace(b'\r\n',b'\n')).hexdigest()==h,('commit canonical source identity',n)
  blobs[n]=hashlib.sha256(blob).hexdigest()
 Z=O/'evidence.zip';assert not Z.exists()
 with zipfile.ZipFile(Z,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for p in sorted(files):z.write(p,p.relative_to(R).as_posix())
 identity={'identity':'pl-resource-optimization-20261015','source_commit':a.source_commit,'baseline_commit':base['commit'],'frozen_telemetry_commit':'f447116','schema_sha256':sha(R/'pl_interface/schema.json'),'source_sha256':source_hashes,'source_sha256_lf':source_lf,'git_source_blob_sha256':blobs,'evidence_sha256':{p.relative_to(R).as_posix():sha(p) for p in sorted(files|{Z})},'vendor_libraries':base['vendor_libraries'],'constraints_sha256':base['actual_top_review']['constraints_sha256'],'comparison':comparison,'cycle_changes':0,'FIFO_depth':256,'snapshot_rows':15,'snapshot_row_bytes':128,'bitgen':'NOT_EXECUTED','signoff_pass':False,'release_blockers':['protected S2MM-only SYN-5066','RS485 external IO timing qualification','real device speed and board/Linux RX recovery not qualified']}
 dest.write_text(json.dumps(identity,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 print('PASS independent optimized candidate seal:',dest)
if __name__=='__main__':main()
