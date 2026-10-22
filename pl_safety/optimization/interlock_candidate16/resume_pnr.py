"""Resume the exact candidate16 gate DB; independent, no hashes or bitgen."""
import argparse,contextlib,ctypes,json,os,re,subprocess,sys,traceback
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
B=ROOT/'pl_safety/build/interlock_route16';OUT=HERE/'launch_r2'
ATTEMPT='r1';TASK_NAME=None
THREADS='''set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
puts "INTERLOCK_TD_THREADS [get_param flow thread]"
get_num_thread
'''
ORIGINAL='''clear_user_sdc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl
'''
def stamp():return datetime.now(timezone(timedelta(hours=8))).isoformat()
def write(p,data):
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(data,indent=2)+'\n');t.replace(p)
def main():
 in_job=ctypes.c_int()
 kernel=ctypes.windll.kernel32
 kernel.GetCurrentProcess.restype=ctypes.c_void_p
 kernel.IsProcessInJob.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_int)]
 assert kernel.IsProcessInJob(kernel.GetCurrentProcess(),None,ctypes.byref(in_job))
 write(OUT/'started.json',{'started_at':stamp(),'process_id':os.getpid(),'in_windows_job':bool(in_job.value),'hashes_computed':False})
 summary=B/('resume_pnr_'+ATTEMPT+'_summary.json');script=B/('resume_pnr_'+ATTEMPT+'.tcl');log_path=B/('resume_pnr_'+ATTEMPT+'.log')
 result={'passed':False,'timing_pass':False,'signoff_pass':False,'hashes_computed':False,
         'resumed_from':'gate.db','original_attempt':'run.log','started_at':stamp()}
 try:
  assert not summary.exists() and not script.exists() and not log_path.exists()
  assert not (B/'place.db').exists() and not (B/'route.db').exists()
  for folder in ['pl_motion/rtl','pl_rs485/rtl','pl_safety/rtl','pl_safety/generated']:
   for p in (ROOT/folder).glob('*.v*'):assert p.read_bytes()==(B/'gp'/p.name).read_bytes(),p
  for folder in ['pl_rs485/generated','pl_interface/generated']:
   for p in (ROOT/folder).glob('*.vh'):assert p.read_bytes()==(B/'gp'/p.name).read_bytes(),p
  base=ROOT/'pl_safety/build/closure_cofactor_route5'
  for name in ['gp/gp.sdc','gp/gp.adc','gp/ps-generated-properties.tcl','gp/axi_dma.v',
               'gp/axi_protocol_converter_merge.v','gp/axi_dma_func_pkg.vh','gp/axi_dma_param_pkg.vh']:
   assert (B/name).read_bytes()==(base/name).read_bytes(),name
  real=json.loads((HERE/'launch_r1/real_result.json').read_text())
  assert real['completed'] and real['passed'] and len(real['cases'])==3
  gate_before=(B/'gate.db').read_bytes()
  script.write_text(f'''cd {B.as_posix()}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
{THREADS}
import_db {(B/'gate.db').as_posix()}
{THREADS}
{ORIGINAL}
set_param place hfn_opt_effort high
set_param place max_fanout 128
set_param place opt_timing high
set_param place logic_level_opt on
 report_param -all -file resume_effective_parameters_{ATTEMPT}.tcl
read_sdc place_budget.sdc
legalize_phy_inst
place
update_timing -mode manhattan
report_timing_summary -file place_budget.timing -path_num 10
{ORIGINAL}
update_timing -mode manhattan
report_timing_summary -file place.timing -path_num 10
export_db place.db
{THREADS}
{ORIGINAL}
read_sdc route_budget.sdc
route
update_timing -mode final
report_timing_summary -file route_budget.timing -path_num 10
{ORIGINAL}
export_sdc -file nominal_route.sdc
update_timing -mode final
report_timing_summary -file route.timing -path_num 10
report_area -io_info -file route.area
check_timing -verbose -file route.check
report_route_status -drc -file route.drc
export_db route.db
puts INTERLOCK_RESUMED_ROUTE_COMPLETE
exit
''')
  exe='D:/Anlogic/TD_Release_2026.1_SP2.200.067/bin/td_commands_prompt.exe'
  with log_path.open('w',encoding='utf-8') as log:
   p=subprocess.run([exe,script.as_posix()],cwd=B,stdout=log,stderr=subprocess.STDOUT,
                    timeout=28800,creationflags=subprocess.CREATE_NO_WINDOW)
  text=log_path.read_text(errors='replace')
  assert p.returncode==0 and 'INTERLOCK_RESUMED_ROUTE_COMPLETE' in text
  assert not re.search(r'\bERROR:|TMR-250[79]',text)
  assert 'INTERLOCK_TD_THREADS 16' in text and 'Number of Thread = 16' in text
  stages={}
  for stage in ['gate','place','route']:
   t=(B/(stage+'.timing')).read_text()
   stages[stage]={k:float(re.search(pat,t)[1]) for k,pat in
    [('setup_ns',r'SWNS:\s*([-\d.]+)ns'),('hold_ns',r'HWNS:\s*([-\d.]+)ns')]}
   if stage!='gate':assert set(re.findall(r'sdc uncertainty\s*:?\s*([-\d.]+)',t)) <= {'0.000'}
  assert (B/'gate.db').read_bytes()==gate_before,'Gate checkpoint changed'
  result.update(passed=True,threads=16,stages=stages,
    timing_pass=stages['route']['setup_ns']>1 and stages['route']['hold_ns']>=0,
    original_constraints_byte_equal=True,source_byte_checks_passed=True)
 except Exception:
  result['failure']=traceback.format_exc();raise
 finally:
  result['completed_at']=stamp();write(summary,result);write(OUT/'td_result.json',result)
  workflow={'passed':result['passed'] and result['timing_pass'], 'flow_completed':result['passed'],
    'timing_pass':result['timing_pass'],'signoff_pass':False,'td':result,'real':json.loads((HERE/'launch_r1/real_result.json').read_text()),
    'completed_at':stamp(),'hashes_computed':False}
  write(OUT/'workflow_result.json',workflow)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--attempt',default='r1')
 parser.add_argument('--launch-dir',default='launch_r2');parser.add_argument('--task-name')
 args=parser.parse_args()
 assert re.fullmatch('r[0-9]+',args.attempt) and re.fullmatch('launch_r[0-9]+',args.launch_dir)
 assert args.task_name is None or re.fullmatch('[A-Za-z0-9_-]+',args.task_name)
 ATTEMPT=args.attempt;OUT=HERE/args.launch_dir;TASK_NAME=args.task_name
 with (OUT/'driver.log').open('w') as stream,contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
  try:main()
  finally:
   if TASK_NAME:
    # Remove only this on-demand definition after its TD child has exited.
    command="$s=New-Object -ComObject Schedule.Service; $s.Connect(); $s.GetFolder('\\').DeleteTask('"+TASK_NAME+"',0)"
    cleanup=subprocess.run(['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
      '-NoProfile','-NonInteractive','-WindowStyle','Hidden','-Command',command],
      stdout=stream,stderr=subprocess.STDOUT,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    write(OUT/'task_cleanup.json',{'task_name':TASK_NAME,'deleted':cleanup.returncode==0})
