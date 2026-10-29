"""Gate/full actual top for a module-validated RTL candidate; no source hashes."""
import argparse,importlib.util,json,re,shutil,subprocess,sys,traceback
from datetime import datetime,timezone
from pathlib import Path
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
ALLOWED={'motion_service.v','motion_stream_rx.v','continuous_motion.v','motion_fifo.v','motion_planner.v','motion_executor.v','rs485_gp_regs.v','rs485_multirate.v',
 'rs485_latest_cache.v','rs485_telemetry.v','rs485_gp_bridge.v','rs485_transaction.v','safety_interlock.v','safety_controller.v','safety_motion_service.v',
 'interlock_motion_dma_lite_top.v','interlock_rs485_shared_lite_top.v','interlock_rs485_gp_full_top.v','interlock_rs485_gp_ps_top.v'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);p.add_argument('--gate-only',action='store_true');p.add_argument('--resume-route',action='store_true');p.add_argument('--prepare-only',action='store_true');p.add_argument('--run-prepared',action='store_true');p.add_argument('--post-route-high',action='store_true');a=p.parse_args()
 assert sum([a.resume_route,a.prepare_only,a.run_prepared])<=1
 assert re.fullmatch('[A-Za-z0-9_-]+',a.tag)
 source=Path(a.candidate).resolve();assert source.is_relative_to(E)
 required={
  'rtl27_candidate_r1':['rtl24_service_r1','rtl24_suite_r1','rtl25_control_r1','rtl26_suite_r1','rtl27_cache3_r1','rtl27_cache1_r1'],
  'rtl28_candidate_r1':['rtl28_service_r1','rtl28_suite_r1','rtl28_control_r1','rtl28_stats_r1','rtl28_cache3_r1','rtl28_cache1_r1','rtl27_rx_reset_r2'],
  'rtl29_candidate_r1':['rtl28_service_r1','rtl28_suite_r1','rtl28_control_r1','rtl28_stats_r1','rtl28_cache3_r1','rtl28_cache1_r1','rtl27_rx_reset_r2','rtl29_transport_r4'],
  'rtl31_candidate_r1':['rtl31_service_r1','rtl31_suite_r1','rtl31_fifo_r1','rtl31_wide_r1','rtl28_control_r1','rtl28_stats_r1','rtl28_cache3_r1','rtl28_cache1_r1','rtl29_transport_r4'],
  'rtl32_candidate_r2':['rtl32_service_r2','rtl32_suite_r2','rtl31_fifo_r1','rtl31_wide_r1','rtl28_control_r1','rtl28_stats_r1','rtl28_cache3_r1','rtl28_cache1_r1','rtl29_transport_r4'],
  'rtl33_candidate_r1':['rtl33_service_r1','rtl33_suite_r1','rtl30_fifo_r1','rtl30_wide_r1','rtl28_control_r1','rtl28_stats_r1','rtl28_cache3_r1','rtl28_cache1_r1','rtl29_transport_r4'],
  'rtl36_candidate_r1':['rtl34_service_r1','rtl36_suite_r1','rtl36_emit_r1','rtl35_monitor_r2','rtl30_fifo_r1','rtl30_wide_r1','rtl28_control_r1','rtl28_stats_r1','rtl28_cache3_r1','rtl28_cache1_r1','rtl29_transport_r4'],
  'rtl37_candidate_r4':['rtl37_service_r2','rtl37_suite_r3','rtl37_time_r2','rtl37_gp_r2','rtl37_transport_r1','rtl37_arithmetic_r1','rtl30_fifo_r1','rtl30_wide_r1'],
  'rtl37_candidate_r5':['rtl37_service_r2','rtl37_suite_r3','rtl37_time_r2','rtl37_gp_r2','rtl37_transport_r1','rtl37_arithmetic_r1','rtl30_fifo_r1','rtl30_wide_r1']}
 assert source.name in required
 for test in required[source.name]:
  assert json.loads((E/test/'result.json').read_text())['passed'],test
 if source.name=='rtl37_candidate_r5':
  assert json.loads((source/'declaration_compatibility.json').read_text())['passed']
  for f in (E/'rtl37_candidate_r4').glob('*.v'):
   expected=f.read_bytes()
   if f.name=='continuous_motion.v':
    expected=expected.replace(b'wire prepared_valid,prepared_push_ready,prepared_pop;',b'wire prepared_valid,prepared_push_ready,prepared_pop,prepared_storage_ready;').replace(b'wire prepared_storage_ready=!own',b'assign prepared_storage_ready=!own')
   assert (source/f.name).read_bytes()==expected,f.name
 if source.name=='rtl28_candidate_r1':
  assert (source/'motion_stream_rx.v').read_bytes()==(E/'rtl27_candidate_r1/motion_stream_rx.v').read_bytes()
 if source.name=='rtl29_candidate_r1':
  for f in (E/'rtl28_candidate_r1').glob('*.v'):
   assert f.read_bytes()==(source/f.name).read_bytes(),f.name
  assert {f.name for f in source.glob('*.v')}=={f.name for f in (E/'rtl28_candidate_r1').glob('*.v')}|{'rs485_telemetry.v'}
 if source.name in ['rtl31_candidate_r1','rtl32_candidate_r2','rtl33_candidate_r1']:
  for name in ['rs485_gp_regs.v','rs485_gp_bridge.v','rs485_multirate.v','rs485_latest_cache.v','rs485_telemetry.v','safety_motion_service.v','safety_controller.v']:
   assert (source/name).read_bytes()==(E/'rtl29_candidate_r1'/name).read_bytes(),name
  if source.name=='rtl32_candidate_r2':
   assert (source/'raw_clocked_notes.json').exists()
   assert (source/'motion_fifo.v').read_bytes()==(E/'rtl31_candidate_r1/motion_fifo.v').read_bytes()
  if source.name=='rtl33_candidate_r1':
   assert (source/'motion_fifo.v').read_bytes()==(E/'rtl30_candidate_r1/motion_fifo.v').read_bytes()
 if source.name=='rtl36_candidate_r1':
  assert (source/'fresh_time_notes.json').exists()
  for name in ['motion_service.v','motion_stream_rx.v','continuous_motion.v','motion_fifo.v','motion_planner.v','motion_executor.v']:
   assert (source/name).read_bytes()==(E/'rtl34_candidate_r1'/name).read_bytes(),name
  assert (source/'motion_fifo.v').read_bytes()==(E/'rtl30_candidate_r1/motion_fifo.v').read_bytes()
  for name in ['rs485_gp_regs.v','rs485_latest_cache.v','rs485_telemetry.v','safety_controller.v']:
   assert (source/name).read_bytes()==(E/'rtl29_candidate_r1'/name).read_bytes(),name
 out=R/'pl_safety/build'/a.tag
 if not a.resume_route and not a.run_prepared:
  spec=importlib.util.spec_from_file_location('actual_builder',R/'pl_safety/build_interlock.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
  sys.argv=[str(R/'pl_safety/build_interlock.py'),'--tag',a.tag,'--prepare-only'];builder.main()
  files=list(source.glob('*.v'));assert {f.name for f in files}<=ALLOWED
  for f in files:
   shutil.copyfile(f,out/'gp'/f.name);assert f.read_bytes()==(out/'gp'/f.name).read_bytes()
  inputs=json.loads((out/'inputs.json').read_text());inputs['isolated_candidate']=source.relative_to(R).as_posix();inputs['isolated_overrides']=[f.name for f in files];inputs['post_route_effort']='high' if a.post_route_high else 'existing_default'
  (out/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
  script=(out/'run.tcl').read_text()
  if a.post_route_high:
   assert script.count('export_sdc -file nominal_route.sdc')==1
   script=script.replace('export_sdc -file nominal_route.sdc','''update_timing -mode final
report_timing_summary -file route_before_physopt.timing -path_num 20
report_area -io_info -file route_before_physopt.area
export_db route_before_physopt.db
set_param flow thread 16
if {[get_param flow thread]!=16} {error "Expected sixteen threads"}
puts "INTERLOCK_TD_THREADS [get_param flow thread]"
get_num_thread
puts RTL_POST_ROUTE_HIGH_BEGIN
phys_opt -post_route -effort high
puts RTL_POST_ROUTE_HIGH_END
set_param flow thread 16
puts "INTERLOCK_TD_THREADS [get_param flow thread]"
get_num_thread
clear_user_sdc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl
export_sdc -file nominal_route.sdc''')
  # Preserve the existing complete flow for an explicit later route resume.
  (out/'full_flow.tcl').write_text(script)
  if a.gate_only:script=script.split('export_db gate.db',1)[0]+'export_db gate.db\nputs RTL_CANDIDATE_GATE_COMPLETE\nexit\n'
  (out/'run.tcl').write_text(script)
 elif a.resume_route:
  assert json.loads((out/'gate_summary.json').read_text())['flow_completed']
  assert not (out/'route_run.log').exists()
  original=(out/'full_flow.tcl').read_text();tail=original.split('export_db gate.db',1)[1]
  script=f'''cd {out.as_posix()}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
set_param flow thread 16
get_num_thread
import_db {(out/'gate.db').as_posix()}
set_param flow thread 16
if {{[get_param flow thread]!=16}} {{error "Expected sixteen threads"}}
puts "INTERLOCK_TD_THREADS [get_param flow thread]"
get_num_thread
clear_user_sdc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl
set_param place hfn_opt_effort high
set_param place max_fanout 128
set_param place opt_timing high
set_param place logic_level_opt on
'''+tail
  (out/'route_run.tcl').write_text(script)
 if a.prepare_only:
  print('PASS module-validated full top prepared:',out);return
 if a.run_prepared:
  inputs=json.loads((out/'inputs.json').read_text())
  assert inputs['isolated_candidate']==source.relative_to(R).as_posix()
  assert {f.name for f in source.glob('*.v')}==set(inputs['isolated_overrides'])
  for f in source.glob('*.v'):assert f.read_bytes()==(out/'gp'/f.name).read_bytes(),f.name
  assert (out/'run.tcl').read_bytes()==(out/'full_flow.tcl').read_bytes()
 name='route_run' if a.resume_route else 'run';result={'flow_completed':False,'signoff_pass':False,'hashes_computed':False,'candidate':str(source),'gate_only':a.gate_only}
 inputs=json.loads((out/'inputs.json').read_text());result['post_route_effort']=inputs.get('post_route_effort','existing_default')
 assert not (out/f'{name}.log').exists(),'Refuse restart/overwrite'
 for filename in ['gp/gp.sdc','gp/gp.adc','gp/ps-generated-properties.tcl']:
  assert (out/filename).read_bytes()==(R/'pl_safety/build/reset_path21'/filename).read_bytes(),filename
 try:
  with (out/f'{name}.log').open('w') as log:
   proc=subprocess.Popen([shutil.which('td_commands_prompt'),(out/f'{name}.tcl').as_posix()],cwd=out,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
   (out/'process.json').write_text(json.dumps({'td_pid':proc.pid,'td_started_at_utc':datetime.now(timezone.utc).isoformat(),'hashes_computed':False},indent=2)+'\n')
   try:proc.wait(timeout=14400)
   except subprocess.TimeoutExpired:
    proc.terminate();proc.wait(timeout=30);raise
  text=(out/f'{name}.log').read_text(errors='replace');marker='RTL_CANDIDATE_GATE_COMPLETE' if a.gate_only else 'INTERLOCK_FULL_TOP_COMPLETE'
  assert proc.returncode==0 and marker in text and not re.search(r'\bERROR:|TMR-250[79]',text)
  assert 'INTERLOCK_TD_THREADS 16' in text and 'Number of Thread = 16' in text
  if not a.gate_only and result['post_route_effort']=='high':
   assert 'RTL_POST_ROUTE_HIGH_END' in text and 'start command "phys_opt -post_route -effort high"' in text
  stages={}
  for stage in (['gate'] if a.gate_only else ['gate','place','route']):
   t=(out/f'{stage}.timing').read_text();stages[stage]={k:float(re.search(pattern,t)[1]) for k,pattern in [('setup_ns',r'SWNS:\s*([-\d.]+)ns'),('hold_ns',r'HWNS:\s*([-\d.]+)ns')]}
  area=(out/('gate.area' if a.gate_only else 'route.area')).read_text()
  fields={'lut6':r'^#unit lut\*\s+' if a.gate_only else r'^#lut6\s+','slice_ff':r'^  #slice reg\s+','eram':r'^#eram\s+','dsp':r'^#dsp\s+'}
  if not a.gate_only:fields.update(slice=r'^#slice\s+',pad_ff=r'^  #pad reg\s+',io=r'^#IO\s+')
  resources={k:int(re.search(pattern+r'(\d+)',area,re.M)[1]) for k,pattern in fields.items()}
  result.update(flow_completed=True,stages=stages,resources=resources,threads=16)
  if not a.gate_only:
   result['timing_target_met']=stages['route']['setup_ns']>1 and stages['route']['hold_ns']>=0
   for stage in ['place','route']:
    assert set(re.findall(r'sdc uncertainty\s*:?\s*([-\d.]+)',(out/f'{stage}.timing').read_text()))<={'0.000'}
  for f in source.glob('*.v'):assert f.read_bytes()==(out/'gp'/f.name).read_bytes()
  for name in ['gp/gp.sdc','gp/gp.adc','gp/ps-generated-properties.tcl']:
   assert (out/name).read_bytes()==(R/'pl_safety/build/reset_path21'/name).read_bytes()
  print(json.dumps(result,indent=2))
 except Exception:result['failure']=traceback.format_exc();raise
 finally:(out/('gate_summary.json' if a.gate_only else 'route_summary.json')).write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
