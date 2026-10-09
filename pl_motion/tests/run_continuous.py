"""Independently tested components and full continuous stream regression."""
import argparse,json,re,sys
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sim_tools import Simulator

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--components-only',action='store_true')
    args=ap.parse_args()
    sim=Simulator(ROOT/'build')
    components=[('motion_fifo', ['motion_fifo.v'],d) for d in [2,3,8]]+[
                ('motion_planner',['motion_planner.v'],None),('motion_executor',['motion_executor.v'],None)]
    for name,files,depth in components:
        out=ROOT/f'build/{name}_{depth}.vvp'
        sim.compile([ROOT/'rtl'/x for x in files]+[ROOT/f'tests/tb_{name}.v'],'tb_'+name,out,
                    extra=[f'-Ptb_motion_fifo.DEPTH={depth}'] if depth else [])
        print(sim.simulate(out),end='',flush=True)
    if args.components_only:return
    def check_case(mode,scale):
        out=ROOT/f'build/continuous_{mode}_{scale}.vvp'
        diagnostic=sim.compile([ROOT/'rtl'/x for x in ['motion_fifo.v','motion_planner.v','motion_executor.v','continuous_motion.v']]+
            [ROOT/'tests/tb_continuous_motion.v'],'tb_continuous_motion',out,
            extra=[f'-Ptb_continuous_motion.MODE={mode}',f'-Ptb_continuous_motion.SCALE={scale}'])
        result=sim.simulate(out,timeout=180)
        if 'PASS continuous' not in result:raise RuntimeError('missing PASS')
        line=next(x for x in result.splitlines() if x.startswith('PASS continuous'))
        metrics={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line)}
        return dict(metrics=metrics,diagnostic=diagnostic,output=result)
    results=[];errors=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(check_case,m,s) for s in [1,2] for m in range(10)]
        for f in as_completed(futures):
            try:
                r=f.result();results.append(r);print(r['output'],end='',flush=True)
            except Exception as e:errors.append(str(e));print('FAIL '+str(e),flush=True)
    if errors:raise RuntimeError('\n'.join(errors))
    totals={k:sum(r['metrics'][k] for r in results) for k in ['checks','starts','dones','END','underflows','stale','abort_offsets']}
    (ROOT/'build/continuous_results.json').write_text(json.dumps(dict(results=results,totals=totals),indent=2)+'\n')
    print('PASS continuous all groups '+json.dumps(totals),flush=True)

if __name__=='__main__':main()
