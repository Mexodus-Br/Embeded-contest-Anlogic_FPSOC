"""Two self-checking miters: complete monitor outputs and real EMIT decode.

Isolated candidate sources only. No hashes and no production mutations.
"""
import argparse,json,re,shutil,subprocess,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
SRC=HERE/'sources_r2'
OUT=HERE/'unit_r2'
def change(s,a,b):
 assert s.count(a)==1,a
 return s.replace(a,b)
def run(name,top,sources):
 command=[shutil.which('iverilog'),'-g2005',*sum((['-I',str(ROOT/x)] for x in
  ['pl_safety/generated','pl_rs485/generated','pl_rs485/tests']),[]),'-s',top,'-o',str(OUT/(name+'.vvp')),*map(str,sources)]
 for stage,argv in [('compile',command),('simulation',[shutil.which('vvp'),str(OUT/(name+'.vvp'))])]:
  with (OUT/(name+'_'+stage+'.log')).open('w') as log:
   p=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,timeout=120)
  assert p.returncode==0,(name,stage)
 text=(OUT/(name+'_simulation.log')).read_text();assert 'PASS' in text
 print(text.strip(),flush=True)
 return {'passed':True,'output':text.strip()}
def main():
 global OUT
 parser=argparse.ArgumentParser();parser.add_argument('--tag',default='unit_r3');args=parser.parse_args()
 assert re.fullmatch('[A-Za-z0-9_-]+',args.tag)
 OUT=HERE/args.tag
 OUT.mkdir(exist_ok=False)
 result={'passed':False,'hashes_computed':False,'production_modified':False}
 try:
  baseline=HERE/'before'
  # Frozen candidate13 reference remains independent of later DUT edits.
  reference=(baseline/'pl_safety/rtl/safety_interlock.v').read_text()
  (OUT/'reference.v').write_text(reference)
  tb=(ROOT/'pl_safety/optimization/interlock_candidate14/probe_r1/tb.v').read_text()
  tb=change(tb,'safety_interlock_lookahead #(.LOOKAHEAD_EPOCH(1)) cached(',
    'safety_interlock15 #(.LOOKAHEAD_EPOCH(1),.FEEDBACK_PREDECODE(1)) cached(.feedback_predecoded(decoded),')
  tb=change(tb,'wire [623:0] expected,actual;', '''wire [623:0] expected,actual;
wire [5:0] ref_task;wire formed,valid,known;wire [63:0] val;
wire [31:0] carry;wire [15:0] word;wire [7:0] enumeration;
rs485_light_parse parse(raw,ref_task,formed,valid,known,val,carry,word,enumeration);
wire [2:0] axis={ref_task==14,ref_task==9,ref_task==4} & {3{formed && valid && known}};
wire [5:0] decoded={axis & {3{enumeration==1}},axis};''')
  (OUT/'tb_core.v').write_text(tb)
  c=(SRC/'pl_safety/rtl/safety_interlock.v').read_text().replace('module safety_interlock #','module safety_interlock15 #')
  (OUT/'core.v').write_text(c)
  result['monitor']=run('core','tb_epoch_cache',[OUT/'reference.v',OUT/'core.v',ROOT/'pl_rs485/rtl/rs485_light_parse.v',OUT/'tb_core.v'])
  old=(baseline/'pl_rs485/rtl/rs485_transaction.v').read_text().replace('module rs485_transaction #','module reference_transaction #')
  (OUT/'reference_transaction.v').write_text(old)
  tb=r'''`timescale 1ns/1ps
module tb_source_decode;
`include "rs485_defs.vh"
reg clk=0;always #5 clk=~clk;
reg rst_n=0;reg [63:0] now_us=0;
wire [255:0] raw,old_raw;wire [5:0] decoded;wire push,old_push;
wire [31:0] accepted,errors,ignored,old_accepted,old_errors,old_ignored;
wire tx,de,active,done,blocked,ready,old_tx,old_de,old_active,old_done,old_blocked,old_ready;
wire [7:0] status,old_status;
rs485_transaction #(.INTERLOCK_PREDECODE(1),.PROTECTION_ADDRS(`RS_SLAVE_ADDRS)) dut(
.clk(clk),.rst_n(rst_n),.time_us(now_us),.rx(1'b1),.request_valid(1'b0),.request_ready(ready),
.request_address(8'd0),.request_query(3'd0),.request_sequence(32'd0),.tx(tx),.de(de),.active(active),
.done(done),.result(status),.bus_blocked(blocked),.push(push),.push_data(raw),
.accepted(accepted),.errors(errors),.ignored_rx(ignored),.protection_decoded(decoded));
reference_transaction reference(.clk(clk),.rst_n(rst_n),.time_us(now_us),.rx(1'b1),.request_valid(1'b0),.request_ready(old_ready),
.request_address(8'd0),.request_query(3'd0),.request_sequence(32'd0),.tx(old_tx),.de(old_de),.active(old_active),
.done(old_done),.result(old_status),.bus_blocked(old_blocked),.push(old_push),.push_data(old_raw),
.accepted(old_accepted),.errors(old_errors),.ignored_rx(old_ignored));
wire [5:0] task_id;wire formed,valid,known;wire [63:0] value;wire [31:0] carry;
wire [15:0] word;wire [7:0] enumeration;
rs485_light_parse parse(raw,task_id,formed,valid,known,value,carry,word,enumeration);
wire [2:0] axes={task_id==14,task_id==9,task_id==4} & {3{formed && valid && known}};
wire [5:0] expected={axes & {3{enumeration==1}},axes};
integer checks=0,a,e,i,j;
task emit;
input [7:0] address,command,st;input [3:0] length;input [47:0] payload;
begin
 @(negedge clk);
 // Inductive source-state enumeration, confined to this testbench.
 dut.state=7;reference.state=7;
 dut.address=address;reference.address=address;dut.command=command;reference.command=command;
 dut.status=st;reference.status=st;dut.length=length;reference.length=length;
 dut.payload=payload;reference.payload=payload;
 @(posedge clk);#1;checks=checks+1;
 if(!push || !old_push || raw!==old_raw || decoded!==expected)
  $fatal(1,"same-edge predecode/raw mismatch raw=%h actual=%h expected=%h",raw,decoded,expected);
 if({tx,de,active,done,status,blocked,ready,accepted,errors,ignored} !==
    {old_tx,old_de,old_active,old_done,old_status,old_blocked,old_ready,old_accepted,old_errors,old_ignored})
  $fatal(1,"original transaction outputs changed");
 @(posedge clk);#1;
 if(push || old_push)$fatal(1,"commit pulse extended");
end endtask
initial begin
 repeat(3)@(negedge clk);rst_n=1;
 for(a=0;a<256;a=a+1)for(e=0;e<256;e=e+1)emit(a,8'h3e,0,1,e);
 for(a=0;a<3;a=a+1)begin
  for(i=0;i<256;i=i+1)begin emit(8'he0+a,i,0,1,1);emit(8'he0+a,8'h3e,i,1,1);end
  for(i=0;i<16;i=i+1)emit(8'he0+a,8'h3e,0,i,1);
  for(i=8;i<48;i=i+1)begin emit(8'he0+a,8'h3e,0,1,48'd1|(48'd1<<i));emit(8'he0+a,8'h3e,0,1,48'd2|(48'd1<<i));end
 end
 $display("PASS source_predecode_miter checks=%0d actual EMIT/raw alignment",checks);$finish;
end
initial begin #5000000;$fatal(1,"source miter timeout");end
endmodule
'''
  (OUT/'tb_source.v').write_text(tb)
  result['source']=run('source','tb_source_decode',[OUT/'reference_transaction.v',SRC/'pl_rs485/rtl/rs485_transaction.v',
    ROOT/'pl_rs485/rtl/uart_tx.v',ROOT/'pl_rs485/rtl/uart_rx.v',ROOT/'pl_rs485/rtl/rs485_light_parse.v',OUT/'tb_source.v'])
  result['passed']=True
 except Exception:
  result['failure']=traceback.format_exc();raise
 finally:(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
