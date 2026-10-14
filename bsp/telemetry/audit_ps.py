"""Compare actual vendor configuration against the accepted scope board."""
import hashlib,json,re,xml.etree.ElementTree as ET
from pathlib import Path
R=Path(__file__).resolve().parents[2];old=R/'bsp/work/scope_soc_prj';new=R/'bsp/work/telemetry_soc_prj'
def values(p):
 root=ET.fromstring(p.read_text(encoding='utf-8'));out={}
 for e in root.iter():
  if e.tag.endswith('configurableElementValue'):
   out[e.get('referenceId')]=(e.text or '').strip()
 return out
rel='system/ip/system_ARM_Processor_System_0/Design.xml'
a,b=values(old/rel),values(new/rel);assert a and not (a.keys()-b.keys())
added={k:b[k] for k in b.keys()-a.keys()};assert added=={'Slave_AXI_HP1_DATA_WIDTH':'64'},added
changed={k:{'old':a[k],'new':b[k]} for k in a if a[k]!=b[k]}
assert set(changed).issubset({'Slave_AXI_HP1_Interface','Slave_AXI_HP1_DATA_WIDTH'}),changed
assert b['Slave_AXI_HP0_Interface']=='1' and b['Slave_AXI_HP1_Interface']=='1'
assert b['DDRC_IO_VOL']=='1.35'
source='system/ip/system_ARM_Processor_System_0/system_ARM_Processor_System_0.tcl'
assert (old/source).read_bytes()==(new/source).read_bytes(),'PS property values changed'
proof={'status':'PASS_ACTUAL_PS_CONFIG_ONLY','changed':changed,'added_hp1_parameter':added,'unchanged_parameter_count':len(a)-len(changed),'ddr_storage_other_ps_properties_unchanged':True,'common_reset':'p2f_rst0_n; not a telemetry recovery reset','hpf_fsbl_hp0_hp1_soft_reset_release':'NOT_EXECUTED; matching release blocked by hardware diagnostic','new_xml_sha256':hashlib.sha256((new/rel).read_bytes()).hexdigest()}
E=R/'bsp/evidence/telemetry-ps-20261014';E.mkdir(exist_ok=True)
(E/'audit.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
for name in ['ps-gp-regenerate.log','actual-ps-ipgen.log','generate_ps.tcl','connections.json']:
 (E/name).write_bytes((new/name).read_bytes())
(E/'Design.xml').write_bytes((new/rel).read_bytes())
print(json.dumps(proof,indent=2))
