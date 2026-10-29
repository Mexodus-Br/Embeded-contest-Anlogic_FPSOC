"""All safety-service output ports: candidate vs preserved36, same test inputs."""
import argparse,importlib.util,json,re,shutil,subprocess,sys
from pathlib import Path
from equivalence import outputs
E=Path(__file__).resolve().parent;R=E.parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);a=p.parse_args()
 c=Path(a.candidate).resolve();o=E/a.tag;o.mkdir(exist_ok=False)
 folders=['pl_safety/rtl','pl_motion/rtl','pl_rs485/rtl'];base=E/'rtl36_candidate_r1'
 originals=[base/f.name if (base/f.name).is_file() else f for d in folders for f in (R/d).glob('*.v')]
 names=set(n for f in originals for n in re.findall(r'\bmodule\s+(\w+)',f.read_text()))
 refs=[]
 for f in originals:
  text=re.sub(r'\b('+'|'.join(sorted(names))+r')\b',lambda m:'ref_'+m[0],f.read_text())
  dest=o/('ref_'+f.name);dest.write_text(text);refs.append(dest)
 sources=[c/f.name if (c/f.name).is_file() else f for d in folders for f in (R/d).glob('*.v')]
 spec=importlib.util.spec_from_file_location('fixture',E/'rtl37_suite_r3/rtl26_motion_fixture.py');fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
 templates=[('legacy',(R/'pl_safety/tests/tb_safety.v').read_text()),('motion',fixture.render())]
 cases=[]
 for label,tb in templates:
  m=re.search(r'safety_motion_service\s*#\(.*?\)\s+dut\(',tb,re.S);assert m
  end=tb.index(');',m.end())+2;instance=tb[m.start():end]
  clone=instance.replace('safety_motion_service #','ref_safety_motion_service #',1).replace(' dut(',' golden(',1)
  # New private qualification is absent from the preserved36 interface.
  clone=re.sub(r'\.collector_query_ok\([^()]*\),','',clone)
  fields=outputs((base/'safety_motion_service.v').read_text())
  clone=re.sub(r'\.(\w+)\(([^()]*)\)',lambda m:'.'+m[1]+'('+('' if m[1] in fields else m[2])+')',clone)
  checks='\n'.join(f'if(dut.{n} !== golden.{n})$fatal(1,"safety cycle differential {n}");' for n in fields)
  observe=clone+'\ninteger cycle_miter=0;always @(posedge clk)begin #1;cycle_miter=cycle_miter+1;\n'+checks+'\nend\n'
  tb=tb.replace('endmodule',observe+'\nendmodule')
  tb=re.sub(r'force dut\.(.*?);',lambda m:m[0]+'force golden.'+m[1]+';',tb)
  tb=re.sub(r'release dut\.(.*?);',lambda m:m[0]+'release golden.'+m[1]+';',tb)
  tb=tb.replace('$finish;','$display("CYCLE_MITER %0d",cycle_miter);$finish;')
  path=o/(label+'.v');path.write_text(tb);top=re.search(r'\bmodule\s+(\w+)',tb)[1]
  variants=[(i,0) for i in range(32)] if label=='legacy' else [(m,k) for m in range(14) for k in range(24)]+[(m,0) for m in range(14,17)]
  for mode,offset in variants:cases.append((label,path,top,mode,offset))
 result=dict(passed=False,hashes_computed=False,reference='rtl36_candidate_r1',cases=[])
 try:
  for i,(label,tb,top,mode,offset) in enumerate(cases):
   tag=f'{label}_{mode}_{offset}'
   cmd=[shutil.which('iverilog'),'-g2005','-s',top,f'-P{top}.MODE={mode}',f'-P{top}.OFFSET={offset}','-o',str(o/(tag+'.vvp'))]
   for d in ['pl_safety/generated','pl_rs485/generated','pl_rs485/tests','pl_interface']:cmd+=['-I',str(R/d)]
   cmd+=list(map(str,sources+refs+[tb]))
   for phase,command in [('compile',cmd),('simulation',[shutil.which('vvp'),str(o/(tag+'.vvp'))])]:
    with (o/(tag+'_'+phase+'.log')).open('w') as log:proc=subprocess.run(command,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    assert proc.returncode==0,(tag,phase)
   text=(o/(tag+'_simulation.log')).read_text();cycles=int(re.search(r'CYCLE_MITER (\d+)',text)[1]);assert cycles>0
   result['cases'].append(dict(case=tag,cycles=cycles,passed=True))
   if (i+1)%24==0:print('PASS all-output safety differential',i+1,flush=True)
  result['passed']=True
 finally:(o/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print('PASS',len(result['cases']),'all-output cycle-matched safety scenarios')
if __name__=='__main__':main()
