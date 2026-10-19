"""Preparation only: same-edge full-u32 lookahead equality versus current RTL.

Does not modify production RTL or implement the real collector's predictor.
The synchronous source model may jump to ANY u32 value, including wraps. The
only premise is that its complete next values are supplied before the edge.
"""
import json,re,shutil,subprocess,traceback
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent/'probe_r1'

def main():
 OUT.mkdir(exist_ok=False)
 result={'passed':False,'hashes_computed':False,'scope':'core algebra only; real-source predictor not implemented'}
 try:
  original=(ROOT/'pl_safety/rtl/safety_interlock.v').read_text()
  source=original
  replacements=[
   ('module safety_interlock(', 'module safety_interlock_lookahead #(parameter LOOKAHEAD_EPOCH=0)('),
   (' input wire poll_stop_commit\n', ' input wire poll_stop_commit,\n input wire [31:0] next_generation,next_revision\n'),
   (' reg previous_run,round_valid;', ' reg previous_run,round_valid;reg epoch_match_q;'),
   (' wire restart=poll_run && (!previous_run || config_change || collector_reset ||\n   collector_generation!=round_generation || collector_revision!=round_revision || config_apply);',
    ''' wire epoch_match=LOOKAHEAD_EPOCH ? epoch_match_q :
   collector_generation==round_generation && collector_revision==round_revision;
 wire restart=poll_run && (!previous_run || config_change || collector_reset || !epoch_match || config_apply);
 wire [31:0] next_round_generation=restart ? collector_generation:round_generation;
 wire [31:0] next_round_revision=restart ? collector_revision:round_revision;'''),
   ('   feedback_generation==round_generation && feedback_revision==round_revision &&',
    '''   (LOOKAHEAD_EPOCH ? (epoch_match_q && feedback_generation==collector_generation &&
    feedback_revision==collector_revision) :
    (feedback_generation==round_generation && feedback_revision==round_revision)) &&'''),
   ('   previous_run<=0;round_valid<=0;', '   epoch_match_q<=1;previous_run<=0;round_valid<=0;'),
   ('   previous_run<=poll_run;', '''   previous_run<=poll_run;
   epoch_match_q<=next_generation==next_round_generation && next_revision==next_round_revision;''')]
  for old,new in replacements:
   assert source.count(old)==1,old
   source=source.replace(old,new)
  (OUT/'monitor.v').write_text(source)
  (OUT/'reference.v').write_text(original)
  outputs=[('owner_open_ok',1),('owner_close_ok',1),('heartbeat_ok',1),('clear_ok',1),
   ('owner_id',64),('last_sequence',64),('owner_active',1),('heartbeat_qualified',1),
   ('active_axes',3),('feedback_seen',3),('feedback_timeout_us',32),('watchdog_timeout_us',32),
   ('feedback_qualified',1),('permit',1),('detect',1),('disable_request',1),
   ('detected_causes',32),('causes',32),('first_cause',32),('first_time',64),('last_times',256)]
  common='''.clk(clk),.rst_n(rst_n),.time_us(time_us),.poll_run(poll_run),.poll_stop_commit(poll_stop_commit),
 .collector_reset(collector_reset),.config_change(config_change),.collector_generation(generation),.collector_revision(revision),
 .collector_periods({32'd1000000,128'd0}),.collector_mask(5'd16),.feedback_commit(feedback_commit),.feedback_raw(raw),
 .feedback_generation(record_generation),.feedback_revision(record_revision),.config_apply(config_apply),.config_axes(config_axes),
 .config_feedback_us(fb_limit),.config_watchdog_us(wd_limit),.idle_off(idle_off),.owner_open(owner_open),.owner_close(owner_close),
 .heartbeat_commit(heartbeat_commit),.heartbeat_owner(heartbeat_owner),.heartbeat_sequence(heartbeat_sequence),.clear_request(clear_request)'''
  instances=[]
  for name,vector in [('safety_interlock','expected'),('safety_interlock_lookahead #(.LOOKAHEAD_EPOCH(1))','actual')]:
   connections=[common];bit=0
   for port,width in outputs:
    connections.append(f'.{port}({vector}[{bit}+:{width}])');bit+=width
   assert bit==624
   if vector=='actual':connections+=['.next_generation(next_generation)','.next_revision(next_revision)']
   instances.append(name+' '+('reference' if vector=='expected' else 'cached')+'('+',\n'.join(connections)+');')
  tb=r'''`timescale 1ns/1ps
module tb_epoch_cache;
reg clk=0;always #5 clk=~clk;
reg rst_n=0;reg [63:0] time_us=64'hfffffffffff00000;
reg poll_run=0,poll_stop_commit=0,collector_reset=0,config_change=0,config_apply=0;
reg [31:0] generation=0,revision=0,next_generation=0,next_revision=0;
always @(posedge clk or negedge rst_n)
 if(!rst_n)begin generation<=0;revision<=0;end
 else begin generation<=next_generation;revision<=next_revision;end
reg stale_generation=0,stale_revision=0;
wire [31:0] record_generation=stale_generation ? generation^32'h01010101:generation;
wire [31:0] record_revision=stale_revision ? revision^32'h80808080:revision;
reg feedback_commit=0;reg [255:0] raw=0;reg [2:0] config_axes=7;
reg [31:0] fb_limit=2000000,wd_limit=2000000;
reg idle_off=1,owner_open=0,owner_close=0,heartbeat_commit=0,clear_request=0;
reg [63:0] heartbeat_owner=0,heartbeat_sequence=0;
wire [623:0] expected,actual;
@INSTANCES@
integer i,comparisons=0,seed=32'h1e0c2026;reg [31:0] random_word;
task compare;begin
 comparisons=comparisons+1;
 if(expected!==actual)$fatal(1,"core output mismatch cycle=%0d count=%0d expected=%h actual=%h",i,comparisons,expected,actual);
 if({reference.round_start,reference.round_generation,reference.round_revision,reference.round_valid,reference.previous_run} !==
    {cached.round_start,cached.round_generation,cached.round_revision,cached.round_valid,cached.previous_run})
  $fatal(1,"round capture boundary mismatch cycle=%0d",i);
 if(cached.epoch_match_q!==((generation==cached.round_generation) && (revision==cached.round_revision)))
  $fatal(1,"cached complete-u32 equality differs on current edge cycle=%0d",i);
end endtask
initial begin
 repeat(3)@(negedge clk);rst_n=1;
 for(i=0;i<8192;i=i+1)begin
  @(negedge clk);random_word=$random(seed);
  next_generation=generation;next_revision=revision;
  if(i%23==0)next_generation=$random(seed);
  if(i%17==0)next_revision=$random(seed);
  if(i%256==0)next_generation=32'hffffffff;
  if(i%256==1)next_generation=0;
  if(i%127==0)begin next_generation=generation+1'b1;next_revision=0;end
  poll_run=i%128<96;poll_stop_commit=i%97==0;
  collector_reset=i%127==0;config_change=i%61==0;config_apply=i%83==0;
  config_axes=(i%3==0)?7:(1<<(i%3));fb_limit=1000000+(i%3)*1000000;wd_limit=3000000-(i%3)*1000000;
  time_us=time_us+((random_word[3:0]+1)*100000);
  idle_off=i%5!=0;owner_open=i%16==8;owner_close=i%13==0;clear_request=i%7==0;
  heartbeat_commit=i%4==0;heartbeat_owner=expected[4+:64]^(i%19==0 ? 64'd1:64'd0);heartbeat_sequence=i+1;
  stale_generation=0;stale_revision=0;
  if(generation==reference.round_generation && revision==reference.round_revision &&
     next_generation==generation && next_revision==revision)begin
   stale_generation=i%11==0;stale_revision=i%13==0;
  end
  raw=0;raw[255:248]=i%37==0 ? 0:1;raw[247:240]=8'he0+(i%3);
  raw[239:232]=i%11==0 ? 8'h3a:8'h3e;raw[215:208]=i%19==0 ? 2:1;
  raw[231:224]=i%17==0 ? 1:0;raw[175:112]=time_us;raw[111:48]=time_us;
  raw[7:0]=i%41==0 ? 1:i%29==0 ? 255:2;
  if(i%31==0)raw[8+(i%40)]=1;
  feedback_commit=i%4!=0;
  #1;compare;
  @(posedge clk);#1;compare;
 end
 $display("PASS epoch_cache_miter cycles=%0d comparisons=%0d full-u32/no-edge-delay",i,comparisons);$finish;
end
initial begin #1000000;$fatal(1,"epoch miter timeout");end
endmodule
'''.replace('@INSTANCES@','\n'.join(instances))
  (OUT/'tb.v').write_text(tb)
  commands=[[shutil.which('iverilog'),'-g2005','-I',str(ROOT/'pl_safety/generated'),'-I',str(ROOT/'pl_rs485/generated'),
    '-s','tb_epoch_cache','-o',str(OUT/'test.vvp'),str(OUT/'reference.v'),str(OUT/'monitor.v'),str(OUT/'tb.v')],
   [shutil.which('vvp'),str(OUT/'test.vvp')]]
  for label,command in zip(['compile','simulation'],commands):
   with (OUT/(label+'.log')).open('w') as log:p=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=90)
   assert p.returncode==0,label
  text=(OUT/'simulation.log').read_text();assert 'PASS epoch_cache_miter' in text
  result.update(passed=True,cycles=8192,pre_and_post_edge_comparisons=16384,complete_u32_identity_preserved=True)
  print(text.strip())
 except Exception:
  result['failure']=traceback.format_exc();raise
 finally:(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
