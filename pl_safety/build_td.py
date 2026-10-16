"""Clone sealed actual project into a new safety candidate; resource/STA only."""
import argparse,hashlib,json,re,shutil,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'pl_safety'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);ap.add_argument('--prepare-only',action='store_true');ap.add_argument('--resume',action='store_true');a=ap.parse_args()
 assert re.fullmatch(r'[A-Za-z0-9_-]+',a.tag)
 b=D/'build'/a.tag;baseline=R/'bsp/work/telemetry_opt_r2main'
 if not a.resume:
  b.mkdir(parents=True,exist_ok=False)
  identity=json.loads((R/'pl_rs485/optimization/round2/ROUND2_RELEASE.json').read_text())
  hashes=identity['project_inputs_sha256']
  # Authenticate the complete frozen project before copying or modifying it.
  for n,h in hashes.items():assert sha(baseline/n)==h,n
  for n in hashes:
   p=b/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(baseline/n,p)
  for folder in ['pl_motion/rtl','pl_safety/rtl','pl_safety/generated']:
   for p in (R/folder).glob('*.v*'):shutil.copyfile(p,b/'gp'/p.name)
  (b/'gp/generated').mkdir(exist_ok=True)
  for p in (R/'pl_interface/generated').glob('*'):
   if p.suffix=='.vh':
    shutil.copyfile(p,b/'gp/generated'/p.name);shutil.copyfile(p,b/'gp'/p.name)
  project=(b/'system.al').read_text(encoding='utf-8')
  project=re.sub(r'(<Project [^>]*Path=")[^"]*',lambda m:m[1]+b.as_posix(),project,count=1)
  additions=''
  for p in sorted((D/'rtl').glob('*.v'))+sorted((D/'generated').glob('*.v')):
   name='gp/'+p.name
   if 'Path="'+name+'"' not in project:
    additions+='<File Path="'+name+'"><FileInfo><Attr Name="UsedInSyn" Val="true" /><Attr Name="UsedInP&amp;R" Val="true" /><Attr Name="BelongTo" Val="design_1" /><Attr Name="CompileOrder" Val="3" /></FileInfo></File>'
  project=project.replace('</Verilog>',additions+'</Verilog>').replace('P&amp;R','P&R')
  (b/'system.al').write_text(project,encoding='utf-8')
  p=b/'system/hdl/system_wrapper.v';s=p.read_text();s=s.replace('input wire clk_100m,rs485_rx,','input wire clk_100m,rs485_rx,input wire [2:0] safety_limit_n,input wire safety_estop_n,').replace('rs485_gp_ps_top #(','safety_rs485_gp_ps_top #(.CONFIG_PROFILE(2),').replace(' control(',' control(.safety_limit_n(safety_limit_n),.safety_estop_n(safety_estop_n),');p.write_text(s)
  # Unassigned new pads are engineering-only. No fabricated physical mapping.
  with (b/'gp/gp.sdc').open('a') as f:
   f.write('\n# Four new asynchronous safety inputs: only pad -> first synchronizer stage is excepted.\n')
   # These four pads feed only the first meta DFFs. A startpoint-only
   # exception survives packing; the next meta->sync paths start at DFFs
   # and remain timed. Do not select nonexistent post-pack logical .d pins.
   f.write('set_false_path -from [get_ports {safety_limit_n[*] safety_estop_n}]\n')
  inputs={str(p.relative_to(b)):sha(p) for p in b.rglob('*') if p.is_file()}
  (b/'inputs.json').write_text(json.dumps({'baseline_project_sha256':hashes,'candidate_inputs_sha256':inputs,'profile':'RESOURCE_FIXTURE_ONLY','reference_speed':2,'no_bitgen':True,'new_input_pins':'UNASSIGNED_UNQUALIFIED'},indent=2)+'\n')
 else:
  m=json.loads((b/'inputs.json').read_text())
  for n,h in m['candidate_inputs_sha256'].items():assert sha(b/n)==h,n
 if a.prepare_only:print('PASS authenticated independent full project prepared',b);return
 script=f'''cd {b.as_posix()}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
open_project system.al
elaborate -top system_wrapper
read_adc -file gp/gp.adc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl
optimize_rtl
optimize_gate -maparea gate.area
report_timing_summary -file gate.timing -path_num 10
export_db gate.db
legalize_phy_inst
place
update_timing -mode manhattan
report_timing_summary -file place.timing -path_num 10
export_db place.db
route
update_timing -mode final
report_timing_summary -file route.timing -path_num 10
report_area -io_info -file route.area
check_timing -verbose -file route.check
report_route_status -drc -file route.drc
export_db route.db
puts SAFETY_RESOURCE_BUILD_COMPLETE
exit
'''
 if a.resume:
  assert (b/'gate.db').is_file()
  script=f'cd {b.as_posix()}\nimport_device dr1_90.db -package DR1M90GEG400 -speed 2\nimport_db gate.db\nread_adc -file gp/gp.adc\nread_sdc gp/gp.sdc\nread_sdc gp/ps-generated-properties.tcl\n'+script.split('export_db gate.db\n')[1]
 name='resume' if a.resume else 'run';assert not (b/(name+'.log')).exists()
 (b/(name+'.tcl')).write_text(script)
 td=shutil.which('td_commands_prompt');assert td
 with (b/(name+'.log')).open('w',encoding='utf-8') as f:
  result=subprocess.run([td,(b/(name+'.tcl')).as_posix()],cwd=b,stdout=f,stderr=subprocess.STDOUT,timeout=7200)
 log=(b/(name+'.log')).read_text(encoding='utf-8',errors='replace')
 if result.returncode or 'SAFETY_RESOURCE_BUILD_COMPLETE' not in log or re.search(r'\bERROR:',log):raise RuntimeError('TD failed; logs/checkpoints retained: '+str(b))
 stages={}
 for n in ['gate','place','route']:
  t=(b/(n+'.timing')).read_text();stages[n]={k:float(re.search(v,t)[1]) for k,v in [('setup_ns',r'SWNS:\s*([-\d.]+)ns'),('hold_ns',r'HWNS:\s*([-\d.]+)ns')]}
 (b/'summary.json').write_text(json.dumps({'stages':stages,'critical_warnings':[x for x in log.splitlines() if 'CRITICAL-WARNING' in x],'signoff_pass':False,'board_validated':False,'bitgen':False},indent=2)+'\n')
 print(json.dumps(stages))
if __name__=='__main__':main()
