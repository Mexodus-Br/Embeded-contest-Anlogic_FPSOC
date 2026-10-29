"""Independent cycle miter for speculative executor data and async cancellation."""
import argparse,json,re,shutil,subprocess
from pathlib import Path
from equivalence import outputs
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--candidate',required=True);a=p.parse_args()
    assert re.fullmatch('[A-Za-z0-9_-]+',a.tag)
    out=HERE/a.tag;out.mkdir(exist_ok=False)
    original=subprocess.check_output(['git','show','07745a8:pl_motion/rtl/motion_executor.v'],cwd=ROOT).decode()
    (out/'reference.v').write_text(original.replace('module motion_executor','module ref_motion_executor',1))
    ports=outputs(original)
    declarations='\n'.join('wire '+w+' '+n+','+n+'_ref;' for n,w in ports.items())
    inputs=['clk','rst_n','rebase_req','rebase_mask','rebase_position','enable_req','enable_mask','disable_req','disable_mask','stop_req','fault','clear_fault','plan_valid','plan_data','home_owner','home_enable','home_reference','home_complete','home_run','home_direction','home_period','home_reference_position','safety_invalidate']
    parameters='''#(.HOME_SUPPORT(1),.STEP_HIGH_CYCLES({4{64'd3}}),.STEP_LOW_CYCLES({4{64'd2}}),
 .DIR_SETUP_CYCLES({4{64'd4}}),.DIR_HOLD_CYCLES({4{64'd7}}),.EN_SETUP_CYCLES({4{64'd5}}),.MAX_STEP_HZ({4{64'd10000000}}))'''
    instances='\n'.join(mod+' '+parameters+' '+inst+'('+','.join('.'+n+'('+n+')' for n in inputs)+','+','.join('.'+n+'('+n+suffix+')' for n in ports)+');' for mod,inst,suffix in [('motion_executor','dut',''),('ref_motion_executor','golden','_ref')])
    compare='\n'.join('if('+n+' !== '+n+'_ref)$fatal(1,"executor stress mismatch '+n+' phase=%0d cycle=%0d",phase,k);' for n in ports)
    tb='''`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,rebase_req=0,enable_req=0,disable_req=0,stop_req=0,clear_fault=0,plan_valid=0;
reg [3:0] rebase_mask=15,enable_mask=15,disable_mask=15,fault=0,safety_invalidate=0;
reg [255:0] rebase_position=0;reg [1196:0] plan_data=0;
reg home_owner=0,home_enable=0,home_reference=0,home_complete=0;
reg [2:0] home_run=0,home_direction=0;
reg [191:0] home_period={3{64'd13}},home_reference_position=0;
integer phase=0,k=0,seed=32'h517ab2,checks=0,starts=0,pulses=0,home_pulses=0,cancels=0;
reg [3:0] moving,positive;reg [255:0] counts;
'''+declarations+'\n'+instances+'''
always @(posedge clk)begin #1;
'''+compare+'''
 checks=checks+1;if(point_start)starts=starts+1;
 if(|pulse_event)begin pulses=pulses+1;if(home_owner)home_pulses=home_pulses+1;end
end
initial begin
 repeat(2)@(negedge clk);
 for(phase=0;phase<1200;phase=phase+1)begin
  rst_n=0;rebase_req=0;enable_req=0;disable_req=0;stop_req=0;clear_fault=0;plan_valid=0;
  fault=0;safety_invalidate=0;home_owner=0;home_enable=0;home_reference=0;home_complete=0;home_run=0;
  // Alternate held reset and a pulse entirely between clock edges.
  if(phase%2==0)begin #1;rst_n=1;end else begin @(negedge clk);rst_n=1;end
  rebase_position=phase%17==0 ? {4{64'h7ffffffffffffffe}}:phase%19==0 ? {4{64'h8000000000000001}}:256'd0;
  for(k=0;k<160;k=k+1)begin
   rebase_req=(k==1);enable_req=(k==3);disable_req=0;stop_req=0;fault=0;clear_fault=0;
   home_reference=0;home_complete=0;safety_invalidate=0;
   // Changing unaccepted payload on every idle cycle must never become RUN.
   positive=$random(seed);moving=$random(seed);
   counts={moving[3]?64'd4:64'd0,moving[2]?64'd3:64'd0,moving[1]?64'd2:64'd0,moving[0]?64'd1:64'd0};
   plan_data={position,256'd0,counts,positive,moving,64'd4,64'd13,64'd100,64'd20,64'd0,64'd1,32'd0,1'b0,4'd15};
   plan_valid=(k==12 || k>112) && (phase%7!=0 || k%3==0);
   if(phase%5==0 && k>=10)begin
    home_owner=1;home_enable=1;home_run=7;home_direction=phase;
    home_reference=(k==11);home_complete=(k==14);home_reference_position=rebase_position[191:0];
   end
   if(phase%6==1 && k==13+phase%95)begin stop_req=1;cancels=cancels+1;end
   if(phase%6==2 && k==13+phase%95)begin fault=1;cancels=cancels+1;end
   if(phase%6==3 && k==13+phase%95)begin disable_req=1;cancels=cancels+1;end
   if(phase%6==4 && k==13+phase%95)safety_invalidate=15;
   @(posedge clk);#2;
   if(phase%11==0 && k==50)begin rst_n=0;#1;rst_n=1;end
   @(negedge clk);
  end
 end
 if(starts<100 || pulses<100 || home_pulses<100 || cancels<100)$fatal(1,"insufficient coverage");
 $display("PASS executor stress checks=%0d starts=%0d pulses=%0d home_pulses=%0d cancels=%0d",checks,starts,pulses,home_pulses,cancels);$finish;
end
initial begin #3000000;$fatal(1,"stress timeout");end
endmodule
'''
    (out/'tb.v').write_text(tb)
    result={'passed':False,'hashes_computed':False,'baseline_commit':'07745a8','outputs_compared':list(ports)}
    try:
        for name,cmd in [('compile',[shutil.which('iverilog'),'-g2005','-s','tb','-o',str(out/'test.vvp'),str(Path(a.candidate).resolve()),str(out/'reference.v'),str(out/'tb.v')]),('simulation',[shutil.which('vvp'),str(out/'test.vvp')])]:
            with (out/(name+'.log')).open('w') as log:proc=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=240)
            assert proc.returncode==0,(name,proc.returncode)
        text=(out/'simulation.log').read_text();assert 'PASS executor stress' in text
        result.update(passed=True,counters={k:int(v) for k,v in re.findall(r'(checks|starts|pulses|home_pulses|cancels)=(\d+)',text)})
        print(result)
    finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
