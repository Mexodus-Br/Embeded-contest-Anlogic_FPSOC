"""Fixed XYZ-reference fixtures through the real DMA/GP/HP converters."""
import json,re,sys,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'pl_dma'));sys.path.insert(0,str(ROOT/'pl_motion/tests'))
from prepare_ip import prepare,digest
import run_motion_integration as common
def main():
 common.BUILD=ROOT/'pl_motion/build/scope_dma';b=common.BUILD;b.mkdir(parents=True,exist_ok=True);ip=prepare()
 vlog=shutil.which('vlog');vsim=shutil.which('vsim')
 common.run([Path(vlog).parent/'vlib.exe','work'],'library')
 head=(ROOT/'pl_dma/rtl/dma_gp_ps_top.v').read_text().split('module dma_gp_ps_top(',1)[1].split(');')[0]
 ports={}
 for d,w,names in re.findall(r'\b(input|output)\s+wire\s*(?:\[(\d+):0\]\s*)?(.*?)(?=\binput|\boutput|$)',head,re.S):
  for n in names.strip().rstrip(',').split(','):ports[n.strip()]=(d,int(w)+1 if w else 1)
 for n,w in [('motion_step',4),('motion_dir',4),('motion_en',4),('motion_point_start',1),('motion_point_done',1),('motion_slot_event',1),('motion_slot_id',64)]:ports[n]=('output',w)
 decl=[];bind=[];wire_inputs={'hp_arready','hp_awready','hp_wready','hp_bresp','hp_rresp'}
 for n,(d,w) in ports.items():
  decl.append(('wire' if d=='output' or n in wire_inputs else 'reg')+' '+(f'[{w-1}:0] ' if w>1 else '')+n+';');bind.append(f'.{n}({n})')
 params=','.join('.'+n+'(`SCOPE_TIMING)' for n in ['STEP_HIGH_CYCLES','STEP_LOW_CYCLES','DIR_SETUP_CYCLES','DIR_HOLD_CYCLES','EN_SETUP_CYCLES','EN_DISABLE_CYCLES'])
 params+=',.MAX_STEP_HZ(`SCOPE_RATE),.EN_ACTIVE_LEVEL(`SCOPE_EN_ACTIVE)'
 (b/'dut_bindings.vh').write_text('`include "params.vh"\n'+'\n'.join(decl)+'\nmotion_gp_ps_top #('+params+') dut('+','.join(bind)+');\n')
 text=(ROOT/'pl_dma/tb/tb_dma.v').read_text().split('task transfer;',1)[0]
 text=text.replace('module tb_dma;','module tb_scope_dma;\n`include "generated/interface_defs.vh"').replace('2000000','110000000')
 text=re.sub(r'\bs_', 'gp_',text)
 # Ready may legally depend on VALID. Retain deterministic stalls during
 # real requests; avoid unrelated toggles throughout the 500ms motion point.
 text=text.replace('hp_arready=control_rst_n &&','hp_arready=control_rst_n && hp_arvalid &&')
 text=text.replace('hp_awready=control_rst_n &&','hp_awready=control_rst_n && hp_awvalid &&')
 text='\n'.join(x for x in text.split('\n') if 'dut.bridge_' not in x and 'loop_occupancy' not in x)
 start=text.index('  if(monitor_packet');end=text.index('\n end\nend\n// AXI',start)
 text=text[:start]+text[end:]
 text+='`include "scope_dma_scenarios.vh"\nendmodule\n'
 assert 'dut.' not in text,'scope observations must use public ports'
 tb=b/'tb_scope_dma.v';tb.write_text(text)
 for p in (ROOT/'pl_motion/scope_test/generated').glob('*.hex'):shutil.copyfile(p,b/p.name)
 rtl=sorted((ROOT/'pl_dma/rtl').glob('*.v'))+sorted((ROOT/'pl_motion/rtl').glob('*.v'))
 common.run([vlog,'-work','work','+incdir+'+str(ROOT/'pl_interface'),'+incdir+'+str(b),'+incdir+'+str(ROOT/'pl_motion/tests'),'+incdir+'+str(ROOT/'pl_motion/scope_test/generated'),'+incdir+'+str(ROOT/'pl_dma/build/ip'),*[Path(x['staged']) for x in ip['libraries'].values()],*rtl,tb],'compile')
 with (b/'simulation.log').open('w',encoding='utf-8') as output:
  r=subprocess.run([vsim,'-batch','work.tb_scope_dma','-do','onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0'],cwd=b,stdout=output,stderr=subprocess.STDOUT,timeout=7200)
 log=(b/'simulation.log').read_text(encoding='utf-8')
 if r.returncode or re.search(r'\*\* (Error|Fatal)',log):raise RuntimeError('scope simulation failed; '+str(b/'simulation.log'))
 marker=next((x for x in log.splitlines() if 'PASS scope_gpio' in x),None)
 if not marker:raise RuntimeError('scope selfcheck incomplete')
 result={'status':'PASS','result':marker,'real_ip':ip,'sources':{str(p.relative_to(ROOT)):digest(p) for p in rtl+[ROOT/'pl_motion/tests/scope_dma_scenarios.vh',ROOT/'pl_interface/schema.json']},'logs':{p.name:digest(p) for p in b.glob('*.log')},'waveform':'scope_outputs.vcd','edge_table':'observed_edges.csv','hierarchical_motion_observation':False}
 (ROOT/'pl_motion/scope_test/SIM_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n');print(marker)
if __name__=='__main__':main()
