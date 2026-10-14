"""Real S2MM-only vendor IP probes. Existing result files are never overwritten."""
import argparse,json,re,shutil,subprocess,sys,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'pl_dma'))
from prepare_ip import prepare
from generate_telemetry import portnames
def run(args,b,name,timeout=240):
 p=subprocess.run(list(map(str,args)),cwd=b,capture_output=True,text=True,timeout=timeout);out=p.stdout+p.stderr
 (b/(name+'.log')).write_text('COMMAND '+repr(list(map(str,args)))+'\nEXIT '+str(p.returncode)+'\n'+out,encoding='utf-8')
 if p.returncode or re.search(r'\*\* (Error|Fatal)',out):raise RuntimeError('failed '+name+'; log retained')
 return out
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);a=ap.parse_args()
 if not a.tag.replace('_','').isalnum():raise ValueError('tag')
 b=R/'pl_dma/build'/('telemetry_'+a.tag);b.mkdir(parents=True,exist_ok=False)
 ip=prepare();top=(R/'pl_dma/rtl/telemetry_dma_lite_top.v').read_text();head=top.split('module telemetry_dma_lite_top(',1)[1].split(');',1)[0];ports=portnames(head)
 wire_inputs={'hp_arready','hp_awready','hp_wready','hp_bresp','hp_rresp'};decl=[];bind=[]
 for n,(d,w) in ports.items():
  decl.append(('wire' if d=='output' or n in wire_inputs else 'reg')+' '+(f'[{w-1}:0] ' if w>1 else '')+n+';');bind.append('.'+n+'('+n+')')
 (b/'dut_bindings.vh').write_text('\n'.join(decl)+'\nwire [31:0] loop_occupancy=0;\ntelemetry_dma_lite_top dut('+','.join(bind)+');\n')
 tb=(R/'pl_dma/tb/tb_dma.v').read_text().split('task transfer;',1)[0].replace('module tb_dma;','module tb_s2mm_real;').replace("33'h080500000","33'h080900000")
 tb+=(R/'pl_dma/tb/telemetry_ip_scenarios.vh').read_text()+'\nendmodule\n';(b/'tb.v').write_text(tb)
 vlog=shutil.which('vlog');vsim=shutil.which('vsim')
 run([Path(vlog).parent/'vlib.exe','work'],b,'library')
 sources=[Path(x['staged']) for x in ip['libraries'].values()]+list((R/'pl_dma/rtl').glob('*.v'))+[b/'tb.v']
 run([vlog,'-work','work','+incdir+'+str(R/'pl_interface'),'+incdir+'+str(R/'pl_dma/build/ip'),'+incdir+'+str(b),*sources],b,'compile')
 out=run([vsim,'-batch','work.tb_s2mm_real','-do','onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0'],b,'simulation')
 if 'PASS telemetry_real_s2mm' not in out:raise RuntimeError('missing selfcheck marker')
 e=R/'pl_dma/reports'/('telemetry_'+a.tag);e.mkdir(exist_ok=False)
 for p in b.glob('*.log'):shutil.copyfile(p,e/p.name)
 result={'status':'PASS','real_ip':ip,'result':[x for x in out.splitlines() if 'PROBE' in x or 'PASS telemetry' in x],
 'source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources if p.is_relative_to(R) and 'build' not in p.parts}}
 (e/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('\n'.join(result['result']))
if __name__=='__main__':main()
