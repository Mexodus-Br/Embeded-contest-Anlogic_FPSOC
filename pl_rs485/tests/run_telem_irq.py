"""Directed persistent-source/mask/W1C set-wins races through real Lite BFM."""
import argparse,os,shutil,json,hashlib
from pathlib import Path
from run_sim import run
R=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);a=ap.parse_args();b=R/'evidence'/('telem_irq_'+a.tag);b.mkdir(exist_ok=False)
ready='''
  wr(`RT_REG_IRQ_MASK,`RT_IRQ_PACKET_READY,15,0);wr(`RT_REG_IRQ_PENDING,31,15,0);
  rd(`RT_REG_IRQ_PENDING,0,v);if(!(v&`RT_IRQ_PACKET_READY) || !irq) $fatal(1,"persistent READY W1C set-wins");
  wr(`RT_REG_IRQ_MASK,0,15,0);if(irq) $fatal(1,"masked IRQ");
  wr(`RT_REG_IRQ_PENDING,31,15,0);rd(`RT_REG_IRQ_PENDING,0,v);if(!(v&1)) $fatal(1,"masked READY lost");
  wr(`RT_REG_IRQ_MASK,1,15,0);if(!irq) $fatal(1,"unmask pending source");wr(`RT_REG_IRQ_MASK,0,15,0);
'''
race='''
  wr(`RT_REG_IRQ_MASK,`RT_IRQ_FAULT,15,0);wr(`RT_REG_IRQ_PENDING,31,15,0);eq(`RT_REG_IRQ_PENDING,0);
  fork
   wr(`RT_REG_IRQ_PENDING,`RT_IRQ_FAULT,15,0);
   begin wait(dut.regs.wf && dut.regs.wa[11:0]==`RT_REG_IRQ_PENDING);dma_ready=0;end
  join
  ticks(3);eq(`RT_REG_IRQ_PENDING,`RT_IRQ_FAULT);if(!irq) $fatal(1,"edge fault lost to W1C");
  wr(`RT_REG_IRQ_PENDING,`RT_IRQ_FAULT,15,0);if(irq) $fatal(1,"fault source cleared");
  wr(`RT_REG_IRQ_MASK,0,15,0);dma_ready=1;ticks(3);dma_ready=0;ticks(3);
  eq(`RT_REG_IRQ_PENDING,`RT_IRQ_FAULT);if(irq) $fatal(1,"masked edge fault");
  wr(`RT_REG_IRQ_MASK,`RT_IRQ_FAULT,15,0);if(!irq) $fatal(1,"edge rearm");
  wr(`RT_REG_IRQ_PENDING,`RT_IRQ_FAULT,15,0);if(irq) $fatal(1,"edge W1C");
'''
tb=(R/'tests/tb_telemetry.v').read_text().replace('  arm_packet(id,1,1024);',ready+'  arm_packet(id,1,1024);').replace('  $display("PASS telemetry unit',race+'  $display("PASS telemetry IRQ unit')
(b/'tb.v').write_text(tb)
iv=shutil.which('iverilog');env=os.environ.copy();root=Path(os.environ['SystemRoot']);env['PATH']=os.pathsep.join([str(Path(iv).parent),str(root/'System32'),str(root)]);env['TMP']=env['TEMP']=str(b)
sources=list((R/'rtl').glob('*.v'))+[b/'tb.v'];exe=b/'irq.vvp'
run([iv,'-g2005','-I',str(R/'generated'),'-I',str(R/'tests'),'-s','tb_telemetry','-o',str(exe),*map(str,sources)],b,env,b/'compile.log')
out=run([shutil.which('vvp'),str(exe)],b,env,b/'test.log');print(out)
if 'PASS telemetry IRQ unit' not in out:raise RuntimeError('IRQ completion missing')
(b/'manifest.json').write_text(json.dumps({'passed':True,'harness_sha256':hashlib.sha256((b/'tb.v').read_bytes()).hexdigest(),'source_sha256':{p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources if p.is_relative_to(R/'rtl')}},indent=2)+'\n')
