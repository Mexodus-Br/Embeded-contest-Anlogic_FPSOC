"""Legacy word oracle plus latency-normalized full endpoint/transport differential."""
import argparse,hashlib,json,os,re,shutil,subprocess
from pathlib import Path
E=Path(__file__).resolve().parent;O=E.parent;R=E.parents[2]
def delayed_reference(old):
 # This adapter samples the LEGACY asynchronous data at its original AR edge;
 # only publication is delayed. It does not reuse the candidate RAM or decoder.
 old=old.replace('module rs485_telem_regs','module rs485_telem_regs_reference',1)
 old=old.replace(' reg ah,wh,waiting;', ' reg reference_pending;reg [31:0] reference_data;\n reg ah,wh,waiting;')
 old=old.replace('assign s_arready=rst_n && !s_rvalid;', 'assign s_arready=rst_n && !s_rvalid && !reference_pending;')
 old=old.replace('ah<=0;wh<=0;waiting<=0;', 'reference_pending<=0;reference_data<=0;ah<=0;wh<=0;waiting<=0;')
 old=old.replace('if(s_rvalid && s_rready) s_rvalid<=0;', 'if(s_rvalid && s_rready) s_rvalid<=0;\n   if(reference_pending) begin reference_pending<=0;s_rdata<=reference_data;s_rresp<=0;s_rvalid<=1;end')
 marker='s_rdata<=v;s_rresp<=response;s_rvalid<=1;if(err!=0) access_error<=err;'
 assert marker in old
 old=old.replace(marker,marker+'''\n    if(s_araddr[32:12]==BASE[32:12] && s_araddr[1:0]==0 && s_araddr[11:0]>=`RT_ROW_BASE && s_araddr[11:0]<`RT_ROW_BASE+`RT_ROWS*`RT_ROW_STRIDE && snap_valid) begin
     reference_pending<=1;reference_data<=v;s_rvalid<=0;
    end''')
 return old
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);ap.add_argument('--slaves',type=int,default=3);a=ap.parse_args()
 D=E/('ram_'+a.tag);D.mkdir(exist_ok=False)
 oldcache=(O/'baseline/rs485_latest_cache_baseline.v').read_text(encoding='utf-8')
 (D/'cache_baseline.v').write_text(oldcache.replace('module rs485_latest_cache','module rs485_latest_cache_baseline',1),encoding='utf-8')
 tb=(O/'tb_cache_diff.v').read_text(encoding='utf-8')
 tb=tb.replace('rs485_latest_cache dut(',f'rs485_latest_cache #(.SLAVE_COUNT({a.slaves})) dut(')
 tb=tb.replace('rs485_latest_cache_baseline reference_cache(',f'rs485_latest_cache_baseline #(.SLAVE_COUNT({a.slaves})) reference_cache(')
 tb=tb.replace(' integer checks=', ' reg [31:0] expected_pipe;always @(posedge clk) expected_pipe<=expected;\n integer checks=')
 tb=tb.replace('snapshot_word=w;#1;', 'snapshot_word=w;@(posedge clk);#1;')
 tb=tb.replace('if(actual!==expected)', 'if(actual!==expected_pipe)').replace('w,actual,expected);','w,actual,expected_pipe);')
 tb=tb.replace('checks=checks+1;\n   end', 'checks=checks+1;@(negedge clk);\n   end')
 extra='''
  // Every clock may update and replace a snapshot, while the RAM reads the OLD
  // snapshot. Vary row/config/time/gen; hammer one row to force slot reuse.
  for(k=0;k<12000;k=k+1) begin
   snapshot_word=$random(seed);time_us=time_us+1;active_mask=$random(seed);
   make_event((k%7==0)?1:0,k%5,k%8);snapshot_capture=(k%3!=0);
   if(k%101==0) collector_generation=collector_generation+1;
   if(k%127==0) active_period_us={$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
   @(posedge clk);#1;
   if(actual!==expected_pipe || errors!==ref_errors) $fatal(1,"continuous read/capture/update collision k=%0d got=%h expected=%h",k,actual,expected_pipe);
   checks=checks+1;@(negedge clk);
  end
  event_valid=0;snapshot_capture=0;capture;
 '''
 tb=tb.replace('  $display("PASS cache differential',extra+'  $display("PASS cache differential')
 (D/'tb_cache_diff.v').write_text(tb,encoding='utf-8')
 iv=shutil.which('iverilog');vvp=shutil.which('vvp');env=os.environ.copy();system=Path(os.environ['SystemRoot'])
 env['PATH']=os.pathsep.join([str(Path(iv).parent),str(system/'System32'),str(system)]);env['TMP']=env['TEMP']=str(D)
 sources=list((R/'pl_rs485/rtl').glob('*.v'))+[D/'cache_baseline.v',D/'tb_cache_diff.v']
 for label,cmd in [('compile',[iv,'-g2005','-I',str(R/'pl_rs485/generated'),'-s','tb_cache_diff','-o',str(D/'cache.vvp'),*map(str,sources)]),('simulation',[vvp,str(D/'cache.vvp')])]:
  p=subprocess.run(cmd,cwd=D,env=env,capture_output=True,text=True,timeout=180);(D/('cache_'+label+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8');assert p.returncode==0,(label,p.stdout+p.stderr)
 assert 'PASS cache differential' in p.stdout;print(p.stdout,flush=True)
 # Reuse all existing full-ring/CRC/IRQ/result/backpressure scenarios and the
 # archived original cache/FIFO. Only the declared row-read latency is adapted.
 source=(O/'run_diff.py').read_text(encoding='utf-8')
 corner='''
  // Commit a replacement snapshot, consume an AR for the OLD snapshot and
  // update the same raw record on one edge. Hold R while updating repeatedly.
  wr(`RT_REG_SNAP_REQ_ID,10000,15,0);
  @(negedge clk);s_awaddr={1'b0,`RT_BASE}+`RT_REG_SNAP_SUBMIT;s_awvalid=1;
  s_wdata=1;s_wstrb=15;s_wvalid=1;
  @(posedge clk);@(negedge clk);s_awvalid=0;s_wvalid=0;
  s_araddr={1'b0,`RT_BASE}+`RT_ROW_BASE+`RT_ROW_RESULT_RAW;s_arvalid=1;
  event_raw={8'd1,8'he0,8'h30,8'd0,8'd1,8'd6,32'd12345,time_us-64'd10,time_us,48'hfeed12345678};event_valid=1;
  @(posedge clk);@(negedge clk);s_arvalid=0;
  if(s_rvalid || s_arready) $fatal(1,"RAM AR was acknowledged before data registration");
  wait(s_rvalid);v=s_rdata;ticks(40);
  if(s_rdata!==v) $fatal(1,"replacement snapshot changed stalled R");
  s_rready=1;s_bready=1;@(posedge clk);@(negedge clk);s_rready=0;s_bready=0;event_valid=0;
  checks=checks+1;
  // Generation invalidation AFTER AR must not alter the accepted response.
  @(negedge clk);s_araddr={1'b0,`RT_BASE}+`RT_ROW_BASE+`RT_ROW_VALID_RAW;s_arvalid=1;
  @(posedge clk);@(negedge clk);s_arvalid=0;generation=generation+1;
  wait(s_rvalid);v=s_rdata;ticks(20);
  if(s_rdata!==v) $fatal(1,"generation changed in-flight RAM R");
  s_rready=1;@(posedge clk);@(negedge clk);s_rready=0;
  checks=checks+1;$display("PASS AXI AR/snapshot/event collision and generation during stalled response");
 '''
 needle="extra+race+ring+'  $display"
 assert needle in source
 source=source.replace(needle,"extra+race+ring+"+repr(corner)+"+'  $display")
 source=source.replace("E=O/('diff_'+a.tag)","E=Path("+repr(str(D/'transport'))+")")
 source=source.replace("(E/'reference_top.v').write_text(top,encoding='utf-8')", "top=top.replace('rs485_telem_regs regs','rs485_telem_regs_reference regs')\n (E/'reference_top.v').write_text(top,encoding='utf-8')\n (E/'regs_reference.v').write_text(DELAYED_REFERENCE,encoding='utf-8')")
 source=source.replace("+[E/'reference_top.v']", "+[E/'reference_top.v',E/'regs_reference.v']")
 source=source.replace("[('tb_cache_diff',O/'tb_cache_diff.v','PASS cache differential'),('tb_telemetry',E/'tb_transport_diff.v','PASS telemetry unit')]", "[('tb_telemetry',E/'tb_transport_diff.v','PASS telemetry unit')]")
 source=source.replace("'cycle_changes':0", "'cycle_changes':{'valid_cache_row_AR_to_R':'+1 clock','all_other_interfaces':0}")
 (D/'transport_runner.py').write_text(source,encoding='utf-8')
 import sys
 previous=sys.argv;sys.argv=['run_diff','--tag',a.tag]
 try:exec(compile(source,str(O/'run_diff.py'),'exec'),{'__file__':str(O/'run_diff.py'),'__name__':'__main__','DELAYED_REFERENCE':delayed_reference((E/'baseline/rs485_telem_regs.v').read_text(encoding='utf-8'))})
 finally:sys.argv=previous
 (D/'result.json').write_text(json.dumps({'passed':True,'ram_read_latency_clocks':1,'axi_extra_wait_clocks':1,'cache_log_sha256':hashlib.sha256((D/'cache_simulation.log').read_bytes()).hexdigest(),'transport':json.loads((D/'transport/result.json').read_text(encoding='utf-8'))},indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
