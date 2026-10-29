"""Current product / actual TD / real compiled copies, explicit generated EOL policy.

Preserve the old strict verifier unchanged. Only the four generated SAF2 wrappers
and five explicitly changed RS485 files may differ by Windows CRLF versus their
canonical LF; record every normalization. No RTL tokens, IP bytes, constraints or
headers are relaxed. Candidate/compiled copies retain the actual tested bytes.
"""
import argparse,importlib.util,json,re
from pathlib import Path
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
GENERATED={f'interlock_{n}.v' for n in ['motion_dma_lite_top','rs485_shared_lite_top','rs485_gp_full_top','rs485_gp_ps_top']}
RS485={'rs485_gp_bridge.v','rs485_gp_regs.v','rs485_latest_cache.v','rs485_multirate.v','rs485_telemetry.v'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--build',required=True);p.add_argument('--real',required=True);p.add_argument('--tag',required=True);a=p.parse_args()
 assert all(re.fullmatch('[A-Za-z0-9_-]+',x) for x in [a.build,a.real,a.tag])
 b=R/'pl_safety/build'/a.build;real=R/'pl_safety/build'/a.real;out=E/a.tag;out.mkdir(exist_ok=False)
 result={'passed':False,'hashes_computed':False,'byte_equal':[],'generated_crlf_to_lf_only':[]}
 def compare(source,copy):
  x,y=source.read_bytes(),copy.read_bytes()
  if x==y:result['byte_equal'].append([str(source.relative_to(R)),str(copy.relative_to(R))]);return
  assert (source.parent==R/'pl_safety/generated' and source.name in GENERATED) or (source.parent==R/'pl_rs485/rtl' and source.name in RS485),source
  assert b'\r' not in x and y.replace(b'\r\n',b'\n')==x,(source,copy)
  result['generated_crlf_to_lf_only'].append([str(source.relative_to(R)),str(copy.relative_to(R))])
 try:
  spec=importlib.util.spec_from_file_location('current_generator',R/'pl_safety/generate_top.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
  for name,text in g.render().items():assert (R/'pl_safety/generated'/name).read_bytes()==text.encode(),name
  for folder in ['pl_motion/rtl','pl_rs485/rtl','pl_safety/rtl','pl_safety/generated']:
   for source in (R/folder).glob('*.v*'):compare(source,b/'gp'/source.name)
  for folder in ['pl_rs485/generated','pl_interface/generated']:
   for source in (R/folder).glob('*.vh'):compare(source,b/'gp'/source.name)
  inventory=json.loads((real/'compiled_sources.json').read_text())
  for entry in inventory['direct_byte_verified_source_copies']:
   source,staged=Path(entry['source']),Path(entry['compiled_copy'])
   assert source.resolve().is_relative_to(R) and staged.resolve().is_relative_to(real)
   assert source.read_bytes()==staged.read_bytes(),source
   if staged.is_relative_to(real/'source'):canonical=R/staged.relative_to(real/'source')
   else:canonical=source
   compare(canonical,staged)
  for name in ['gp/gp.sdc','gp/gp.adc','gp/ps-generated-properties.tcl','gp/axi_dma.v','gp/axi_protocol_converter_merge.v','gp/axi_dma_func_pkg.vh','gp/axi_dma_param_pkg.vh','system/hdl/system_wrapper.v']:
   assert (b/name).read_bytes()==(R/'pl_safety/build/reset_path21'/name).read_bytes(),name
  for name in ['axi_dma.v','axi_protocol_converter_merge.v','axi_dma_func_pkg.vh','axi_dma_param_pkg.vh']:
   assert (b/'gp'/name).read_bytes()==(real/'ip'/name).read_bytes(),name
  assert json.loads((R/'pl_safety/evidence'/a.real/'result.json').read_text())['passed']
  result.update(passed=True,build=a.build,real=a.real,canonical_generator_checked=True,
   old_strict_verifier_unchanged=True,eol_policy='Only four named generated SAF2 wrappers and five explicitly changed RS485 files; CRLF-to-LF only, zero token changes')
  print('PASS current/TD/real source identities; explicit generated EOL normalizations',len(result['generated_crlf_to_lf_only']))
 finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
