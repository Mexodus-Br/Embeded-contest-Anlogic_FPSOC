"""Real protected DMA+GP/HP converter integration with unchanged HP BFM."""
import json,re,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'pl_dma'));sys.path.insert(0,str(ROOT/'pl_motion/tests'))
from prepare_ip import prepare,digest
import run_motion_integration as common
def main():
 common.BUILD=ROOT/'pl_dma/build/questa_motion';b=common.BUILD;b.mkdir(parents=True,exist_ok=True);ip=prepare()
 vlog=shutil.which('vlog');vsim=shutil.which('vsim')
 common.run([Path(vlog).parent/'vlib.exe','work'],'library')
 top=(ROOT/'pl_dma/rtl/dma_gp_ps_top.v').read_text();head=top.split('module dma_gp_ps_top(',1)[1].split(');')[0]
 ports={}
 for d,w,names in re.findall(r'\b(input|output)\s+wire\s*(?:\[(\d+):0\]\s*)?(.*?)(?=\binput|\boutput|$)',head,re.S):
  for n in names.strip().rstrip(',').split(','):ports[n.strip()]=(d,int(w)+1 if w else 1)
 decl=[];bind=[];wire_inputs={'hp_arready','hp_awready','hp_wready','hp_bresp','hp_rresp'}
 for n,(d,w) in ports.items():
  decl.append(('wire' if d=='output' or n in wire_inputs else 'reg')+' '+(f'[{w-1}:0] ' if w>1 else '')+n+';');bind.append(f'.{n}({n})')
 params=','.join(f'.{n}({{4{{64\'d{x}}}}})' for n,x in [('STEP_HIGH_CYCLES',3),('STEP_LOW_CYCLES',2),('DIR_SETUP_CYCLES',4),('DIR_HOLD_CYCLES',7),('EN_SETUP_CYCLES',5),('EN_DISABLE_CYCLES',3),('MAX_STEP_HZ',10000000)])
 (b/'dut_bindings.vh').write_text('\n'.join(decl)+'\nmotion_gp_ps_top #('+params+') dut('+','.join(bind)+');\n')
 text=(ROOT/'pl_dma/tb/tb_dma.v').read_text().split('task transfer;',1)[0]
 text=text.replace('module tb_dma;','module tb_motion_dma;\n`include "generated/interface_defs.vh"')
 text=re.sub(r'\bs_', 'gp_',text).replace('dut.d_','dut.core.fabric.dma_core.d_').replace('dut.bridge_','dut.core.fabric.dma_core.bridge_')
 text=text.replace('reg rd_active=0','reg hp_read_error=0;reg rd_active=0').replace('assign hp_rresp=0;','assign hp_rresp=hp_read_error ? 2 : 0;')
 text=text.replace('`include "dut_bindings.vh"','`include "dut_bindings.vh"\nwire [31:0] loop_occupancy=dut.core.fabric.dma_core.loop_occupancy;')
 text+='`include "motion_dma_scenarios.vh"\nendmodule\n';tb=b/'tb_motion_dma.v';tb.write_text(text)
 rtl=sorted((ROOT/'pl_dma/rtl').glob('*.v'))+sorted((ROOT/'pl_motion/rtl').glob('*.v'))
 common.run([vlog,'-work','work','+incdir+'+str(ROOT/'pl_interface'),'+incdir+'+str(b),'+incdir+'+str(ROOT/'pl_dma/tb'),'+incdir+'+str(ROOT/'pl_dma/build/ip'),*[Path(x['staged']) for x in ip['libraries'].values()],*rtl,tb],'compile')
 log=common.run([vsim,'-batch','work.tb_motion_dma','-do','onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0'],'simulation')
 marker=next((x for x in log.splitlines() if 'PASS motion_dma_real_ip' in x),None)
 if not marker:raise RuntimeError('real motion selfcheck incomplete')
 gp=(ROOT/'pl_motion/tb/tb_gp_control_top.v').read_text().replace('module tb_gp_ps_control_top;','module tb_gp_motion_probe;').replace('gp_ps_control_top dut','motion_gp_ps_top dut')
 gp=gp.replace('always @(negedge clk_100m) begin','always @(negedge clk_100m) begin #1;')
 extras=[]
 for n,(d,w) in ports.items():
  if n.startswith('hp_') or n=='hp0_aclk':extras.append('.'+n+'('+ (f"{w}'d0" if d=='input' else '')+')')
 gp=gp.replace('.gp_rvalid(gp_rvalid),.gp_rready(gp_rready)', '.gp_rvalid(gp_rvalid),.gp_rready(gp_rready),'+','.join(extras))
 probe=b/'tb_gp_motion_probe.v';probe.write_text('`define GP_PS_BOUNDARY\n'+gp)
 common.run([vlog,'-work','work','+incdir+'+str(ROOT/'pl_interface'),probe],'compile_probe')
 glog=common.run([vsim,'-batch','work.tb_gp_motion_probe','-do','onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0'],'probe')
 gmarker=next((x for x in glog.splitlines() if 'PASS gp_ps_control_top' in x),None)
 if not gmarker:raise RuntimeError('original probe regression incomplete')
 result={'status':'PASS','result':marker,'probe_regression':gmarker,'real_ip':ip,'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in rtl+[ROOT/'pl_dma/tb/motion_dma_scenarios.vh',ROOT/'pl_interface/schema.json']},'logs':{p.name:digest(p) for p in b.glob('*.log')}}
 (ROOT/'pl_dma/MOTION_DMA_SIM_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n');print(marker)
if __name__=='__main__':main()
