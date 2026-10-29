"""Review final routed design and export its bit/HPF, never download to hardware."""
from pathlib import Path
import argparse,json,re,subprocess,zipfile
H=Path(__file__).resolve().parent;R=H.parents[1]
TD=Path('D:/Anlogic/TD_Release_2026.1_SP2.200.067/bin')
parser=argparse.ArgumentParser();parser.add_argument('--candidate',default='route');parser.add_argument('--hardware-directory',default='hardware');args=parser.parse_args()
assert re.fullmatch('[a-z0-9]+',args.candidate)
assert re.fullmatch('[a-zA-Z0-9_]+',args.hardware_directory)
P=H/args.hardware_directory
log=(P/'run.log').read_text(errors='replace')
assert 'INTERLOCK_FULL_TOP_COMPLETE' in log,'Full P&R is not complete'
t=(P/(args.candidate+'.timing')).read_text();check=(P/(args.candidate+'.check')).read_text()
setup=float(re.search(r'SWNS:\s*([-\d.]+)ns',t)[1]);hold=float(re.search(r'HWNS:\s*([-\d.]+)ns',t)[1])
# Latest user override 2026-10-29: after this route refinement, setup >0ns, hold >=0.
# Original nominal 100MHz constraints and all safety logic remain unchanged.
assert setup>0 and hold>=0, ('Require this-round positive setup and nonnegative hold',setup,hold)
for name in ['invalid constraint','combinational loops','no clock']:
 assert re.search(r'checking '+name+r'\(0\)',check),name
assert log.count('INTERLOCK_TD_THREADS 16')>=5
assert not (P/'system.bit').exists(),'Never overwrite a prior bitstream'
script='''cd @PATH@
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db @DB@.db
set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
puts "HOME_TD_THREADS [get_param flow thread]"
get_num_thread
bitgen -bit system.bit
puts FULL_FUNCTION_BIT_COMPLETE
exit
'''.replace('@PATH@',P.as_posix()).replace('@DB@',args.candidate)
(H/'bitgen.tcl').write_text(script)
with (P/'bitgen.log').open('w') as out:subprocess.run([str(TD/'td_commands_prompt.exe'),(H/'bitgen.tcl').as_posix()],cwd=P,stdout=out,stderr=subprocess.STDOUT,check=True)
assert 'FULL_FUNCTION_BIT_COMPLETE' in (P/'bitgen.log').read_text(errors='replace')
(H/'export_hpf.tcl').write_text('si_select_dialog HpfToolDialog\nsi_set_checkbox HpfToolDialog HpfToolDialog.IncludeBitstream checked\nsi_click_push_button HpfToolDialog HpfToolDialog.OK\nexit\n')
with (P/'hpf-export.log').open('w') as out:
 subprocess.run([str(TD/'hpfTool.exe'),'-batch','-prj_path',P.as_posix(),'-prj_name','system',
  '-ps_path',(P/'system/ip/system_ARM_Processor_System_0').as_posix(),'-design_path',(P/'system').as_posix(),
  '-bitstream_path',(P/'system.bit').as_posix(),'-bitstream_status','latest','-ip_catalog',(TD.parent/'ip/depot').as_posix(),'-tcl',(H/'export_hpf.tcl').as_posix()],cwd=P,stdout=out,stderr=subprocess.STDOUT,check=True)
with zipfile.ZipFile(P/'system.hpf') as z:
 assert z.read('HPFs/system.bit')==(P/'system.bit').read_bytes()
 def params(text):return dict(re.findall(r'<ipxact:configurableElementValue referenceId="([^"]+)">([^<]*)</ipxact:configurableElementValue>',text))
 actual=params((P/'system/Design.xml').read_text());exported=params(z.read('HPFs/Design.xml').decode());assert len(actual)>500 and actual==exported
area=(P/(args.candidate+'.area')).read_text();metrics={}
for n in ['lut6','slice','slice reg','eram','dsp','pad']:
 m=re.search(r'#'+n+r'\s+(\d+)\s+out of\s+(\d+)\s+([\d.]+)%',area)
 if m:metrics[n]=dict(used=int(m[1]),total=int(m[2]),percent=float(m[3]))
(H/'hardware-result.json').write_text(json.dumps(dict(hardware_directory=args.hardware_directory,selected_database=args.candidate,setup_ns=setup,hold_ns=hold,minimum_setup_ns=0,minimum_setup_exclusive=True,setup_positive=setup>0,setup_gt_1ns=setup>1,setup_ge_0_2ns=setup>=0.2,threads=16,
 config_profile=0,home_only=False,clock_mhz=100,metrics=metrics,matched_hpf_ps_parameters=len(actual),bit_matches_hpf=True,
 cdc_independent_gate=False,board_tested=False,signoff_pass=False,unresolved=['protected-IP SYN-5066','external IO/electrical qualification','physical speed/DDR','actual RS485 and HOME acceptance']),indent=2)+'\n')
print('PASS full P&R positive setup/nonnegative hold, constraints, resources, same-project bit/HPF')
