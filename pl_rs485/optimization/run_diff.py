"""Use byte-archived pre-optimization RTL as an independent cycle/word oracle."""
import argparse,ast,hashlib,json,os,re,shutil,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'pl_rs485/optimization'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);a=ap.parse_args()
 E=O/('diff_'+a.tag);E.mkdir(exist_ok=False)
 m=json.loads((O/'baseline/manifest.json').read_text(encoding='utf-8'))
 for name in ('rs485_latest_cache','rs485_telemetry'):
  p=O/'baseline'/(name+'_baseline.v')
  assert hashlib.sha256(p.read_bytes()).hexdigest()==m['reports_sha256'][p.name]
  (E/p.name).write_text(p.read_text().replace('module '+name,'module '+name+'_baseline',1),encoding='utf-8')
 top=(R/'pl_rs485/rtl/rs485_telem_top.v').read_text().replace('module rs485_telem_top','module rs485_telem_top_baseline',1)
 top=top.replace('rs485_latest_cache #','rs485_latest_cache_baseline #').replace('rs485_telemetry #','rs485_telemetry_baseline #')
 # These instances have no # parameters in the current top.
 top=re.sub(r'\brs485_latest_cache\b','rs485_latest_cache_baseline',top)
 top=re.sub(r'\brs485_telemetry\b','rs485_telemetry_baseline',top)
 (E/'reference_top.v').write_text(top,encoding='utf-8')
 tb=(R/'pl_rs485/tests/tb_telemetry.v').read_text()
 def constant(script,name):
  tree=ast.parse((R/'pl_rs485/tests'/script).read_text())
  return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
 ready=constant('run_telem_irq.py','ready');race=constant('run_telem_irq.py','race')
 extra=constant('run_telem_results.py','extra')
 ring='''
  // Repeated snapshot ID must replay its frozen time/data, then a new ID sees
  // the updates. The cache differential also checks all row words directly.
  rd(`RT_SNAPSHOT_BASE,0,v);held={32'd0,v};time_us=time_us+64'd123456;
  emit(8'he0,8'h30,0,6,48'h80000000ffff,900);snap(8);eq(`RT_SNAPSHOT_BASE,held[31:0]);
  snap(9);rd(`RT_SNAPSHOT_BASE,0,v);if(v==held[31:0]) $fatal(1,"new snapshot did not recapture");
  dma_ready=1;ticks(3);recover_to(4);beats=0;m_ready=0;
  for(n=0;n<256;n=n+1) emit(8'he1,8'h33,0,4,n,n);
  eq(`RT_REG_FIFO_LEVEL,256);time_us=time_us+10010;
  for(q=0;q<20;q=q+1) begin
   wait(dut.transport.state==1);rd(`RT_REG_PACKET_ID,0,id);arm_packet(id,4,1024);
   wait(m_valid);ticks(200);m_ready=1;wait(dut.transport.state==5);ticks(1);acknowledge(id,4);m_ready=0;
   if(q<4) for(n=0;n<16;n=n+1) emit(8'he2,8'h30,0,6,{16'd0,q[15:0],n[15:0]},32'd2000+n);
  end
  eq(`RT_REG_FIFO_LEVEL,0);
  emit(8'he0,8'h3e,0,1,1,3000);time_us=time_us+10010;wait(dut.transport.state==1);
  rd(`RT_REG_PACKET_ID,0,id);arm_packet(id,4,64);wait(m_valid);ticks(2000);m_ready=1;
  wait(m_valid && dut.transport.beat==7);@(negedge clk);
  event_raw={8'd1,8'he0,8'h3e,8'd0,8'd1,8'd1,32'd3001,time_us-64'd10,time_us,48'd2};event_valid=1;
  ticks(1);event_valid=0;wait(dut.transport.state==5);ticks(1);acknowledge(id,4);eq(`RT_REG_FIFO_LEVEL,1);
  time_us=time_us+10010;wait(dut.transport.state==1);rd(`RT_REG_PACKET_ID,0,id);arm_packet(id,4,64);
  wait(dut.transport.state==5);ticks(1);acknowledge(id,4);eq(`RT_REG_FIFO_LEVEL,0);
  $display("PASS ERAM ring wrap and one-record simultaneous pop/push/refresh/long backpressure differential");
 '''
 tb=tb.replace('  arm_packet(id,1,1024);',ready+'  arm_packet(id,1,1024);')
 tb=tb.replace('  $display("PASS telemetry unit',extra+race+ring+'  $display("PASS telemetry unit')
 inst=re.search(r' rs485_telem_top dut\(.*?\);',tb,re.S)[0]
 outs=['s_awready','s_wready','s_bvalid','s_arready','s_rvalid','s_bresp','s_rresp','s_rdata','irq','m_data','m_keep','m_last','m_valid']
 ref=inst.replace('rs485_telem_top dut','rs485_telem_top_baseline reference_transport')
 for n in outs:ref=ref.replace('.'+n+'('+n+')','.'+n+'(ref_'+n+')')
 decl='\n'.join('wire '+('[63:0] ' if n=='m_data' else '[31:0] ' if n=='s_rdata' else '[7:0] ' if n=='m_keep' else '[1:0] ' if n in ['s_bresp','s_rresp'] else '')+'ref_'+n+';' for n in outs)
 compare='always @(negedge clk) if(rst_n) begin\n'
 for n in outs:
  if n in ['m_data','m_keep','m_last']:condition='m_valid && '
  elif n in ['s_rdata','s_rresp']:condition='s_rvalid && '
  elif n=='s_bresp':condition='s_bvalid && '
  else:condition=''
  compare+=f' if({condition}{n}!==ref_{n}) $fatal(1,"transport differential {n}");\n'
 for n in ['fifo_level','status','completion_serial','full_drop','disabled_drop','cancel_drop','stream_records','stream_packets','dma_ok','dma_failed','wait_arm_max_us','backpressure_max_cycles','ready_lateness_max_us','packet_id','packet_generation','packet_count','packet_bytes','command_error','command_result','events']:
  compare+=f' if(dut.transport.{n}!==reference_transport.transport.{n}) $fatal(1,"transport differential {n}");\n'
 compare+='end\n'
 # One full-ring pop/push writes the location the old head occupied. The next
 # head must be the following oldest record, never the newly enqueued tail.
 collision='''
 reg collision_sent=0,collision_active=0;
 always @(negedge clk) begin
  if(collision_active) begin event_valid=0;collision_active=0;end
  else if(!collision_sent && m_valid && m_ready && dut.transport.count==256 && dut.transport.beat==7) begin
   event_raw={8'd1,8'he2,8'h39,8'd0,8'd1,8'd2,32'd999,time_us-64'd10,time_us,48'd123};
   event_valid=1;collision_active=1;collision_sent=1;
  end
 end
 initial begin wait(collision_sent);$display("PASS full FIFO simultaneous pop/push differential");end
 '''
 tb=tb.replace(inst,inst+'\n'+decl+'\n'+ref+'\n'+compare+'\n'+collision)
 (E/'tb_transport_diff.v').write_text(tb,encoding='utf-8')
 env=os.environ.copy();iv=shutil.which('iverilog');vvp=shutil.which('vvp')
 system=Path(os.environ['SystemRoot']);env['PATH']=os.pathsep.join([str(Path(iv).parent),str(system/'System32'),str(system)]);env['TMP']=env['TEMP']=str(E)
 sources=list((R/'pl_rs485/rtl').glob('*.v'))+list(E.glob('*baseline.v'))+[E/'reference_top.v']
 results=[]
 for bench,file,marker in [('tb_cache_diff',O/'tb_cache_diff.v','PASS cache differential'),('tb_telemetry',E/'tb_transport_diff.v','PASS telemetry unit')]:
  commands=[[iv,'-g2005','-Wall','-I',str(R/'pl_rs485/generated'),'-I',str(R/'pl_rs485/tests'),'-s',bench,'-o',str(E/(bench+'.vvp')),*map(str,sources),str(file)],[vvp,str(E/(bench+'.vvp'))]]
  for i,cmd in enumerate(commands):
   p=subprocess.run(cmd,cwd=E,env=env,capture_output=True,text=True,timeout=120)
   (E/(bench+('_compile.log' if i==0 else '_simulation.log'))).write_text('COMMAND '+repr(cmd)+'\nEXIT '+str(p.returncode)+'\n'+p.stdout+p.stderr,encoding='utf-8')
   assert p.returncode==0,(bench,i,p.stdout+p.stderr)
  assert marker in p.stdout;pprint=p.stdout.strip();print(pprint);results.append(pprint)
 (E/'result.json').write_text(json.dumps({'passed':True,'cycle_changes':0,'results':results,'sources_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+[O/'tb_cache_diff.v',O/'run_diff.py',E/'tb_transport_diff.v']}},indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
