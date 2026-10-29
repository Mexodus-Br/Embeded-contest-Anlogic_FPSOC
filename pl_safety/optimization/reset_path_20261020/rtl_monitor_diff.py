"""Original monitor assertions and all-output cycle miter, current wrap flags on."""
import argparse,json,re,shutil,subprocess
from pathlib import Path
from equivalence import outputs
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);a=p.parse_args()
 c=Path(a.candidate).resolve();out=E/a.tag;out.mkdir(exist_ok=False)
 original=(R/'pl_safety/rtl/safety_interlock.v').read_text();(out/'reference.v').write_text(original.replace('module safety_interlock','module ref_safety_interlock',1))
 header=original.split(')(\n',1)[1].split(');',1)[0];ports=[]
 for block in re.finditer(r'\b(?:input|output)\b(.*?)(?=\b(?:input|output)\b|$)',header,re.S):
  text=re.sub(r'\[[^]]*\]|\b(?:wire|reg|signed)\b','',block[1]);ports+=re.findall(r'\b[A-Za-z_]\w*\b',text)
 tb=(R/'pl_safety/tests/tb_interlock.v').read_text();start=tb.index(' safety_interlock dut(');end=tb.index(');',start)+2;inst=tb[start:end]
 args=[x.strip() for x in inst.split('dut(',1)[1][:-2].split(',')];assert len(args)==len(ports),(len(args),len(ports))
 decl=[];checks=[];clone_args=args[:]
 for i,port in enumerate(ports):
  if port not in outputs(original):continue
  expr=args[i];assert re.fullmatch(r'\w+',expr),expr;clone_args[i]='ref_'+expr
  decl.append('wire '+outputs(original)[port]+' ref_'+expr+';');checks.append(f'if({expr} !== ref_{expr})$fatal(1,"monitor differential {port}");')
 clone='ref_safety_interlock golden('+','.join(clone_args)+');'
 observe='\n'+'\n'.join(decl)+'\n'+clone+'\ninteger miter_cycles=0;always @(posedge clk)begin #1;miter_cycles=miter_cycles+1;\n'+'\n'.join(checks)+'\nend\n'
 tb=tb[:start]+inst.replace('safety_interlock dut(', 'safety_interlock #(.LOOKAHEAD_WRAP(1)) dut(')+observe+tb[end:]
 # The original test preloads the owner watermark to skip 2^64 OPEN calls;
 # apply the same stimulus to the independent reference, without changing it.
 tb=re.sub(r'dut\.owner_watermark=(.*?);',lambda m:m[0]+'golden.owner_watermark='+m[1]+';',tb)
 tb=tb.replace('$finish;','$display("PASS monitor wrap current-state differential cycles=%0d",miter_cycles);$finish;');(out/'tb.v').write_text(tb)
 result={'passed':False,'hashes_computed':False}
 try:
  for phase,cmd in [('compile',[shutil.which('iverilog'),'-g2005','-I',str(R/'pl_safety/generated'),'-I',str(R/'pl_rs485/generated'),'-s','tb_interlock','-o',str(out/'test.vvp'),str(c/'safety_interlock.v'),str(R/'pl_rs485/rtl/rs485_light_parse.v'),str(out/'reference.v'),str(out/'tb.v')]),('simulation',[shutil.which('vvp'),str(out/'test.vvp')])]:
   with (out/f'{phase}.log').open('w') as log:proc=subprocess.run(cmd,cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=120)
   assert proc.returncode==0,phase
  log=(out/'simulation.log').read_text();assert 'PASS monitor wrap current-state differential' in log
  result.update(passed=True,output=log);print(log)
 finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
