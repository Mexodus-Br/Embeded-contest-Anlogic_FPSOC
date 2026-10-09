"""Four-axis real HDL self-checks; run in the verified Icarus environment."""
import sys
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sim_tools import Simulator


def main():
    sim=Simulator(ROOT/'build')
    def check_profile(scale,polarity,group):
        out=ROOT/f'build/four_{scale}_{group}.vvp'
        diagnostics=sim.compile([ROOT/'rtl/four_axis_motion.v',
            ROOT/'tests/tb_four_axis_motion.v'],'tb_four_axis_motion',out,
            extra=[f'-Ptb_four_axis_motion.SCALE={scale}',f'-Ptb_four_axis_motion.POL={polarity}',
                   f'-Ptb_four_axis_motion.TEST_GROUP={group}'])
        # Report routine Icarus memory sensitivity notices compactly; retain
        # every other diagnostic verbatim. These are not excluded test cases.
        notices=[x for x in diagnostics.splitlines() if 'warning: @* is sensitive to all 4 words in array' in x]
        other=[x for x in diagnostics.splitlines() if x not in notices]
        result=sim.simulate(out,timeout=180)
        if 'PASS four' not in result:
            raise RuntimeError('four-axis self-check did not complete')
        line=next(x for x in result.splitlines() if x.startswith('PASS four'))
        metrics={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line)}
        return dict(scale=scale,polarity=polarity,group=group,metrics=metrics,
                    diagnostics=diagnostics,output=result),\
            f'scale={scale} EN_POL={polarity} group={group} array_sensitivity_notices={len(notices)}\n'+\
            ('\n'.join(other)+'\n' if other else '')+result
    # Independent simulations, unique outputs. Every future is inspected;
    # there are no agents, retries or skipped groups.
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(check_profile,scale,polarity,group)
                 for scale,polarity in [(1,15),(2,10)] for group in range(6)]
        results=[]
        for future in as_completed(futures):
            record,message=future.result()
            results.append(record)
            print(message,end='',flush=True)
    results.sort(key=lambda r:(r['scale'],r['group']))
    totals={k:sum(r['metrics'][k] for r in results)
            for k in ['checks','points','slots','edges','safety_offsets','reset_offsets']}
    (ROOT/'build/four_axis_results.json').write_text(
        json.dumps(dict(results=results,totals=totals),indent=2)+'\n',encoding='utf-8')
    print('PASS all four-axis groups: '+json.dumps(totals),flush=True)


if __name__=='__main__':
    main()
