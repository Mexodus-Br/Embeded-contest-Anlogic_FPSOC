"""Split configuration admission from HOME's executing permit, exactly."""
import importlib.util,json,shutil
from pathlib import Path
from rtl24_prepare import replace
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 out=E/'rtl26_candidate_r1';out.mkdir(exist_ok=False)
 for f in (E/'rtl25_candidate_r1').glob('*.v'):shutil.copyfile(f,out/f.name)
 s=(out/'rs485_gp_regs.v').read_text()
 s=replace(s,'output wire interlock_run,interlock_reset,interlock_config_pending,','output wire interlock_run,interlock_reset,interlock_config_pending,interlock_config_stored_pending,')
 s=replace(s,'assign interlock_config_pending=config_pending || cfg_valid || !cfg_ready || reset_count!=0 || cfg_applied || config_admission;',
  'assign interlock_config_stored_pending=config_pending || cfg_valid || !cfg_ready || reset_count!=0 || cfg_applied;\n assign interlock_config_pending=interlock_config_stored_pending || config_admission;')
 (out/'rs485_gp_regs.v').write_text(s)
 s=(R/'pl_rs485/rtl/rs485_gp_bridge.v').read_text()
 s=replace(s,'output wire interlock_run,interlock_reset,interlock_config_pending,','output wire interlock_run,interlock_reset,interlock_config_pending,interlock_config_stored_pending,')
 s=replace(s,'.interlock_config_pending(interlock_config_pending),','.interlock_config_pending(interlock_config_pending),.interlock_config_stored_pending(interlock_config_stored_pending),')
 (out/'rs485_gp_bridge.v').write_text(s)
 s=(R/'pl_safety/rtl/safety_controller.v').read_text()
 s=replace(s,'parameter CONFIG_APPROVED=0,INTERLOCK_SUPPORT=0,','parameter CONFIG_APPROVED=0,INTERLOCK_SUPPORT=0,SPLIT_RUN_PERMIT=0,')
 s=replace(s,'input wire interlock_permit,interlock_detect,','input wire interlock_run_permit,interlock_permit,interlock_detect,')
 s=replace(s,'(INTERLOCK_SUPPORT && (!interlock_permit || interlock_detect)))home_run=0;',
  '(INTERLOCK_SUPPORT && (!(SPLIT_RUN_PERMIT ? interlock_run_permit:interlock_permit) || interlock_detect)))home_run=0;')
 (out/'safety_controller.v').write_text(s)
 s=(R/'pl_safety/rtl/safety_motion_service.v').read_text()
 s=replace(s,'collector_reset,collector_config_pending,','collector_reset,collector_config_pending,collector_config_stored_pending,')
 s=replace(s,'wire il_permit,il_detect,','wire il_run_permit,il_permit,il_detect,')
 s=replace(s,'.INTERLOCK_SUPPORT(INTERLOCK_SUPPORT),.HOME_DIRECTION',
  '.INTERLOCK_SUPPORT(INTERLOCK_SUPPORT),.SPLIT_RUN_PERMIT(INTERLOCK_SUPPORT),.HOME_DIRECTION')
 s=replace(s,'.interlock_permit(il_permit),','.interlock_run_permit(il_run_permit),.interlock_permit(il_permit),')
 s=replace(s,'assign il_permit=raw_permit && !collector_config_pending && !cfg_pending;',
 '''assign il_permit=raw_permit && !collector_config_pending && !cfg_pending;
 // config_admission implies interlock_idle, which includes !owner. During
 // every PRE/SEARCH/PULL executing cycle owner is true, so the admission
 // cofactor is exactly zero. Retain ALL stored/configuration/reset fences.
 // HOME acceptance and ordinary commands still use the full current permit.
 assign il_run_permit=raw_permit && !collector_config_stored_pending && !cfg_pending;
 // synthesis translate_off
 always @(posedge clk)if(rst_n && owner)begin
  if(interlock_idle)$fatal(1,"HOME owner cannot hold idle admission");
  if(collector_config_pending !== collector_config_stored_pending)
   $fatal(1,"configuration admission reached an executing HOME owner");
  if(il_run_permit !== il_permit)$fatal(1,"HOME permit cofactor mismatch");
 end
 // synthesis translate_on''')
 s=replace(s,'assign il_permit=1;assign il_clear_ok=1;', 'assign il_run_permit=1;assign il_permit=1;assign il_clear_ok=1;')
 (out/'safety_motion_service.v').write_text(s)
 # Generator is the source of truth; emit isolated copies for synthesis.
 s=(R/'pl_safety/generate_top.py').read_text()
 s=s.replace('collector_reset,collector_config_pending,','collector_reset,collector_config_pending,collector_config_stored_pending,')
 s=s.replace('.collector_config_pending(collector_config_pending),','.collector_config_pending(collector_config_pending),.collector_config_stored_pending(collector_config_stored_pending),')
 s=s.replace('.interlock_config_pending(collector_config_pending),','.interlock_config_pending(collector_config_pending),.interlock_config_stored_pending(collector_config_stored_pending),')
 (out/'generate_top.py').write_text(s)
 namespace={'__file__':str(R/'pl_safety/generate_top.py'),'__name__':'isolated_generator'}
 exec(compile(s,str(R/'pl_safety/generate_top.py'),'exec'),namespace)
 for name,text in namespace['render']().items():
  if name.startswith('interlock_'):(out/name).write_text(text)
 (out/'notes.json').write_text(json.dumps({'hashes_computed':False,'internal_cycles_added':0,
  'proof':'admission implies idle; idle implies !owner; PRE/SEARCH/PULL imply owner; thus HOME-run admission cofactor=0',
  'retained':'all stored pending/reset/apply fences, raw permit/detect, full admission permit for HOME start and ordinary commands',
  'status':'isolated module validation pending'},indent=2)+'\n')
 print('Prepared RTL26 exact HOME-running configuration cofactor')
if __name__=='__main__':main()
