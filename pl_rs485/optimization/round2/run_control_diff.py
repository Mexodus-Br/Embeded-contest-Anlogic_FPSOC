"""Cycle-exact control/collector comparison against the archived parent candidate."""
import argparse,hashlib,json,os,re,shutil,subprocess
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[2]
def ports(text):
 h=text.split(')(input',1)[1] if ')(input' in text else text.split(')(\n',1)[-1]
 h=('input'+h if ')(input' in text else h).split(');',1)[0]
 result={}
 for m in re.finditer(r'\b(input|output)\s+(?:wire|reg)\s*(?:\[(\d+):0\]\s*)?(.*?)(?=\binput|\boutput|$)',h,re.S):
  direction,width,names=m.groups()
  for n in names.split(','):
   if n.strip():result[n.strip()]=(direction,int(width)+1 if width else 1)
 return result
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);a=ap.parse_args();D=E/('control_'+a.tag);D.mkdir(exist_ok=False)
 env=os.environ.copy();system=Path(os.environ['SystemRoot']);iv=shutil.which('iverilog');vvp=shutil.which('vvp')
 env['PATH']=os.pathsep.join([str(Path(iv).parent),str(system/'System32'),str(system)]);env['TMP']=env['TEMP']=str(D)
 results=[]
 for module,bench in [('rs485_gp_regs','tb_gp_regs'),('rs485_multirate','tb_multirate')]:
  rtl=(R/'pl_rs485/rtl'/(module+'.v')).read_text(encoding='utf-8');old=(E/'baseline'/(module+'.v')).read_text(encoding='utf-8')
  (D/(module+'_reference.v')).write_text(old.replace('module '+module,'module '+module+'_reference',1),encoding='utf-8')
  tb=(R/'pl_rs485/tests'/(bench+'.v')).read_text(encoding='utf-8');start=tb.index(' '+module+' ')
  end=tb.index(');',tb.index('dut(',start))+2;inst=tb[start:end];ref=inst.replace(module+' ',module+'_reference ',1).replace('dut(','reference_dut(',1)
  decl=[];comp=[]
  for name,signal in re.findall(r'\.(\w+)\((\w+)\)',inst[inst.index('dut('):]):
   direction,width=ports(rtl)[name]
   if direction!='output':continue
   decl.append('wire '+(f'[{width-1}:0] ' if width>1 else '')+'ref_'+signal+';')
   ref=ref.replace('.'+name+'('+signal+')','.'+name+'(ref_'+signal+')')
   condition='valid && ' if name=='record_data' else 's_rvalid && ' if name in ['s_rdata','s_rresp'] else 's_bvalid && ' if name=='s_bresp' else ''
   comp.append(f'if({condition}{signal}!==ref_{signal}) $fatal(1,"cycle differential {module}.{name}");')
  tb=tb[:end]+'\n'+'\n'.join(decl)+'\n'+ref+'\ninteger diff_cycles=0;always @(negedge clk) if(rst_n) begin diff_cycles=diff_cycles+1;\n'+'\n'.join(comp)+'\nend\n'+tb[end:]
  tb=re.sub(r'force dut\.(\w+)=(.*?);',lambda m:m[0]+f'force reference_dut.{m[1]}={m[2]};',tb)
  tb=re.sub(r'release dut\.(\w+);',lambda m:m[0]+f'release reference_dut.{m[1]};',tb)
  tb=tb.replace('$finish;', '$display("PASS control differential cycles=%0d",diff_cycles);$finish;')
  if module=='rs485_multirate':
   saturation='''
 integer sat_i,sat_seed=20261015;reg [31:0] sat_a;reg [63:0] sat_b;
 initial begin
  for(sat_i=0;sat_i<65536;sat_i=sat_i+1) begin
   sat_a=$random(sat_seed);sat_b={$random(sat_seed),$random(sat_seed)};
   case(sat_i%8)
    0:sat_b=0;1:sat_b=1;2:sat_b=64'hffffffff;
    3:sat_b=64'h100000000;4:sat_b=64'hffffffffffffffff;
    5:sat_b={32'd0,$random(sat_seed)};6:sat_a=32'hffffffff;
   endcase
   if(dut.sat_add(sat_a,sat_b)!==reference_dut.sat_add(sat_a,sat_b)) $fatal(1,"saturation differential");
  end
  $display("PASS 65536 unsigned saturation edge/random differential vectors");
 end
 '''
   tb=tb.replace('endmodule',saturation+'\nendmodule')
  (D/(bench+'.v')).write_text(tb,encoding='utf-8')
  sources=list((R/'pl_rs485/rtl').glob('*.v'))+[D/(module+'_reference.v'),D/(bench+'.v')]
  for label,cmd in [('compile',[iv,'-g2005','-I',str(R/'pl_rs485/generated'),'-I',str(R/'pl_rs485/tests'),'-s',bench,'-o',str(D/(bench+'.vvp')),*map(str,sources)]),('simulation',[vvp,str(D/(bench+'.vvp'))])]:
   p=subprocess.run(cmd,cwd=D,env=env,capture_output=True,text=True,timeout=900);(D/(bench+'_'+label+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8');assert p.returncode==0,(bench,label,p.stdout+p.stderr)
  assert 'PASS control differential' in p.stdout
  results.append(p.stdout.strip());print(p.stdout,flush=True)
 (D/'result.json').write_text(json.dumps({'passed':True,'cycle_changes':0,'results':results,'source_sha256':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['pl_rs485/rtl/rs485_gp_regs.v','pl_rs485/rtl/rs485_multirate.v']}},indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
