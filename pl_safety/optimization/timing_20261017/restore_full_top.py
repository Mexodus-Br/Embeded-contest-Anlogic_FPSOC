"""Authenticate complete P&R and re-report its exact geometry at original SDC.

TD may retain an optimization uncertainty through route despite a later set=0.
Clear only user SDC, reload both original files, and export/compare the effective
commands before producing an independent final database. No routing is altered.
"""
import argparse,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[2];D=R/'pl_safety'
sys.path.insert(0,str(D));from build_td import THREADS_TCL

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def commands(p):return [x.strip() for x in p.read_text().splitlines() if x.strip() and not x.lstrip().startswith('#')]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--parent',required=True);ap.add_argument('--tag',required=True);a=ap.parse_args()
 assert all(re.fullmatch(r'[A-Za-z0-9_-]+',x) for x in [a.parent,a.tag])
 p=D/'build'/a.parent;b=D/'build'/a.tag
 log=(p/'run.log').read_text(errors='replace');assert 'SAFETY_RESOURCE_BUILD_COMPLETE' in log and 'Number of Thread = 16' in log and 'SAFETY_TD_THREADS 16' in log
 assert not re.search(r'\bERROR:',log) and 'finish command "route"' in log
 inputs=json.loads((p/'inputs.json').read_text())
 for n,h in inputs['candidate_inputs_sha256'].items():assert sha(p/n)==h,n
 for folder in ['pl_motion/rtl','pl_safety/rtl','pl_safety/generated']:
  for f in (R/folder).glob('*.v*'):assert f.read_bytes()==(p/'gp'/f.name).read_bytes(),('stale parent source',f)
 b.mkdir(exist_ok=False)
 for n in inputs['candidate_inputs_sha256']:
  q=b/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p/n,q)
 project=(b/'system.al').read_text(encoding='utf-8');project=re.sub(r'(<Project [^>]*Path=")[^"]*',lambda m:m[1]+b.as_posix(),project,count=1);(b/'system.al').write_text(project,encoding='utf-8')
 inputs['candidate_inputs_sha256']={n:sha(b/n) for n in inputs['candidate_inputs_sha256']}
 for name in ['gate.area','gate.timing','effective_parameters.tcl']:shutil.copyfile(p/name,b/name)
 for name in ['run.log','run.tcl','inputs.json']:shutil.copyfile(p/name,b/('parent_full_'+name))
 for name in ['place_closure_margin.timing','route_closure_margin.timing','optimization_margin.sdc','restore_nominal.sdc']:
  if (p/name).exists():shutil.copyfile(p/name,b/name)
 proof=E/'constraint_restore_validation1/result.json';proof_data=json.loads(proof.read_text())
 assert proof_data['passed'] and proof_data['threads']==16 and proof_data['extra_setup_uncertainty_ns']==1.25
 for name,h in proof_data['source_sha256'].items():assert sha(R/name)==h,('restoration proof changed',name)
 inputs['inherited_pnr']={'build':a.parent,'place_db_sha256':sha(p/'place.db'),'route_db_sha256':sha(p/'route.db'),'run_log_sha256':sha(p/'run.log'),'input_manifest_sha256':sha(p/'inputs.json'),'restoration_proof_sha256':sha(proof),'geometry_unchanged':True}
 (b/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
 reload=f'''clear_user_sdc
read_adc -file gp/gp.adc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl
'''
 script=f'''cd {b.as_posix()}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
{THREADS_TCL}
import_db {(p/'place.db').as_posix()}
{THREADS_TCL}
{reload}
update_timing -mode manhattan
report_timing_summary -path_num 10 -file place.timing
export_sdc -file nominal_place.sdc
import_db {(p/'route.db').as_posix()}
{THREADS_TCL}
{reload}
update_timing -mode final
report_timing_summary -path_num 10 -file route.timing
report_area -io_info -file route.area
check_timing -verbose -file route.check
report_route_status -drc -file route.drc
export_sdc -file nominal_route.sdc
export_db route.db
puts SAFETY_RESOURCE_BUILD_COMPLETE
exit
'''
 (b/'run.tcl').write_text(script)
 with (b/'run.log').open('w',encoding='utf-8') as f:result=subprocess.run([shutil.which('td_commands_prompt'),(b/'run.tcl').as_posix()],cwd=b,stdout=f,stderr=subprocess.STDOUT,timeout=900)
 log2=(b/'run.log').read_text(errors='replace');assert result.returncode==0 and 'SAFETY_RESOURCE_BUILD_COMPLETE' in log2 and 'Number of Thread = 16' in log2 and not re.search(r'\bERROR:',log2)
 for stage in ['place','route']:
  assert commands(b/('nominal_'+stage+'.sdc'))==commands(b/'gp/gp.sdc'),('effective SDC differs',stage)
  assert all(float(v)==0 for v in re.findall(r'sdc uncertainty:\s*([-\d.]+)ns',(b/(stage+'.timing')).read_text())),('uncertainty persists',stage)
 assert 'checking invalid constraint(0)' in (b/'route.check').read_text()
 stages={}
 for stage in ['gate','place','route']:
  text=(b/(stage+'.timing')).read_text();stages[stage]={k:float(re.search(pattern,text)[1]) for k,pattern in [('setup_ns',r'SWNS:\s*([-\d.]+)ns'),('hold_ns',r'HWNS:\s*([-\d.]+)ns')]}
 summary={'stages':stages,'threads':16,'physical_optimization':'inherited_authenticated_complete_PnR;effective_original_SDC_commands_verified','inherited_pnr':inputs['inherited_pnr'],'effective_nominal_sdc_sha256':sha(b/'nominal_route.sdc'),'wns_target_ns_exclusive':1.0,'timing_target_pass':stages['route']['setup_ns']>1.0 and stages['route']['hold_ns']>=0,'critical_warnings':list(dict.fromkeys(x for x in (log+'\n'+log2).splitlines() if 'CRITICAL-WARNING' in x)),'signoff_pass':False,'board_validated':False,'bitgen':False}
 (b/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
