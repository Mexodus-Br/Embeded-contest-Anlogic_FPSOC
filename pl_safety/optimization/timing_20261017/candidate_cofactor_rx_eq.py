"""Local exploratory candidate; production source is unchanged."""
"""Cycle equivalence against the original receiver, including modulo-count edges."""
import hashlib,json,subprocess,sys,traceback
from pathlib import Path
R=Path(__file__).resolve().parents[3];D=R/'pl_safety'
sys.path.insert(0,str(R/'pl_motion'))
from sim_tools import Simulator

def main():
 out=D/'evidence'/sys.argv[1];out.mkdir(exist_ok=False);sim=Simulator(out)
 source=R/'pl_safety/optimization/timing_20261017/cofactor_receiver_candidate.v'
 baseline=subprocess.check_output(['git','show','c9f2e05:pl_motion/rtl/motion_stream_rx.v'],cwd=R)
 (out/'baseline.v').write_bytes(baseline.replace(b'module motion_stream_rx(',b'module baseline_rx('))
 tb=(R/'pl_motion/tests/tb_motion_stream_rx.v').read_text()
 begin=tb.index('motion_stream_rx dut(');end=tb.index('));',begin)+3
 instance=tb[begin:end].replace('motion_stream_rx dut','baseline_rx reference')
 widths={'arm_ready':1,'packet_busy':1,'partial_empty':1,'s_ready':1,'point_valid':1,'error':1,'packet_closed':1,'point_session':64,'duration_tick':64,'point_sequence':32,'packet_count':32,'point_end':1,'point_mask':4,'point_target':256}
 declarations=[]
 for name,width in widths.items():
  declarations.append('wire '+('' if width==1 else f'[{width-1}:0] ')+name+'_ref;')
  instance=instance.replace('.'+name+'('+name+')','.'+name+'('+name+'_ref)')
 lhs=','.join(widths);rhs=','.join(n+'_ref' for n in widths)
 compare='\n'.join(declarations)+'\n'+instance+f'''
integer equivalence_checks=0;
always @(negedge clk)if(rst_n)begin
 #1;
 equivalence_checks=equivalence_checks+1;
 if({{{lhs}}} !== {{{rhs}}}) $fatal(1,"receiver cycle equivalence failed");
end
'''
 tb=tb[:end]+compare+tb[end:]
 # Existing protocol oracle covers valid records, backpressure, all 72 byte
 # corruptions and abort phases. Inject unreachable-in-practice counter edges
 # solely to check the 32-bit modulo identity without billions of records.
 extra='''
 for(offset=0;offset<5;offset=offset+1)begin
  for(j=0;j<6;j=j+1)begin
   case(offset)
    0:begin_packet(0);
    1:begin_packet(1);
    2:begin_packet(2);
    3:begin_packet(32'h80000000);
    4:begin_packet(32'hffffffff);
   endcase
   case(j/2)
    0:begin dut.completed=0;reference.completed=0;end
    1:begin dut.completed=arm_count-1;reference.completed=arm_count-1;end
    2:begin dut.completed=32'hffffffff;reference.completed=32'hffffffff;end
   endcase
   make_record(0);
   for(i=0;i<9;i=i+1)beat(i,i==8 && ((reference.completed+32'd1==arm_count) ^ (j%2)));
   repeat(20)@(negedge clk);
   @(negedge clk);abort=1;@(negedge clk);abort=0;
  end
 end
 $display("PASS receiver equivalence cycles=%0d boundary_cases=30",equivalence_checks);
'''
 tb=tb.replace(' $display("PASS motion_stream_rx',extra+' $display("PASS motion_stream_rx')
 (out/'tb.v').write_text(tb)
 result={'passed':False,'baseline_commit':'c9f2e05','baseline_sha256':hashlib.sha256(baseline).hexdigest(),'source_sha256':{source.relative_to(R).as_posix():hashlib.sha256(source.read_bytes()).hexdigest()}}
 try:
  target=out/'equivalence.vvp'
  (out/'compile.log').write_text(sim.compile([source,out/'baseline.v',out/'tb.v'],'tb_motion_stream_rx',target,includes=[R/'pl_interface']))
  log=sim.simulate(target,timeout=120);(out/'run.log').write_text(log)
  assert 'PASS receiver equivalence' in log
  result['passed']=True;print(log)
 except Exception:result['failure']=traceback.format_exc();raise
 finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
