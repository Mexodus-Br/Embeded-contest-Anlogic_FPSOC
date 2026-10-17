"""Zero-cycle DMA-stop cofactor proof and complete service-output comparison."""
import argparse,hashlib,itertools,json,re,sys,traceback
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[2]
sys.path.insert(0,str(R/'pl_motion'));from sim_tools import Simulator

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);ap.add_argument('--production',action='store_true');a=ap.parse_args();out=E/a.tag;out.mkdir(exist_ok=False);sim=Simulator(out)
 # Exhaust all independent Boolean operands, including reset, every abort,
 # idle occupancy, error state and coincident DMA/private/GP STOP sources.
 checks=0
 for bits in itertools.product([False,True],repeat=16):
  ps,pd,he,sw,fl,dr,rr,rd,ca,sd,seen,busy,sv,rst,raw,hs=bits
  abort=ps or pd or (hs and he) or sw or fl or dr or not rr or rd or ca or sd
  rx=rst and not abort and raw;occ=busy or sv
  old=(ps and not seen and occ) or sw or rx or ((fl or dr or not rr or rd) and occ)
  non_dma=ps or pd or (hs and he) or sw or fl or not rr or rd or ca or sd
  new=(ps and not seen and occ) or sw or ((fl or not rr or rd) and occ) or (occ if dr else (rst and not non_dma and raw))
  assert old==new,(bits,old,new);checks+=1
 service=R/'pl_motion/rtl/motion_service.v' if a.production else E/'cofactor_service_candidate.v';rx=R/'pl_motion/rtl/motion_stream_rx.v' if a.production else E/'cofactor_receiver_candidate.v'
 old=E/'baseline/motion_service.v';ref=out/'reference.v';ref.write_text(old.read_text().replace('module motion_service #(','module baseline_motion_service #('))
 tb=(R/'pl_motion/tests/tb_motion_service.v').read_text();start=tb.index('motion_service #(');end=tb.index('));',start)+3
 instance=tb[start:end];widths={}
 header=old.read_text().split(')(\n',1)[1].split(');',1)[0]
 for dr,w,names in re.findall(r'\b(input|output)\s+(?:wire|reg)\s*(?:\[(\d+):0\]\s*)?(.*?)(?=\binput|\boutput|$)',header,re.S):
  if dr=='output':
   for n in names.strip().rstrip(',').split(','):widths[n.strip()]=int(w)+1 if w else 1
 # Bind every original output, including formerly unconnected safety outputs.
 for n in widths:
  if not re.search(r'\.'+n+r'\(',instance):instance=instance[:-2]+',.'+n+'('+n+'));'
 declarations='\n'.join('wire '+('' if w==1 else f'[{w-1}:0] ')+n+'_ref;' for n,w in widths.items())
 declared=set(re.findall(r'\.(\w+)\(\1\)',tb[start:end]))
 for n,w in widths.items():
  if n not in declared:declarations+='\nwire '+('' if w==1 else f'[{w-1}:0] ')+n+';'
 reference=instance.replace('motion_service #(','baseline_motion_service #(').replace(')) dut(', ')) reference(')
 for n in widths:reference=reference.replace('.'+n+'('+n+')','.'+n+'('+n+'_ref)')
 lhs=','.join(widths);rhs=','.join(n+'_ref' for n in widths)
 monitor=f'''\ninteger equivalent_cycles=0;
 always @(negedge clk)if(rst_n)begin #1;
  equivalent_cycles=equivalent_cycles+1;
  if({{{lhs}}} !== {{{rhs}}}) $fatal(1,"all service outputs differ");
  if(dut.stop_kernel !== reference.stop_kernel) $fatal(1,"STOP detecting-edge differs");
 end
'''
 tb=tb[:start]+declarations+'\n'+instance+'\n'+reference+monitor+tb[end:]
 tb=tb.replace('$finish;',f'$display("PASS service cofactor outputs={len(widths)} cycles=%0d",equivalent_cycles);$finish;')
 (out/'tb.v').write_text(tb)
 sources=[p for p in (R/'pl_motion/rtl').glob('*.v') if p.name not in ['motion_service.v','motion_stream_rx.v']]+[service,rx,ref,out/'tb.v']
 result={'passed':False,'cofactor_exhaustive_checks':checks,'source_sha256':{p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
 try:
  log=sim.compile(sources,'tb_motion_service',out/'test.vvp',includes=[R/'pl_interface']);(out/'compile.log').write_text(log)
  log=sim.simulate(out/'test.vvp',timeout=180);(out/'simulate.log').write_text(log);assert 'PASS' in log
  result['passed']=True;print(log)
 except Exception:result['failure']=traceback.format_exc();raise
 finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
