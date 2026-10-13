"""Fail-closed final BSP motion hardware audit; never edit frozen PL evidence."""
from pathlib import Path
import json,re,hashlib,zipfile,subprocess,sys
B=Path(__file__).resolve().parents[1];R=B.parent;W=B/'work/scope_soc_prj'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
subprocess.run([sys.executable,str(R/'bsp/scope/verify_input.py')],cwd=R,check=True)
release=json.loads((R/'pl_motion/GPIO_RELEASE.json').read_text())
log=(W/'build_gp.log').read_text()
if (W/'resume_route.log').exists():log+='\n'+(W/'resume_route.log').read_text()
assert 'BSP_SCOPE_BOARD_BITSTREAM_COMPLETE' in log
assert not re.search(r'\bERROR:|CRITICAL-WARNING',log)
stages={}
for stage in ['gate','place','route']:
 t=(W/('gp_'+stage+'.timing')).read_text()
 stages[stage]={'setup_wns_ns':float(re.search(r'SWNS:\s*([-\d.]+)ns',t)[1]),'hold_wns_ns':float(re.search(r'HWNS:\s*([-\d.]+)ns',t)[1])}
 if stage=='route':
  assert min(stages[stage].values())>=0
  assert 'Both (Slow and Fast)' in t and '99.99%' in t
  for n in ['board_100m','ps/DR1_PHY_PROCESSOR_SYSTEM_Inst.GEN_PL_GP0S','ps/DR1_PHY_PROCESSOR_SYSTEM_Inst.GEN_PL_HP0']:
   assert re.search(r'100\.000\s+[1-9]\d*\s+'+re.escape(n)+r'\s',t),n
check=(W/'gp_route.check').read_text()
for n in ['checking no clock','checking no input delay','checking no output delay','checking combinational loops','checking invalid constraint']:
 hits=re.findall(re.escape(n)+r'\((\d+)\)',check)
 if hits:assert all(int(x)==0 for x in hits),n
props=W/'gp/ps-generated-properties.tcl'
expected=Path(R/'bsp/work/gp_soc_prj/system/ip/system_ARM_Processor_System_0/system_ARM_Processor_System_0.tcl').read_text().replace('ARM_Processor_System_f6ddd1d59490_Inst/DR1_PHY_PROCESSOR_SYSTEM_Inst','ps/DR1_PHY_PROCESSOR_SYSTEM_Inst')
assert props.read_text()==expected,'PS property values changed'
assert (W/'gp/gp.adc').read_text().count('set_pin_assignment')==10
assert 'H16' in (W/'gp/gp.adc').read_text()
assert 'motion_gp_ps_top #' in (W/'system/hdl/system_wrapper.v').read_text()
assert 'dma_gp_ps_top control' not in (W/'system/hdl/system_wrapper.v').read_text()
with zipfile.ZipFile(W/'system.hpf') as z:
 assert z.read('HPFs/system.bit')==(W/'system.bit').read_bytes()
 header=z.read('HPFs/soc_plat.h').decode()
 assert re.search(r'DDRC_IO_VOL\s+1.35',header)
 with zipfile.ZipFile(B/'work/dma_soc_prj/system.hpf') as old:
  prior=old.read('HPFs/soc_plat.h').decode()
 def values(t):return dict(re.findall(r'^#define\s+(\w+)\s+(.+)$',t,re.M))
 oldv,newv=values(prior),values(header)
 kept={k:v for k,v in oldv.items() if any(k.startswith(p) for p in ['DDRC_','MMC0_','MMC1_','QSPI_','CPU_','UART_'])}
 assert all(newv.get(k)==v for k,v in kept.items()),'DDR/storage/boot clocks differ'
area=(W/'gp_route.area').read_text()
result={'status':'REVIEWED_FOR_ISOLATED_MOTION_BUILD','source_commit':release['source_commit'],'handoff_commit':'1ae5ce1218e06ab8d2a9674d6fa760a1d98529a9','schema_sha256':sha(R/'pl_interface/schema.json'),'hpf_sha256':sha(W/'system.hpf'),'bitstream_sha256':sha(W/'system.bit'),'kernel_config_sha256':'81f7b75cb8e2f0901ef3dbd6eb78282db988031904dd1001ed709beb1120dbf1','stages':stages,'reference_speed':2,'routed_clock_mhz':100,'resources':{k:int(re.search(r'^#'+k+r'\s+(\d+)',area,re.M)[1]) for k in ['lut6','reg','slice','eram','dsp','gclk','sclk']},'ps_property_values_unchanged':True,'retained_ddr_storage_macros':kept,'motor_outputs':'confirmed J12 nine GPIOs plus H16 input; scope only','test_parameters':'500-cycle guards 100kHz A0..A2, M4 disabled raw64/prepared8 START32; not driver/product freeze','reset':'startup p2f_rst0_n; same-domain synchronized release; DMA-only recovery does not reset epoch/position; final FSBL GP/HP soft reset release audited separately','diagnostics_sha256':sha(W/'gp_route.check'),'remaining_high_classes':'vendor ERAM reset / executor unused physical ofb; preserved for explicit review','board_verified':False}
E=B/'evidence/scope-hardware-20261013';E.mkdir(exist_ok=True)
for name in ['build_gp.log','resume_route.log','resume_route.tcl','gp_gate.timing','gp_place.timing','gp_route.timing','gp_route.check','gp_route.area','connections.json','ps-gp-regenerate.log','actual-ps-ipgen.log','hpf-final.log']:
 if (W/name).is_file():(E/name).write_bytes((W/name).read_bytes())
(E/'index.json').write_text(json.dumps({p.name:sha(p) for p in sorted(E.iterdir()) if p.name!='index.json'},indent=2)+'\n')
result['gpio_pins']=json.loads((R/'pl_motion/scope_test/CONFIG.json').read_text())['pins']
for p in result['gpio_pins']:
 assert re.search(r'^\s*'+p['port']+r'\s+OUTPUT\s+'+p['ball']+r'\s+LVCMOS33\s+HRIO\s+8\s+NONE\s+OREG',area,re.M),p
assert '-datapath_only 20' in (W/'gp/gp.sdc').read_text()
result['remaining_high_classes']='vendor ERAM reset / planner unused mapped OFB; DRC SLATR-1036/1038 notes retained'
(B/'scope/integration.review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['status','stages','resources','hpf_sha256','bitstream_sha256']},indent=2))
