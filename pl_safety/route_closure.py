"""Reroute an authenticated full-top placement with a tighter setup budget.

The nominal 10ns constraints, RTL and prior reports are preserved. Both the
stricter optimization report and the restored nominal report are retained.
"""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
from build_td import THREADS_TCL
R=Path(__file__).resolve().parents[1];D=R/'pl_safety'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def timing(p):
 text=p.read_text()
 return {k:float(re.search(pattern,text)[1]) for k,pattern in [('setup_ns',r'SWNS:\s*([-\d.]+)ns'),('hold_ns',r'HWNS:\s*([-\d.]+)ns')]}
def board_setup(p):
 return float(re.search(r'Path Group\s*:\s*board_100m -> board_100m.*?Max\s*:\s*SWNS\s*([-\d.]+)ns',p.read_text(),re.S)[1])

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--build',required=True);ap.add_argument('--tag',required=True);ap.add_argument('--margin-proof',default='margin_semantics4');a=ap.parse_args()
 assert all(re.fullmatch(r'[A-Za-z0-9_-]+',n) for n in [a.build,a.tag,a.margin_proof])
 proof=D/'evidence'/a.margin_proof/'result.json';p=json.loads(proof.read_text())
 assert p['passed'] and p['threads']==16 and p['optimization_clock']=='board_100m'
 assert p['extra_setup_uncertainty_ns']==1.25 and p['stages']['original']==p['stages']['restored']
 source=D/'build'/a.build;b=D/'build'/a.tag
 log=(source/'run.log').read_text(errors='replace')
 assert 'finish command "export_db place.db"' in log,'Parent placement must be fully written'
 assert 'SAFETY_TD_THREADS 16' in log and 'Number of Thread = 16' in log
 data=json.loads((source/'inputs.json').read_text())
 for name,h in data['candidate_inputs_sha256'].items():assert sha(source/name)==h,name
 for folder in ['pl_motion/rtl','pl_safety/rtl','pl_safety/generated']:
  for file in (R/folder).glob('*.v*'):assert file.read_bytes()==(source/'gp'/file.name).read_bytes(),('parent RTL changed',file)
 b.mkdir(exist_ok=False)
 (b/'parent_place_run.log').write_bytes((source/'run.log').read_bytes())
 shutil.copyfile(source/'run.tcl',b/'parent_full_run.tcl')
 shutil.copyfile(source/'inputs.json',b/'parent_inputs.json')
 for name in data['candidate_inputs_sha256']:
  target=b/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,target)
 project=(b/'system.al').read_text(encoding='utf-8')
 project=re.sub(r'(<Project [^>]*Path=")[^"]*',lambda m:m[1]+b.as_posix(),project,count=1)
 (b/'system.al').write_text(project,encoding='utf-8')
 data['candidate_inputs_sha256']={name:sha(b/name) for name in data['candidate_inputs_sha256']}
 data['inherited_placement']={'build':a.build,'inputs_sha256':sha(source/'inputs.json'),'place_db_sha256':sha(source/'place.db'),'parent_place_run_log_sha256':sha(b/'parent_place_run.log'),'parent_full_run_tcl_sha256':sha(b/'parent_full_run.tcl'),'margin_proof':a.margin_proof,'margin_proof_sha256':sha(proof),'extra_setup_uncertainty_ns':1.25,'optimization_clock':'board_100m','nominal_clocks_unchanged':True}
 (b/'inputs.json').write_text(json.dumps(data,indent=2)+'\n')
 for name in ['gate.area','gate.timing','place.timing','effective_parameters.tcl']:
  if (source/name).exists():shutil.copyfile(source/name,b/name)
 (b/'closure_margin.sdc').write_text('set_clock_uncertainty -setup 1.25 [get_clocks board_100m]\n')
 (b/'restore_nominal.sdc').write_text('set_clock_uncertainty -setup 0 [get_clocks board_100m]\n')
 script=f'''cd {b.as_posix()}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db {(source/'place.db').as_posix()}
{THREADS_TCL}
read_adc -file gp/gp.adc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl
read_sdc closure_margin.sdc
route
update_timing -mode final
report_timing_summary -file route_closure_margin.timing -path_num 10
read_sdc restore_nominal.sdc
update_timing -mode final
report_timing_summary -file route.timing -path_num 10
report_area -io_info -file route.area
check_timing -verbose -file route.check
report_route_status -drc -file route.drc
export_db route.db
puts SAFETY_RESOURCE_BUILD_COMPLETE
exit
'''
 (b/'run.tcl').write_text(script)
 with (b/'run.log').open('w',encoding='utf-8') as f:
  result=subprocess.run([shutil.which('td_commands_prompt'),(b/'run.tcl').as_posix()],cwd=b,stdout=f,stderr=subprocess.STDOUT,timeout=7200)
 log=(b/'run.log').read_text(errors='replace')
 assert result.returncode==0 and 'SAFETY_RESOURCE_BUILD_COMPLETE' in log and not re.search(r'\bERROR:',log),'TD failed; reports retained'
 assert 'SAFETY_TD_THREADS 16' in log and 'Number of Thread = 16' in log
 assert not re.search(r'Global iterations in (?!16\b)\d+ thread',log)
 stages={name:timing(b/(name+'.timing')) for name in ['gate','place','route']}
 margin=timing(b/'route_closure_margin.timing')
 nominal_board=board_setup(b/'route.timing');tight_board=board_setup(b/'route_closure_margin.timing')
 assert abs(nominal_board-tight_board-1.25)<0.002,'Nominal board restoration differs from verified semantics'
 assert stages['route']['hold_ns']==margin['hold_ns'],'Hold budget must remain unchanged'
 assert 'checking invalid constraint(0)' in (b/'route.check').read_text()
 warnings=list(dict.fromkeys(line for line in ((b/'parent_place_run.log').read_text(errors='replace')+'\n'+log).splitlines() if 'CRITICAL-WARNING' in line))
 summary={'stages':stages,'threads':16,'physical_optimization':'inherited_parent_placement; stricter_board_setup_route','inherited_placement':data['inherited_placement'],'route_under_extra_1p25ns_setup_budget':margin,'board_budget_proof':{'nominal_setup_ns':nominal_board,'tightened_setup_ns':tight_board},'nominal_setup_uncertainty_sdc_ns':0,'wns_target_ns_exclusive':1.0,'timing_target_pass':stages['route']['setup_ns']>1.0 and stages['route']['hold_ns']>=0,'critical_warnings':warnings,'signoff_pass':False,'board_validated':False,'bitgen':False}
 (b/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
