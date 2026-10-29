"""Receiver cycle miter, including sub-cycle reset at every partial/CRC phase."""
import argparse,json,re,shutil,subprocess
from pathlib import Path
from equivalence import outputs
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);a=p.parse_args()
 out=E/a.tag;out.mkdir(exist_ok=False);candidate=Path(a.candidate).resolve()
 original=(R/'pl_motion/rtl/motion_stream_rx.v').read_text();(out/'reference.v').write_text(original.replace('module motion_stream_rx','module ref_motion_stream_rx',1))
 tb=(R/'pl_motion/tests/tb_motion_stream_rx.v').read_text();start=tb.index('motion_stream_rx dut(');end=tb.index(');',start)+2
 inst=tb[start:end];clone=inst.replace('motion_stream_rx dut(','ref_motion_stream_rx golden(');decl=[];checks=[]
 payload={'point_session','duration_tick','point_sequence','point_end','point_mask','point_target'}
 for port,expr in re.findall(r'\.(\w+)\((\w+)\)',inst):
  if port not in outputs(original):continue
  decl.append('wire '+outputs(original)[port]+' ref_'+expr+';');clone=clone.replace(f'.{port}({expr})',f'.{port}(ref_{expr})')
  checks.append(f'if({"point_valid && " if port in payload else ""}{expr} !== ref_{expr})$fatal(1,"RX miter mismatch {port}");')
 observe='\n'+'\n'.join(decl)+'\n'+clone+'\ninteger miter_cycles=0;always @(posedge clk)begin #1;miter_cycles=miter_cycles+1;\n'+'\n'.join(checks)+'\nend\n'
 # The original bench only samples resets at posedges. Its saved backpressure
 # ownership must also be invalidated for the newly added between-edge reset.
 observe+='always @(negedge rst_n)blocked<=0;\n'
 tb=tb[:end]+observe+tb[end:]
 extra='''
 // Leave old nonzero records in storage; invalidate with a reset shorter
 // than one clock, then prove a fresh nine-beat record overwrites all fields.
 for(offset=0;offset<96;offset=offset+1)begin
  allow_points=0;begin_packet(1);make_record(0);
  for(i=0;i<offset%10;i=i+1)beat(i,i==8);
  repeat(offset%17)@(negedge clk);
  @(negedge clk);#1;rst_n=0;#1;
  check(!point_valid && !packet_busy && !error,"sub-cycle reset revokes old owner immediately");
  #1;rst_n=1;s_valid=0;repeat(2)@(negedge clk);
  check(arm_ready && partial_empty && !point_valid,"old partial/held record cannot revive");
  outputs=0;expected_seq=0;input_beats=0;begin_packet(1);make_record(0);
  for(i=0;i<9;i=i+1)beat(i,i==8);
  repeat(30)@(negedge clk);check(point_valid,"fresh complete record held");
  repeat(41)@(negedge clk);allow_points=1;wait(!packet_busy);@(negedge clk);
  check(outputs==1,"one fresh record, no old owner resurrection");
 end
 $display("PASS RX short reset differential epochs=96 cycles=%0d",miter_cycles);
'''
 tb=tb.replace(' $display("PASS motion_stream_rx',extra+' $display("PASS motion_stream_rx')
 (out/'test.v').write_text(tb);result={'passed':False,'hashes_computed':False}
 try:
  for phase,cmd in [('compile',[shutil.which('iverilog'),'-g2005','-I',str(R/'pl_interface'),'-s','tb_motion_stream_rx','-o',str(out/'test.vvp'),str(candidate/'motion_stream_rx.v'),str(out/'reference.v'),str(out/'test.v')]),('simulation',[shutil.which('vvp'),str(out/'test.vvp')])]:
   with (out/f'{phase}.log').open('w') as log:proc=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=240)
   assert proc.returncode==0,phase
  text=(out/'simulation.log').read_text();assert 'PASS RX short reset differential epochs=96' in text
  result.update(passed=True,epochs=96,output=text);print(text)
 finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
