"""100MHz OOC component P&R; report hierarchy, do not sum scan fixtures."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
from prepare_ip import ROOT,TD,prepare,digest
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--component',choices=['parse','cache','packet','dma'],required=True);ap.add_argument('--tag',required=True);a=ap.parse_args()
 module={'parse':'rs485_light_parse','cache':'rs485_latest_cache','packet':'rs485_telemetry','dma':'telemetry_dma_lite_top'}[a.component]
 b=ROOT/'build'/('telem_'+a.component+'_'+a.tag);b.mkdir(exist_ok=False);e=ROOT/'reports'/('telem_'+a.component+'_'+a.tag)
 sources=[];hashes={};header=(ROOT.parent/'pl_interface/generated/interface_defs.vh').read_text()
 for d in ['pl_rs485','pl_dma','pl_motion']:
  for p in (ROOT.parent/d/'rtl').glob('*.v'):
   text=p.read_text().replace('`include "generated/interface_defs.vh"',header)
   text=re.sub(r'`include "([^"]+)"',lambda m:(ROOT.parent/'pl_rs485/generated'/m[1]).read_text(),text)
   dest=b/p.name;dest.write_text(text);sources.append(dest);hashes[str(p.relative_to(ROOT.parent))]=digest(p)
 target=(b/(module+'.v')).read_text().split(');',1)[0];ports={}
 for match in re.finditer(r'\b(input|output)\s+(?:wire|reg)\s*(?:\[(\d+):0\]\s*)?(.*?)(?=\binput|\boutput|$)',target,re.S):
  d,w,names=match.groups()
  for n in names.split(','):
   n=n.strip()
   if n:ports[n]=(d,int(w)+1 if w else 1)
 ins={n:w for n,(d,w) in ports.items() if d=='input' and n not in ['clk','clk_100m','rst_n','arst_n']};outs={n:w for n,(d,w) in ports.items() if d=='output'}
 iw=max(2,sum(ins.values()));ow=max(2,sum(outs.values()));text=f'module telem_probe(input clk,rst_n,scan_in,load,output scan_out);\nreg [{iw-1}:0] inp;reg [{ow-1}:0] obs;\n'
 for n,w in outs.items():text+=f'wire [{w-1}:0] o_{n};\n'
 text+=f"always @(posedge clk) begin inp<={{inp[{iw-2}:0],scan_in}};if(load) obs<={{{','.join('o_'+n for n in outs)}}};else obs<={{obs[{ow-2}:0],1'b0}};end\nassign scan_out=obs[{ow-1}];\n"
 binds=[];offset=0
 for n,(d,w) in ports.items():
  v='clk' if n in ['clk','clk_100m'] else 'rst_n' if n in ['rst_n','arst_n'] else 'o_'+n if d=='output' else f'inp[{offset}+: {w}]'
  if n in ins:offset+=w
  binds.append('.'+n+'('+v+')')
 text+=module+' dut('+','.join(binds)+');\nendmodule\n';(b/'top.v').write_text(text);(b/'clock.sdc').write_text('create_clock -name telem_clk -period 10 [get_ports clk]\n')
 files=[]
 if a.component=='dma':files=[Path(x['staged']) for x in prepare()['libraries'].values()]
 files+=sources+[b/'top.v'];script=f'cd {{{b.as_posix()}}}\nimport_device dr1_90.db -package DR1M90GEG400 -speed 2\n'
 script+=''.join(f'analyze -file {{{p.as_posix()}}}\n' for p in files)
 script+='''elaborate -top telem_probe
optimize_rtl
write_verilog rtl_netlist.v
read_sdc clock.sdc
optimize_gate -maparea gate.area
update_timing
report_timing_summary -file gate.timing -path_num 3
legalize_phy_inst
place
update_timing -mode manhattan
report_timing_summary -file place.timing -path_num 3
route
update_timing -mode final
report_timing_summary -file route.timing -path_num 3
report_area -file route.area
check_timing -verbose -file route.check
report_route_status -drc
puts TELEMETRY_COMPONENT_COMPLETE
exit
'''
 (b/'run.tcl').write_text(script)
 with (b/'run.log').open('w') as log:p=subprocess.run([str(TD/'bin/td_commands_prompt.exe'),(b/'run.tcl').as_posix()],cwd=b,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
 log=(b/'run.log').read_text();e.mkdir(exist_ok=False)
 for name in ['rtl_netlist.v','top.v','clock.sdc','run.tcl','run.log','gate.area','gate.timing','place.timing','route.timing','route.area','route.check','route.qor']:
  if (b/name).exists():shutil.copyfile(b/name,e/name)
 if p.returncode or 'TELEMETRY_COMPONENT_COMPLETE' not in log or 'ERROR:' in log:raise RuntimeError('TD failed '+str(b))
 result={'module':module,'clock_MHz':100,'source_sha256':hashes,'fixture_sha256':digest(b/'top.v'),'constraint_sha256':digest(b/'clock.sdc'),'stages':{}}
 for stage in ['gate','place','route']:
  t=(b/(stage+'.timing')).read_text();result['stages'][stage]={'setup':float(re.search(r'SWNS:\s*([-\d.]+)ns',t)[1]),'hold':float(re.search(r'HWNS:\s*([-\d.]+)ns',t)[1])}
 (e/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['stages']))
 if any(v<0 for v in result['stages']['route'].values()):raise RuntimeError('routed timing failure')
if __name__=='__main__':main()
