"""Read-only TD experiment: prove margin insertion/removal preserves baseline STA."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
from build_td import THREADS_TCL
R=Path(__file__).resolve().parents[1];D=R/'pl_safety'
ap=argparse.ArgumentParser();ap.add_argument('--build',required=True);ap.add_argument('--tag',required=True);a=ap.parse_args()
b=D/'build'/a.build;out=D/'evidence'/a.tag;out.mkdir(exist_ok=False)
(out/'margin.sdc').write_text('set_clock_uncertainty -setup 1.25 [get_clocks board_100m]\n')
(out/'restore.sdc').write_text('set_clock_uncertainty -setup 0 [get_clocks board_100m]\n')
tcl=f'''cd {out.as_posix()}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db {(b/'route.db').as_posix()}
{THREADS_TCL}
read_adc -file {(b/'gp/gp.adc').as_posix()}
read_sdc {(b/'gp/gp.sdc').as_posix()}
read_sdc {(b/'gp/ps-generated-properties.tcl').as_posix()}
update_timing -mode final
report_timing_summary -file original.timing -path_num 1
read_sdc {(out/'margin.sdc').as_posix()}
update_timing -mode final
report_timing_summary -file margin.timing -path_num 1
read_sdc {(out/'restore.sdc').as_posix()}
update_timing -mode final
report_timing_summary -file restored.timing -path_num 1
check_timing -verbose -file restored.check
puts SAFETY_MARGIN_PROBE_COMPLETE
exit
'''
(out/'probe.tcl').write_text(tcl)
with (out/'probe.log').open('w') as f:r=subprocess.run([shutil.which('td_commands_prompt'),(out/'probe.tcl').as_posix()],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
values={}
for name in ['original','margin','restored']:
 if not (out/(name+'.timing')).exists():continue
 text=(out/(name+'.timing')).read_text()
 values[name]={key:float(re.search(pattern,text)[1]) for key,pattern in [('setup_ns',r'SWNS:\s*([-\d.]+)ns'),('hold_ns',r'HWNS:\s*([-\d.]+)ns')]}
log=(out/'probe.log').read_text(errors='replace')
passed=r.returncode==0 and 'SAFETY_MARGIN_PROBE_COMPLETE' in log and 'Number of Thread = 16' in log
passed=passed and len(values)==3 and values['original']==values['restored'] and abs(values['original']['setup_ns']-values['margin']['setup_ns']-1.25)<0.002 and values['original']['hold_ns']==values['margin']['hold_ns']
passed=passed and (out/'restored.check').exists() and 'checking invalid constraint(0)' in (out/'restored.check').read_text()
passed=passed and values['original']==json.loads((b/'summary.json').read_text())['stages']['route']
(out/'result.json').write_text(json.dumps({'passed':passed,'purpose':'Tool margin semantics only; no placement/routing or RTL qualification','threads':16,'build':a.build,'route_db_sha256':hashlib.sha256((b/'route.db').read_bytes()).hexdigest(),'optimization_clock':'board_100m','extra_setup_uncertainty_ns':1.25,'stages':values,'no_bitgen':True},indent=2)+'\n')
assert passed,values
print('PASS original setup/hold restored exactly; 1.25ns tighter optimization budget',values)
