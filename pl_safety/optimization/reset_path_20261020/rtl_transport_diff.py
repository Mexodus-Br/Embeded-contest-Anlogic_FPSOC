"""Original transport/CRC/FIFO/GP tests plus cycle miter for valid AXIS words."""
import argparse,ast,json,re,shutil,subprocess
from pathlib import Path
from equivalence import outputs
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);p.add_argument('--extended',action='store_true');a=p.parse_args()
 c=Path(a.candidate).resolve();out=E/a.tag;out.mkdir(exist_ok=False)
 original=(R/'pl_rs485/rtl/rs485_telemetry.v').read_text();old=out/'reference.v';old.write_text(original.replace('module rs485_telemetry','module ref_rs485_telemetry',1))
 tb=(R/'pl_rs485/tests/tb_telemetry.v').read_text()
 # The original top contains the endpoint and transport; clone the transport
 # directly from its real original wrapper bindings, and compare every output.
 wrapper=(R/'pl_rs485/rtl/rs485_telem_top.v').read_text();start=wrapper.index('rs485_telemetry #');end=wrapper.index(');',start)+2;instance=wrapper[start:end]
 module_name=re.search(r'rs485_telemetry\s*(?:#\(.*?\))?\s*(\w+)\(',instance,re.S)[1]
 clone=instance.replace('rs485_telemetry ','ref_rs485_telemetry ',1).replace(module_name+'(','reference_transport(',1)
 # Evaluate inside the top scope, so use its actual wires and parameters.
 decl=[];checks=[]
 for port,expr in re.findall(r'\.(\w+)\((\w+)\)',instance):
  if port not in outputs(original):continue
  decl.append('wire '+outputs(original)[port]+' ref_'+expr+';');clone=clone.replace(f'.{port}({expr})',f'.{port}(ref_{expr})')
  cond='m_valid && ' if port=='m_data' else ''
  checks.append(f'if({cond}{expr} !== ref_{expr})$fatal(1,"transport differential {port}");')
 extra='\n'+'\n'.join(decl)+'\n'+clone+'\ninteger miter_cycles=0;always @(posedge clk)begin #1;miter_cycles=miter_cycles+1;\n'+'\n'.join(checks)+'\nend\n'
 wrapper='`timescale 1ns/1ps\n'+wrapper.replace('endmodule',extra+'endmodule');(out/'top.v').write_text(wrapper)
 if a.extended:
  def literal(path,name):
   return next(n.value.value for n in ast.walk(ast.parse(path.read_text())) if isinstance(n,ast.Assign) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
  ready=literal(R/'pl_rs485/tests/run_telem_irq.py','ready');race=literal(R/'pl_rs485/tests/run_telem_irq.py','race')
  results=literal(R/'pl_rs485/tests/run_telem_results.py','extra')
  ring=literal(R/'pl_rs485/optimization/run_diff.py','ring');collision=literal(R/'pl_rs485/optimization/run_diff.py','collision')
  tb=tb.replace('  arm_packet(id,1,1024);',ready+'  arm_packet(id,1,1024);')
  reset='''
  for(reset_phase=0;reset_phase<60;reset_phase=reset_phase+1)begin
   @(negedge clk);#1;rst_n=0;#2;rst_n=1;m_ready=0;dma_ready=1;dma_quiescent=1;ticks(3);
   recover_to(1);emit(8'he0,8'h3e,0,1,2,4000+reset_phase);
   time_us=time_us+10010;wait(dut.transport.state==1);rd(`RT_REG_PACKET_ID,0,id);arm_packet(id,1,64);
   wait(dut.transport.state==3);repeat(reset_phase)@(negedge clk);
   @(negedge clk);#1;rst_n=0;#1;
   if(m_valid || dut.transport.count!=0)$fatal(1,"subcycle reset published retained frame/owner");
   #1;rst_n=1;ticks(3);if(m_valid)$fatal(1,"old packet resurrected after subcycle reset");
  end
  $display("PASS private frame/CRC subcycle reset phases=60");
'''
  tb=tb.replace('  $display("PASS telemetry unit',results+race+ring+reset+'  $display("PASS telemetry unit')
  tb=tb.replace('endmodule',collision+'\ninteger reset_phase;always @(negedge rst_n)blocked=0;\nendmodule')
 tb=tb.replace('$finish;','$display("PASS transport differential cycles=%0d",dut.miter_cycles);$finish;');(out/'test.v').write_text(tb)
 sources=[c/f.name if (c/f.name).is_file() else f for f in (R/'pl_rs485/rtl').glob('*.v') if f.name!='rs485_telem_top.v']+[out/'top.v',old,out/'test.v']
 result={'passed':False,'hashes_computed':False}
 try:
  for phase,cmd in [('compile',[shutil.which('iverilog'),'-g2005','-I',str(R/'pl_rs485/generated'),'-I',str(R/'pl_rs485/tests'),'-s','tb_telemetry','-o',str(out/'test.vvp'),*map(str,sources)]),('simulation',[shutil.which('vvp'),str(out/'test.vvp')])]:
   with (out/f'{phase}.log').open('w') as log:proc=subprocess.run(cmd,cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=240)
   assert proc.returncode==0,phase
  log=(out/'simulation.log').read_text();cycles=int(re.search(r'PASS transport differential cycles=(\d+)',log)[1]);assert cycles>2000
  if a.extended:assert 'PASS private frame/CRC subcycle reset phases=60' in log and 'PASS full FIFO simultaneous pop/push differential' in log
  result.update(passed=True,cycles=cycles,extended=a.extended,output=log);print(log)
 finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
