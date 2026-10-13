"""Independent deterministic fail-fast runner; no retries or skipped failures."""
import argparse,hashlib,json,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(args,cwd,env,log,timeout=90):
    p=subprocess.run(args,cwd=cwd,env=env,capture_output=True,text=True,timeout=timeout)
    out=p.stdout+p.stderr
    log.write_text('COMMAND '+repr(args)+'\nEXIT '+str(p.returncode)+'\n'+out)
    if p.returncode:raise RuntimeError(f'failed {p.returncode}; retained {log}')
    return out
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=20261013);ap.add_argument('--tag',default='current');ap.add_argument('--wave',action='store_true');a=ap.parse_args()
    if not a.tag.replace('_','').replace('-','').isalnum():raise ValueError('invalid tag')
    b=ROOT/'evidence'/('sim_'+a.tag);b.mkdir(parents=True,exist_ok=True)
    tracked=[ROOT/'schema.json',ROOT/'tools/generate.py',ROOT/'tests/run_sim.py']
    tracked += [p for folder in ['rtl','generated','tests'] for p in (ROOT/folder).glob('*') if p.is_file()]
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked}
    env=os.environ.copy();iv=shutil.which('iverilog');vvp=shutil.which('vvp')
    if not iv or not vvp:raise RuntimeError('Icarus required')
    if os.name=='nt':
        system=Path(os.environ['SystemRoot']);env['PATH']=os.pathsep.join([str(Path(iv).parent),str(system/'System32'),str(system)])
        env['TMP']=env['TEMP']=str(b)
    for bench in ['tb_rs485','tb_profile','tb_fifo']:
        sources=list((ROOT/'rtl').glob('*.v'))+[ROOT/'tests'/f'{bench}.v']
        run([iv,'-g2005','-Wall','-I',str(ROOT/'generated'),'-s',bench,'-o',str(b/(bench+'.vvp'))]+[str(p) for p in sources],b,env,b/(bench+'_compile.log'))
        out=run([vvp,str(b/(bench+'.vvp')),f'+seed={a.seed}']+(['+wave'] if a.wave else []),b,env,b/(bench+'_simulation.log'))
        print(out,end='')
        marker={'tb_rs485':'PASS rs485','tb_profile':'PASS profile','tb_fifo':'PASS FIFO'}[bench]
        if marker not in out:raise RuntimeError('missing completion marker')
    if any(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()!=v for k,v in hashes.items()):raise RuntimeError('sources changed during simulation')
    (b/'manifest.json').write_text(json.dumps({'seed':a.seed,'source_sha256':hashes,'passed':['tb_rs485','tb_profile','tb_fifo']},indent=2)+'\n')
if __name__=='__main__':main()
