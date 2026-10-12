"""Required real DMA and HP conversion simulation; no behavioral substitute."""
import argparse,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from prepare_ip import prepare
def run(args,b,name):
 r=subprocess.run(list(map(str,args)),cwd=b,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=240)
 (b/(name+'.log')).write_text(r.stdout,encoding='utf-8')
 if r.returncode or re.search(r'\*\* (Error|Fatal)',r.stdout):raise RuntimeError('simulation failed '+name+'\n'+r.stdout[-5000:])
 return r.stdout
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--shared',action='store_true');a=ap.parse_args()
 module='dma_gp_ps_top' if a.shared else 'dma_loopback_top'
 manifest=prepare();b=ROOT/('build/questa_shared' if a.shared else 'build/questa');b.mkdir(parents=True,exist_ok=True)
 top=(ROOT/('rtl/'+module+'.v')).read_text();head=top.split('module '+module+'(',1)[1].split(');')[0]
 ports={}
 for d,w,names in re.findall(r'\b(input|output)\s+wire\s*(?:\[(\d+):0\]\s*)?(.*?)(?=\binput|\boutput|$)',head,re.S):
  for n in names.strip().rstrip(',').split(','):ports[n.strip()]=(d,int(w)+1 if w else 1)
 decl=[];bindings=[];wire_inputs={'hp_arready','hp_awready','hp_wready','hp_bresp','hp_rresp'}
 for n,(d,w) in ports.items():
  decl.append(('wire' if d=='output' or n in wire_inputs else 'reg')+' '+(f'[{w-1}:0] ' if w>1 else '')+n+';')
  bindings.append(f'.{n}({n})')
 (b/'dut_bindings.vh').write_text('\n'.join(decl)+'\n'+module+' dut('+','.join(bindings)+');\n')
 vlog=shutil.which('vlog');vsim=shutil.which('vsim')
 if not vlog or not vsim:raise RuntimeError('Questa required for real protected DMA')
 run([Path(vlog).parent/'vlib.exe',b/'work'],b,'library')
 deps=[ROOT.parent/'pl_motion/rtl/gp_control_regs.v',ROOT.parent/'pl_motion/rtl/gp_ps_write_adapter.v']
 test=ROOT/'tb/tb_dma.v';test_module='tb_dma'
 if a.shared:
  text=test.read_text().replace('module tb_dma;','module tb_dma_shared;')
  text=re.sub(r'\bs_', 'gp_',text)
  text=text.replace('dut.d_','dut.core.fabric.dma_core.d_').replace('dut.bridge_','dut.core.fabric.dma_core.bridge_')
  text=text.replace('`include "dut_bindings.vh"','`include "dut_bindings.vh"\nwire [31:0] loop_occupancy=dut.core.fabric.dma_core.loop_occupancy;')
  text=text.replace('clk_100m=0;arst_n=0;','clk_100m=0;arst_n=0;gp_awid=0;gp_arid=0;gp_awlen=0;gp_arlen=0;gp_awsize=2;gp_arsize=2;gp_awburst=1;gp_arburst=1;gp_awlock=0;gp_arlock=0;gp_awcache=0;gp_arcache=0;gp_awprot=0;gp_arprot=0;gp_wlast=1;')
  text=text.replace('polls=0;status_value=0;',"write_reg(33'h08040006c,32'hcafe1234,15,0,1);read_reg(33'h08040006c,0,status_value);check(status_value==32'hcafe1234,\"GP scratch during DMA\");polls=0;status_value=0;")
  text=text.replace('reset_design;\n read_reg(BASE+4', 'reset_design;\n fork write_reg(BASE+40,0,15,2,2);read_reg(33\'h080400000,0,status_value);join\n check(status_value==1,"independent GP read/DMA write ownership");\n fork write_reg(33\'h08040006c,32\'h5432abcd,15,0,1);read_reg(BASE+4,0,status_value);join\n check(status_value[0],"independent DMA read/GP write ownership");\n read_reg(BASE+4')
  test=b/'tb_dma_shared.v';test.write_text(text);test_module='tb_dma_shared'
 sources=[Path(x['staged']) for x in manifest['libraries'].values()]+deps+sorted((ROOT/'rtl').glob('*.v'))+[test]
 run([vlog,'-work',b/'work','+incdir+'+str(ROOT.parent/'pl_interface'),'+incdir+'+str(b),'+incdir+'+str(ROOT/'build/ip'),*sources],b,'compile')
 log=run([vsim,'-batch','work.'+test_module,'-do','onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0'],b,'dma')
 marker=next((x for x in log.splitlines() if 'PASS dma_real_ip' in x),None)
 if not marker:raise RuntimeError('required self-check completion missing\n'+log[-4000:])
 result={'status':'PASS','simulator':vsim,'real_ip':manifest,'result':marker,
         'source_sha256':{str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sources if x.is_relative_to(ROOT) and 'build' not in x.parts}}
 if a.shared:
  gp=(ROOT.parent/'pl_motion/tb/tb_gp_control_top.v').read_text()
  gp=gp.replace('module tb_gp_ps_control_top;','module tb_gp_dma_probe;').replace('gp_ps_control_top dut','dma_gp_ps_top dut')
  # Existing fixture tests unused IRQ bits at clock initialization time zero.
  # Shared DMA has live bits1/2: sample after combinational reset settles.
  gp=gp.replace('always @(negedge clk_100m) begin','always @(negedge clk_100m) begin #1;')
  extras=[]
  for n,(d,w) in ports.items():
   if n.startswith('hp_') or n=='hp0_aclk':extras.append(f'.{n}('+ (f"{w}'d0" if d=='input' else '')+')')
  gp=gp.replace('.gp_rvalid(gp_rvalid),.gp_rready(gp_rready)', '.gp_rvalid(gp_rvalid),.gp_rready(gp_rready),'+','.join(extras))
  (b/'tb_gp_dma_probe.v').write_text('`define GP_PS_BOUNDARY\n'+gp)
  run([vlog,'-work',b/'work','+incdir+'+str(ROOT.parent/'pl_interface'),b/'tb_gp_dma_probe.v'],b,'compile_gp_probe')
  glog=run([vsim,'-batch','work.tb_gp_dma_probe','-do','onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0'],b,'gp_probe')
  result['gp_regression']=next((x for x in glog.splitlines() if 'PASS gp_ps_control_top' in x),None)
  if not result['gp_regression']:raise RuntimeError('GP shared-fabric regression did not complete')
 (ROOT/('SHARED_SIM_RESULTS.json' if a.shared else 'SIM_RESULTS.json')).write_text(json.dumps(result,indent=2)+'\n');print(marker)
if __name__=='__main__':
 try:main()
 except Exception as error:
  (ROOT/('SHARED_SIM_RESULTS.json' if '--shared' in sys.argv else 'SIM_RESULTS.json')).write_text(json.dumps({'status':'FAILED','error':str(error)},indent=2)+'\n')
  raise
