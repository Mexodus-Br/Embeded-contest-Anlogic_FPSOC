"""Compare complete GP/collector read views to the retained candidate21 RTL."""
import argparse,json,re,shutil,subprocess
from pathlib import Path
from equivalence import outputs
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-directory',required=True);p.add_argument('--tag',required=True);p.add_argument('--stats-valid',action='store_true');p.add_argument('--private-payload',action='store_true');a=p.parse_args()
 candidate=Path(a.source_directory).resolve();out=E/a.tag;out.mkdir(exist_ok=False)
 result={'passed':False,'hashes_computed':False,'cases':[]}
 try:
  for module,bench in [('rs485_gp_regs','tb_gp_regs'),('rs485_multirate','tb_multirate')]:
   current=R/'pl_rs485/rtl'/f'{module}.v'
   original=current.read_text();old=out/f'ref_{module}.v';old.write_text(original.replace('module '+module,'module ref_'+module,1))
   tb=(R/'pl_rs485/tests'/f'{bench}.v').read_text();start=tb.index(' '+module+' ');end=tb.index(');',tb.index('dut(',start))+2
   inst=tb[start:end];clone=inst.replace(module+' ','ref_'+module+' ',1).replace('dut(','golden(',1)
   decl=[];compare=[];port_widths=outputs(original)
   for port,expr in re.findall(r'\.(\w+)\((\w+)\)',inst):
    if port not in port_widths:continue
    decl.append('wire '+port_widths[port]+' ref_'+expr+';');clone=clone.replace(f'.{port}({expr})',f'.{port}(ref_{expr})')
    cond='valid && ' if port=='record_data' else ''
    if a.private_payload and port in ['cfg_period_us','cfg_mask']:cond='dut.cfg_valid && '
    compare.append(f'if({cond}{expr} !== ref_{expr})$fatal(1,"RTL control mismatch {module}.{port}");')
   # Also compare every counter view, not only the debug selector, and reset
   # between edges during each existing reset fixture.
   extra=''
   if module=='rs485_multirate':
    extra='if(dut.observe_tasks !== golden.observe_tasks)$fatal(1,"all statistics views differ");'
    if a.stats_valid:
     extra='''if(dut.observe_stats_ready !== golden.initialized)$fatal(1,"statistics valid lifecycle differs");
if(dut.observe_stats_ready && dut.observe_tasks !== golden.observe_tasks)$fatal(1,"all valid statistics views differ");'''
    tb=tb.replace('task reset_case;', 'task reset_case;')
   observe='\n'+'\n'.join(decl)+'\n'+clone+'\ninteger diff_cycles=0;always @(negedge clk)begin #1;diff_cycles=diff_cycles+1;\n'+'\n'.join(compare)+'\n'+extra+'\nend\n'
   tb=tb[:end]+observe+tb[end:]
   tb=re.sub(r'force dut\.(\w+)=(.*?);',lambda m:m[0]+f'force golden.{m[1]}={m[2]};',tb)
   tb=re.sub(r'release dut\.(\w+);',lambda m:m[0]+f'release golden.{m[1]};',tb)
   tb=tb.replace('$finish;','$display("DIFF_CYCLES %0d",diff_cycles);$finish;')
   target=out/f'{bench}.v';target.write_text(tb)
   sources=[candidate/f.name if (candidate/f.name).exists() else f for f in (R/'pl_rs485/rtl').glob('*.v')]
   for phase,cmd in [('compile',[shutil.which('iverilog'),'-g2005','-I',str(R/'pl_rs485/generated'),'-I',str(R/'pl_rs485/tests'),'-s',bench,'-o',str(out/f'{bench}.vvp'),*map(str,sources+[old,target])]),('simulation',[shutil.which('vvp'),str(out/f'{bench}.vvp')])]:
    with (out/f'{module}_{phase}.log').open('w') as log:proc=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
    assert proc.returncode==0,(module,phase,proc.returncode)
   log=(out/f'{module}_simulation.log').read_text();assert 'PASS' in log and 'DIFF_CYCLES' in log
   rec={'module':module,'passed':True,'cycles':int(re.search(r'DIFF_CYCLES (\d+)',log)[1])};result['cases'].append(rec);print(rec,flush=True)
  result['passed']=True
 finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
