"""Fail-fast GP regressions, unique evidence tag and frozen source manifest."""
import argparse,hashlib,json,os,shutil
from pathlib import Path
from run_sim import run
R=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);ap.add_argument('--seed',type=int,default=20261014);a=ap.parse_args()
    if not a.tag.replace('_','').isalnum():raise ValueError('tag')
    b=R/'evidence'/('sim_'+a.tag);b.mkdir(parents=True,exist_ok=False)
    paths=[R.parent/'pl_interface/schema.json']+[p for f in ['rtl','generated','tests','tools'] for p in (R/f).glob('*') if p.is_file()]
    hashes={os.path.relpath(p,R).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    iv=shutil.which('iverilog');vvp=shutil.which('vvp');env=os.environ.copy()
    if not iv or not vvp:raise RuntimeError('Icarus required')
    if os.name=='nt':
        system=Path(os.environ['SystemRoot']);env['PATH']=os.pathsep.join([str(Path(iv).parent),str(system/'System32'),str(system)])
        env['TMP']=env['TEMP']=str(b)
    benches=['tb_gp_regs','tb_gp_stress','tb_gp_e2e']
    for bench in benches:
        sources=list((R/'rtl').glob('*.v'))+[R/'tests'/f'{bench}.v']
        run([iv,'-g2005','-Wall','-I',str(R/'generated'),'-I',str(R/'tests'),'-s',bench,'-o',str(b/(bench+'.vvp'))]+[str(p) for p in sources],b,env,b/(bench+'_compile.log'))
        out=run([vvp,str(b/(bench+'.vvp')),f'+seed={a.seed}'],b,env,b/(bench+'_simulation.log'),timeout=180)
        print(out,end='')
        if 'PASS GP' not in out:raise RuntimeError('completion marker absent')
    if any(hashlib.sha256((R/k).read_bytes()).hexdigest()!=v for k,v in hashes.items()):raise RuntimeError('source changed')
    (b/'manifest.json').write_text(json.dumps({'seed':a.seed,'source_sha256':hashes,'passed':benches},indent=2)+'\n')
if __name__=='__main__':main()
