"""Real two-controller GP/HP0/HP1 system + reference motion differential test."""
import argparse,re,json,hashlib,shutil,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'pl_dma'));sys.path.insert(0,str(R/'pl_dma/tests'))
from prepare_ip import prepare
from generate_telemetry import portnames
from run_telemetry import run
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);a=ap.parse_args();b=R/'pl_dma/build'/('telemetry_system_'+a.tag);b.mkdir(exist_ok=False)
 ip=prepare();top=(R/'pl_dma/rtl/rs485_gp_ps_top.v').read_text();head=top.split(')(\n',1)[1].split(');',1)[0];ports=portnames(head)
 decl=[];bind=[];refbind=[];refs=[]
 for n,(d,w) in ports.items():
  wire=d=='output' or n in ['hp_arready','hp_awready','hp_wready','hp_bresp','hp_rresp'] or n.startswith('hp1_') and n not in ['hp1_bid','hp1_bvalid']
  decl.append(('wire' if wire else 'reg')+' '+(f'[{w-1}:0] ' if w>1 else '')+n+';');bind.append('.'+n+'('+n+')')
  if n.startswith(('hp1_','rs485_')):continue
  if d=='input':refbind.append('.'+n+'('+n+')')
  else:
   refs.append('wire '+(f'[{w-1}:0] ' if w>1 else '')+'ref_'+n+';');refbind.append('.'+n+'(ref_'+n+')')
 params=','.join('.'+n+'({4{64\'d'+str(x)+'}})' for n,x in [('STEP_HIGH_CYCLES',3),('STEP_LOW_CYCLES',2),('DIR_SETUP_CYCLES',4),('DIR_HOLD_CYCLES',7),('EN_SETUP_CYCLES',5),('EN_DISABLE_CYCLES',3),('MAX_STEP_HZ',10000000)])
 (b/'dut_bindings.vh').write_text('\n'.join(decl+refs)+'\nrs485_gp_ps_top #('+params+') dut('+','.join(bind)+');\nmotion_gp_ps_top #('+params+') reference_motion('+','.join(refbind)+');\n')
 tb=(R/'pl_dma/tb/tb_dma.v').read_text().split('task transfer;',1)[0];tb=tb.replace('module tb_dma;','module tb_telemetry_system;\n`include "generated/interface_defs.vh"\n`include "telem_defs.vh"\n`include "gp_defs.vh"')
 tb=re.sub(r'\bs_','gp_',tb).replace('dut.d_','dut.core.fabric.dma_core.d_').replace('dut.bridge_','dut.core.fabric.dma_core.bridge_').replace('cycle>2000000','cycle>20000000')
 tb=tb.replace('`include "dut_bindings.vh"','`include "dut_bindings.vh"\nwire [31:0] loop_occupancy=dut.core.fabric.dma_core.loop_occupancy;')
 helpers=(R/'pl_dma/tb/motion_dma_scenarios.vh').read_text().split('initial begin',1)[0]
 tb+=helpers+(R/'pl_dma/tb/telemetry_hp1_bfm.vh').read_text()+(R/'pl_dma/tb/telemetry_system_scenarios.vh').read_text()+'\nendmodule\n';(b/'tb.v').write_text(tb)
 vlog=shutil.which('vlog');vsim=shutil.which('vsim');run([Path(vlog).parent/'vlib.exe','work'],b,'library')
 rtl=[p for d in ['pl_dma','pl_motion','pl_rs485'] for p in (R/d/'rtl').glob('*.v')]
 sources=[Path(x['staged']) for x in ip['libraries'].values()]+rtl+[b/'tb.v']
 run([vlog,'-work','work','+incdir+'+str(R/'pl_interface'),'+incdir+'+str(R/'pl_rs485/generated'),'+incdir+'+str(R/'pl_dma/build/ip'),'+incdir+'+str(b),*sources],b,'compile')
 out=run([vsim,'-batch','work.tb_telemetry_system','-do','onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0'],b,'simulation',timeout=600)
 if 'PASS telemetry_system_real' not in out:raise RuntimeError('missing end-to-end completion')
 e=R/'pl_dma/reports'/('telemetry_system_'+a.tag);e.mkdir(exist_ok=False)
 for p in b.glob('*.log'):shutil.copyfile(p,e/p.name)
 result={'status':'PASS','real_ip':ip,'result':[x for x in out.splitlines() if 'PASS telemetry' in x], 'source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in rtl}}
 (e/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('\n'.join(result['result']))
if __name__=='__main__':main()
