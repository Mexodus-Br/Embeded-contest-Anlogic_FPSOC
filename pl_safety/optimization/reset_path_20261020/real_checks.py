"""Run the three real vendor-IP scenarios serially; no hashes or board access."""
import argparse, json, subprocess, sys, traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--round',type=int,default=17);ap.add_argument('--tag',default='real_r1')
    a=ap.parse_args();assert a.round in [17,18,19,20,21] and a.tag.replace('_','').isalnum()
    out=HERE/a.tag;out.mkdir(exist_ok=False)
    result={'passed':False,'hashes_computed':False,'cases':[]}
    try:
        for scenario in ['protection','watchdog','feedback_timeout']:
            tag=f'reset{a.round}_real_'+scenario+'_r1'
            cmd=[sys.executable,'-u',str(ROOT/'pl_safety/tests/interlock_real_system.py'),
                 '--tag',tag,'--scenario',scenario,'--accepted-overlap']
            with (out/(scenario+'.log')).open('w') as log:
                p=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
            path=ROOT/'pl_safety/evidence'/tag/'result.json'
            record={'scenario':scenario,'tag':tag,'exit_code':p.returncode,
                    'passed':p.returncode==0 and path.exists() and json.loads(path.read_text())['passed']}
            result['cases'].append(record)
            (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
            print(record,flush=True);assert record['passed'],record
        result['passed']=True
    except Exception:
        result['failure']=traceback.format_exc();raise
    finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
