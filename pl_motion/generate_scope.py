"""Generate explicit oscilloscope-only parameters/pins and fixed MOT2 fixtures."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'pl_interface'))
from motion_v2 import encode
def render():
 c=json.loads((ROOT/'scope_test/CONFIG.json').read_text(encoding='utf-8'))
 assert c['clock_hz']==100000000 and c['enabled_axis_mask']==7
 assert len(c['pins'])==9 and len({p['ball'] for p in c['pins']})==9
 h='// Generated scope-test only; M4 zero parameters prohibit ENABLE.\n'
 h+='`define SCOPE_TIMING {64\'d0,{3{64\'d%d}}}\n'%c['timing_cycles']
 h+='`define SCOPE_RATE {64\'d0,{3{64\'d%d}}}\n'%c['max_step_hz']
 h+='`define SCOPE_EN_ACTIVE 4\'h%x\n'%c['en_active_level']
 a='# Confirmed J12 scope-only mapping; not M1-M3 mechanical mapping.\n'
 a+='set_pin_assignment { clk_100m } { LOCATION = H16; IOSTANDARD = LVCMOS33; }\n'
 for p in c['pins']:
  a+='set_pin_assignment { %s } { LOCATION = %s; IOSTANDARD = LVCMOS33; DRIVESTRENGTH = %d; SLEWRATE = %s; PACKREG = %s; }\n'%(p['port'],p['ball'],c['drive_strength_ma'],c['slew_rate'],c['output_packreg'])
 s='''# Scope-only ASYNCHRONOUS observation interface; no external clocked receiver.
# 10ns internal clocks remain unchanged. Output_delay names the reference only.
# The nine GPIO paths have an explicit datapath-only bound, not synchronous receiver setup.
create_clock -name board_100m -period 10 [get_ports clk_100m]
set_output_delay -clock board_100m -max 0 [get_ports {a0_step a0_dir a0_en a1_step a1_dir a1_en a2_step a2_dir a2_en}]
set_output_delay -clock board_100m -min 0 [get_ports {a0_step a0_dir a0_en a1_step a1_dir a1_en a2_step a2_dir a2_en}]
'''
 s+='set_max_delay -to [get_ports {a0_step a0_dir a0_en a1_step a1_dir a1_en a2_step a2_dir a2_en}] -datapath_only %s\n'%c['scope_output_datapath_max_ns']
 result={'scope_test/generated/params.vh':h.encode(),'scope_test/generated/pins.adc':a.encode(),'scope_test/generated/timing.sdc':s.encode()}
 for name,sid,target in [('outbound',1,c['endpoint_steps']),('return',2,c['origin_steps']),('stop',3,c['endpoint_steps'])]:
  v={'session_id':sid,'sequence':0,'flags':1,'axis_mask':7,'duration_tick':c['duration_tick']}
  v.update({'target'+str(i):x for i,x in enumerate(target)});b=encode(v)
  result['scope_test/generated/'+name+'.bin']=b
  result['scope_test/generated/'+name+'.hex']=(' '.join('%02x'%x for x in b)+'\n').encode()
 return result
def main():
 p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
 for name,data in render().items():
  path=ROOT/name
  if a.check:assert path.read_bytes()==data,'stale '+name
  else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
 print('PASS scope-test generated params, pins and canonical MOT2 fixtures')
if __name__=='__main__':main()
