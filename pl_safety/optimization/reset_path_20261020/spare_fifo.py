"""Original FIFO assertions with a physical spare slot and varied capacities."""
import json,shutil,subprocess,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
if __name__=='__main__':
    out=HERE/'spare_fifo_r1';out.mkdir(exist_ok=False)
    tb=(ROOT/'pl_motion/tests/tb_motion_fifo.v').read_text()
    assert tb.count('motion_fifo #(.DEPTH(DEPTH))')==1
    (out/'tb.v').write_text(tb.replace('motion_fifo #(.DEPTH(DEPTH))','motion_fifo #(.DEPTH(DEPTH),.SPARE_SLOT(1))'))
    result={'passed':False,'hashes_computed':False,'cases':[]}
    try:
        for depth in [2,3,7,8,64,65]:
            commands=[('compile',[shutil.which('iverilog'),'-g2005','-s','tb_motion_fifo',f'-Ptb_motion_fifo.DEPTH={depth}',
                       '-o',str(out/f'depth{depth}.vvp'),str(ROOT/'pl_motion/rtl/motion_fifo.v'),str(out/'tb.v')]),
                      ('simulation',[shutil.which('vvp'),str(out/f'depth{depth}.vvp')])]
            for phase,cmd in commands:
                with (out/f'depth{depth}_{phase}.log').open('w') as log:
                    p=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=60)
                assert p.returncode==0,(depth,phase)
            log=(out/f'depth{depth}_simulation.log').read_text();assert 'PASS FIFO' in log
            result['cases'].append({'depth':depth,'passed':True,'result':log.strip()});print(log.strip())
        result['passed']=True
    except Exception:
        result['failure']=traceback.format_exc();raise
    finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
