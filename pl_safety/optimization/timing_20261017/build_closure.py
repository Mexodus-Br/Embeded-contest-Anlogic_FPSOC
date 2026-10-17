"""Full real top; tighter optimization budget, final reports at original budget.

Retains all original build_td authentication, thread and strict-target assertions.
No protected IP, project constraints, clock periods or board outputs are edited.
"""
import hashlib,json,re,sys
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[2];D=R/'pl_safety'
sys.path.insert(0,str(D))

def board_setup(path):
 return float(re.search(r'Path Group\s*:\s*board_100m -> board_100m.*?Max\s*:\s*SWNS\s*([-\d.]+)ns',path.read_text(),re.S)[1])

def main():
 assert '--tag' in sys.argv and '--resume' not in sys.argv and '--prepare-only' not in sys.argv
 tag=sys.argv[sys.argv.index('--tag')+1];assert re.fullmatch(r'[A-Za-z0-9_-]+',tag)
 proof=E/'constraint_restore_validation1/result.json';p=json.loads(proof.read_text())
 assert p['passed'] and p['threads']==16 and p['extra_setup_uncertainty_ns']==1.25 and p['before']['hold_ns']==p['restored']['hold_ns']
 for name,h in p['source_sha256'].items():assert hashlib.sha256((R/name).read_bytes()).hexdigest()==h,('restoration proof changed',name)
 source=(D/'build_td.py').read_text()
 old="script=f'''cd {b.as_posix()}"
 new="(b/'optimization_margin.sdc').write_text('set_clock_uncertainty -setup 1.25 [get_clocks board_100m]\\n')\n (b/'restore_nominal.sdc').write_text('set_clock_uncertainty -setup 0 [get_clocks board_100m]\\n')\n "+old
 assert source.count(old)==1;source=source.replace(old,new)
 old='''legalize_phy_inst
place
update_timing -mode manhattan
report_timing_summary -file place.timing -path_num 10
export_db place.db
route
update_timing -mode final
report_timing_summary -file route.timing -path_num 10'''
 new='''read_sdc optimization_margin.sdc
legalize_phy_inst
place
update_timing -mode manhattan
report_timing_summary -file place_closure_margin.timing -path_num 10
clear_user_sdc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl
update_timing -mode manhattan
report_timing_summary -file place.timing -path_num 10
export_db place.db
read_sdc optimization_margin.sdc
route
update_timing -mode final
report_timing_summary -file route_closure_margin.timing -path_num 10
clear_user_sdc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl
update_timing -mode final
report_timing_summary -file route.timing -path_num 10'''
 assert source.count(old)==1;source=source.replace(old,new)
 exec(compile(source,str(D/'build_td.py'),'exec'),{'__file__':str(D/'build_td.py'),'__name__':'__main__'})
 b=D/'build'/tag;m=json.loads((b/'summary.json').read_text())
 for stage in ['place','route']:
  nominal=board_setup(b/(stage+'.timing'));tight=board_setup(b/(stage+'_closure_margin.timing'))
  assert abs(nominal-tight-1.25)<.002,('budget restoration',stage,nominal,tight)
  hold=lambda f:float(re.search(r'HWNS:\s*([-\d.]+)ns',f.read_text())[1])
  assert hold(b/(stage+'.timing'))==hold(b/(stage+'_closure_margin.timing'))
 for name in ['gp/gp.sdc','gp/gp.adc','gp/ps-generated-properties.tcl']:
  assert (b/name).read_bytes()==(D/'evidence/predecode_top7_paused'/name).read_bytes()
 m['physical_optimization']+=';place_and_route_extra_1p25ns_setup_budget_restored_before_final_reports'
 m['budget_restoration']={'extra_setup_uncertainty_ns':1.25,'nominal_setup_uncertainty_sdc_ns':0,'hold_budget_unchanged':True,'proof_sha256':hashlib.sha256(proof.read_bytes()).hexdigest(),'original_constraint_bytes_preserved':True}
 (b/'summary.json').write_text(json.dumps(m,indent=2)+'\n');print('PASS original-budget final reports authenticated',tag)
if __name__=='__main__':main()
