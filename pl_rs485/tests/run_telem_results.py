"""Focused failed/aborted packet result test using the same AXI selfchecker."""
import argparse,os,shutil,json,hashlib
from pathlib import Path
from run_sim import run
R=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);a=ap.parse_args();b=R/'evidence'/('telem_results_'+a.tag);b.mkdir(exist_ok=False)
extra='''
  eq(`RT_REG_DMA_FAILED,1);
  emit(8'he0,8'h3a,0,1,2,500);time_us=time_us+10010;wait(dut.transport.state==1);
  rd(`RT_REG_PACKET_ID,0,id);rd(`RT_REG_PACKET_BYTES,0,v);arm_packet(id,3,v);wait(m_valid);
  wr(`RT_REG_COMPLETE_ID,id,15,0);wr(`RT_REG_COMPLETE_GEN,3,15,0);wr(`RT_REG_COMPLETE_RESULT,1,15,0);wr(`RT_REG_COMPLETE,1,15,0);
  eq(`RT_REG_DMA_FAILED,2);ticks(10);if(!m_valid) $fatal(1,"failed completion retracted VALID");
  wr(`RT_REG_COMPLETE,1,15,0);eq(`RT_REG_DMA_FAILED,2);
  wr(`RT_REG_COMPLETE_RESULT,0,15,0);wr(`RT_REG_COMPLETE,1,15,2);
  dma_ready=0;ticks(3);dma_ready=1;ticks(3);eq(`RT_REG_DMA_FAILED,2);
'''
tb=(R/'tests/tb_telemetry.v').read_text().replace('  $display("PASS telemetry unit',extra+'  $display("PASS telemetry result unit')
(b/'tb.v').write_text(tb)
iv=shutil.which('iverilog');env=os.environ.copy();root=Path(os.environ['SystemRoot']);env['PATH']=os.pathsep.join([str(Path(iv).parent),str(root/'System32'),str(root)]);env['TMP']=env['TEMP']=str(b)
sources=list((R/'rtl').glob('*.v'))+[b/'tb.v'];exe=b/'result.vvp'
run([iv,'-g2005','-I',str(R/'generated'),'-I',str(R/'tests'),'-s','tb_telemetry','-o',str(exe),*map(str,sources)],b,env,b/'compile.log')
out=run([shutil.which('vvp'),str(exe)],b,env,b/'test.log');print(out)
(b/'manifest.json').write_text(json.dumps({'passed':True,'harness_sha256':hashlib.sha256((b/'tb.v').read_bytes()).hexdigest(),'source_sha256':{p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources if p.is_relative_to(R/'rtl')}},indent=2)+'\n')
