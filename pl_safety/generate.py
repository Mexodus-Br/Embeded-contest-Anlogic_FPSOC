"""Safety definitions from the canonical schema; explicit versioned configs."""
import argparse,hashlib,json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'pl_safety'
def render(config_root=None):
 s=json.loads((R/'pl_interface/schema.json').read_text(encoding='utf-8'))
 p=s['safety_profiles']['gp_safety_home_v1']
 assert p['irq_intid']==p['irq_spi']+32 and p['irq_line']==7
 assert p['base']==0x80a00000 and p['size']==4096
 resources=[(q['base'],q['size'],q['irq_line']) for group in ['motion_integration_profiles','rs485_gp_profiles'] for q in s[group].values()]
 resources += [(s['rs485_telemetry']['base'],s['rs485_telemetry']['size'],s['rs485_telemetry']['irq_line'])]
 resources += [(s['rs485_telemetry']['dma']['base'],4096,s['rs485_telemetry']['dma']['irq_line'])]
 resources += [(q['address']['base'],q['address']['size'],q['irq']['pl_line']) for q in s['gp_control_profiles'].values()]
 resources += [(q['address']['base'],q['address']['size'],line) for q in s['dma_loopback_profiles'].values() for line in [q['irq']['mm2s_line'],q['irq']['s2mm_line']]]
 for b,n,irq in resources:assert b+n<=p['base'] or p['base']+4096<=b;assert irq!=7
 offsets=list(p['registers'].values());assert len(offsets)==len(set(offsets)) and all(x%4==0 and x<p['snapshot_base'] for x in offsets)
 const={k.upper():v for k,v in p.items() if isinstance(v,int)}
 for group in ['registers','commands','errors','states','causes','snapshot']:
  const.update({group.upper()+'_'+k:v for k,v in p[group].items()})
 v=['// Generated from pl_interface/schema.json. Do not edit.','`ifndef SAFETY_DEFS_VH','`define SAFETY_DEFS_VH']
 h=['/* Generated from pl_interface/schema.json. */','#ifndef SAFETY_DEFS_H','#define SAFETY_DEFS_H']
 for n,x in const.items():v.append(f"`define SAF_{n} 32'h{x:08x}");h.append(f'#define SAF_{n} 0x{x:08x}u')
 v.append('`endif\n');h.append('#endif\n')
 out={'safety_defs.vh':'\n'.join(v),'safety_defs.h':'\n'.join(h)}
 params=['// Generated versioned configuration. PROFILE=0 production, 1 simulation.']
 cfgs=[json.loads(((config_root or D/'config')/f'{n}.json').read_text()) for n in ['production','simulation','resource_fixture']]
 assert type(cfgs[0]['approved']) is bool and all(c['approved'] is True for c in cfgs[1:])
 if cfgs[0]['approved']:
  c=cfgs[0]
  assert c.get('approval_scope') in ['home_calibration_only','runtime_calibrated_motion'] and c.get('machine_xyz_calibrated') is False
  assert c.get('reference_convention')=='limit_contact_minus_150_pull_complete_zero_unmapped'
  assert c['REFERENCE_POSITION']==[-150]*3 and c['PULL_DISTANCE']==[150]*3
  assert c['HOME_DIRECTION']==0 and c['SEARCH_MAX_STEPS']==[500]*3
  assert c['SEARCH_MAX_US']==10000000 and c['PULL_MAX_US']==c['PRE_MAX_US']==3000000
  assert c['PRE_DISTANCE']==c['PRE_MAX_STEPS']==c['PULL_MAX_STEPS']==[150]*3
  assert c['RELEASE_CYCLES']==2000000
  assert all(c[k]==[1000000]*3 for k in ['SEARCH_PERIOD','PULL_PERIOD','PRE_PERIOD'])
  assert c['motion_timing']==dict(clock_hz=100000000,step_high_cycles=3125,step_low_cycles=3125,dir_setup_cycles=500,dir_hold_cycles=500,en_setup_cycles=500,en_disable_cycles=500,max_step_hz=16000)
 assert all(c['version']==1 for c in cfgs) and cfgs[1]['purpose'].startswith('simulation_only')
 keys=['HOME_DIRECTION','RELEASE_CYCLES','SEARCH_MAX_US','PULL_MAX_US','PRE_MAX_US','SEARCH_PERIOD','PULL_PERIOD','PRE_PERIOD','REFERENCE_POSITION','PULL_DISTANCE','PRE_DISTANCE','SEARCH_MAX_STEPS','PULL_MAX_STEPS','PRE_MAX_STEPS']
 for k in keys:
  width=192 if isinstance(cfgs[0][k],list) else 3 if k=='HOME_DIRECTION' else 64
  values=[]
  for cfg in cfgs:
   x=cfg[k]
   if isinstance(x,list):
    assert len(x)==3 and all(type(y) is int and (-(1<<63)<=y<(1<<63) if k=='REFERENCE_POSITION' else 0<=y<(1<<64)) for y in x)
    x=sum((y&((1<<64)-1))<<(64*i) for i,y in enumerate(x))
   assert type(x) is int and 0<=x<(1<<width)
   values.append(f"{width}'h{x:x}")
  params.append(f'localparam [{width-1}:0] C_{k}=CONFIG_PROFILE==2 ? {values[2]} : CONFIG_PROFILE==1 ? {values[1]} : {values[0]};')
 params.append(f"localparam C_APPROVED=CONFIG_PROFILE==0 ? 1'b{int(cfgs[0]['approved'])} : (CONFIG_PROFILE==1 || CONFIG_PROFILE==2);")
 normal=cfgs[0].get('approval_scope')=='runtime_calibrated_motion' and cfgs[0]['approved']
 params.append("localparam C_HOME_ONLY="+("1'b0" if normal else "CONFIG_PROFILE==0")+"; // explicit versioned production motion policy")
 for i,cfg in enumerate(cfgs):
  digest=hashlib.sha256(json.dumps(cfg,sort_keys=True,separators=(',',':')).encode()).hexdigest()
  params.append(f"localparam [255:0] CONFIG_HASH_{i}=256'h{digest};")
 params.append('localparam [255:0] C_CONFIG_HASH=CONFIG_PROFILE==2 ? CONFIG_HASH_2 : CONFIG_PROFILE==1 ? CONFIG_HASH_1 : CONFIG_HASH_0;')
 out['safety_parameters.vh']='\n'.join(params)+'\n'
 cfg=cfgs[0];digest=hashlib.sha256(json.dumps(cfg,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 policy=['/* Generated from production.json: exact HOME calibration identity, never XYZ qualification. */','#ifndef HOME_CALIBRATION_POLICY_H','#define HOME_CALIBRATION_POLICY_H',f'#define HC_APPROVED {int(cfg["approved"])}u']
 for i in range(8):policy.append(f'#define HC_CONFIG_WORD_{i} 0x{int(digest,16)>>(32*i)&0xffffffff:08x}u')
 policy.append('#define HC_CONFIG_WORDS { '+', '.join(f'HC_CONFIG_WORD_{i}' for i in range(8))+' }')
 policy.append(f'#define HC_NORMAL_MOTION_APPROVED {int(normal)}u')
 policy.append('#define HC_REFERENCE_STEPS (-150)\n#define HC_COMPLETED_STEPS 0\n#endif\n')
 out['home_calibration_policy.h']='\n'.join(policy)
 return out
def main():
 a=argparse.ArgumentParser();a.add_argument('--check',action='store_true');args=a.parse_args()
 for n,t in render().items():
  p=D/'generated'/n
  if args.check:assert p.read_bytes()==t.encode(),n
  else:p.write_bytes(t.encode())
 print('PASS safety schema/config generation'+(' check' if args.check else ''))
if __name__=='__main__':main()
