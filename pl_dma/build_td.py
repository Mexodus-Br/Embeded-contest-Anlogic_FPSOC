"""100MHz OOC serial-observation probe with untouched vendor DMA/converter."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
from prepare_ip import ROOT,TD,prepare,digest
def run(script,b,name,timeout):
 p=b/(name+'.tcl');p.write_text(script)
 with (b/(name+'.log')).open('w') as log:
  r=subprocess.run([str(TD/'bin/td_commands_prompt.exe'),p.as_posix()],cwd=b,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
 text=(b/(name+'.log')).read_text()
 # OOC pads are deliberately auto-placed. Retain this sole placement diagnostic
 # in raw reports; it is never acceptable as real board pin assignment proof.
 serious='\n'.join(x for x in text.splitlines() if 'SYN-6021' not in x)
 if r.returncode or 'DMA_TD_COMPLETE' not in text or re.search(r'\bERROR:|CRITICAL-WARNING',serious):raise RuntimeError('TD failed: '+str(b/(name+'.log')))
def stats(b,stage):
 t=(b/(stage+'.timing')).read_text();w=float(re.search(r'SWNS:\s*([-\d.]+)ns',t)[1]);h=float(re.search(r'HWNS:\s*([-\d.]+)ns',t)[1])
 return {'setup_wns_ns':w,'hold_wns_ns':h,'pass':w>=0 and h>=0,
         'start':re.search(r'Begin Point\s*:\s*(.+)',t)[1],'end':re.search(r'End Point\s*:\s*(.+)',t)[1]}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--place-route',action='store_true');ap.add_argument('--physical-only',action='store_true');ap.add_argument('--top',choices=['dma_loopback_top','dma_gp_ps_top'],default='dma_gp_ps_top');a=ap.parse_args()
 ip=prepare();b=ROOT/('build/td' if a.top=='dma_loopback_top' else 'build/td_shared');b.mkdir(parents=True,exist_ok=True)
 files=sorted((ROOT/'rtl').glob('*.v'))+[ROOT.parent/'pl_motion/rtl/gp_control_regs.v',ROOT.parent/'pl_motion/rtl/gp_ps_write_adapter.v'];inputs={str(p.relative_to(ROOT.parent)):digest(p) for p in files}
 inputs['shared_header']=digest(ROOT.parent/'pl_interface/generated/interface_defs.vh')
 result={'status':'OOC_REFERENCE_ONLY','top':a.top,'clock_period_ns':10,'reference_speed':2,'device':'DR1M90GEG400','ip':ip,'inputs':inputs}
 if not a.physical_only:
  source=(ROOT/('rtl/'+a.top+'.v')).read_text();head=source.split('module '+a.top+'(',1)[1].split(');')[0];ports={}
  for d,w,names in re.findall(r'\b(input|output)\s+wire\s*(?:\[(\d+):0\]\s*)?(.*?)(?=\binput|\boutput|$)',head,re.S):
   for n in names.strip().rstrip(',').split(','):ports[n.strip()]=(d,int(w)+1 if w else 1)
  ins={n:w for n,(d,w) in ports.items() if d=='input' and n not in ['clk_100m','arst_n']}
  outs={n:w for n,(d,w) in ports.items() if d=='output' and n not in ['hp0_aclk','gp0_aclk']};iw=sum(ins.values());ow=sum(outs.values())
  result['probe_register_bits']={'input':iw,'observation':ow}
  probe=f'module dma_td_probe(input clk,arst_n,serial_in,load,output serial_out);\nreg [{iw-1}:0] inp;reg [{ow-1}:0] obs;\n'
  for n,w in outs.items():probe+=f'wire [{w-1}:0] {n};\n'
  probe+=f'always @(posedge clk) begin inp<={{inp[{iw-2}:0],serial_in}};if(load) obs<={{{",".join(outs)}}};else obs<={{obs[{ow-2}:0],1\'b0}};end\nassign serial_out=obs[{ow-1}];\n'
  binds=['.clk_100m(clk)','.arst_n(arst_n)','.hp0_aclk()'];k=0
  if a.top=='dma_gp_ps_top':binds.append('.gp0_aclk()')
  for n,w in ins.items():binds.append(f'.{n}(inp[{k}+: {w}])');k+=w
  binds += [f'.{n}({n})' for n in outs];probe+=a.top+' dut('+','.join(binds)+');\nendmodule\n'
  (b/'probe.v').write_text(probe);(b/'dma.sdc').write_text('create_clock -name dma_clk -period 10 [get_ports clk]\n')
  header=(ROOT.parent/'pl_interface/generated/interface_defs.vh').read_text();expanded=[]
  for p in files:
   dest=b/p.name;dest.write_text(p.read_text().replace('`include "generated/interface_defs.vh"',header));expanded.append(dest)
  script=f'cd {{{b.as_posix()}}}\nimport_device dr1_90.db -package DR1M90GEG400 -speed 2\n'
  for p in [Path(x['staged']) for x in ip['libraries'].values()]+expanded+[b/'probe.v']:script+=f'analyze -file {{{p.as_posix()}}}\n'
  # TD also needs the untouched vendor includes alongside the source.
  script+='elaborate -top dma_td_probe\noptimize_rtl\nread_sdc dma.sdc\noptimize_gate -maparea gate.area\nupdate_timing\nreport_timing_summary -file gate.timing -path_num 3\ncheck_timing -verbose -file gate.check\nexport_db gate.db\nputs DMA_TD_COMPLETE\nexit\n'
  run(script,b,'gate',600);result['gate']=stats(b,'gate');result['sdc_sha256']=digest(b/'dma.sdc')
  (b/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
 else:
  saved=json.loads((b/'summary.json').read_text())
  if saved['inputs']!=inputs or saved['ip']!=ip or saved['sdc_sha256']!=digest(b/'dma.sdc'):raise RuntimeError('changed gate inputs')
  result=saved
 if not result['gate']['pass']:raise RuntimeError('100MHz gate failed')
 if a.place_route or a.physical_only:
  script=f'cd {{{b.as_posix()}}}\nimport_device dr1_90.db -package DR1M90GEG400 -speed 2\nimport_db gate.db\nread_sdc dma.sdc\nlegalize_phy_inst\nplace\nupdate_timing -mode manhattan\nreport_timing_summary -file place.timing -path_num 3\nreport_area -file place.area\nroute\nupdate_timing -mode final\nreport_timing_summary -file route.timing -path_num 3\nreport_area -file route.area\ncheck_timing -verbose -file route.check\nreport_route_status -drc\nexport_db route.db\nputs DMA_TD_COMPLETE\nexit\n'
  run(script,b,'physical',1200);result['place']=stats(b,'place');result['route']=stats(b,'route')
  if not result['route']['pass']:raise RuntimeError('100MHz route failed')
 if 'route' in result:
  area=(b/'route.area').read_text();check=(b/'route.check').read_text()
  result['route_resources']={key:int(re.search(r'^#'+key+r'\s+(\d+)',area,re.M)[1]) for key in ['lut6','reg','slice','eram','dsp','gclk','sclk']}
  result['check_timing_diagnostics']={key:int(re.search(pattern,check)[1]) for key,pattern in {'no_clock':r'checking no clock\((\d+)\)','dummy_nodes':r'checking dummy node\((\d+)\)','input_delay_missing':r'checking no input delay\((\d+)\)','output_delay_missing':r'checking no output delay\((\d+)\)'}.items()}
 (ROOT/('SUBSYSTEM_TD_RESULTS.json' if a.top=='dma_loopback_top' else 'TD_RESULTS.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['gate','place','route'] if k in result},indent=2))
if __name__=='__main__':main()
