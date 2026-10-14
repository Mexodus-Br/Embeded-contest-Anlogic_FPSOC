"""Deterministic telemetry units, preserving failure logs and source identity."""
import argparse,hashlib,json,os,shutil
from pathlib import Path
from run_sim import run
R=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);ap.add_argument('--seed',type=int,default=20261014);a=ap.parse_args()
 if not a.tag.replace('_','').isalnum():raise ValueError('tag')
 b=R/'evidence'/('telemetry_'+a.tag);b.mkdir(exist_ok=False)
 iv=shutil.which('iverilog');vvp=shutil.which('vvp');env=os.environ.copy()
 if os.name=='nt':
  root=Path(os.environ['SystemRoot']);env['PATH']=os.pathsep.join([str(Path(iv).parent),str(root/'System32'),str(root)]);env['TMP']=env['TEMP']=str(b)
 sources=list((R/'rtl').glob('*.v'))+[R/'tests/tb_telemetry.v']
 run([iv,'-g2005','-Wall','-I',str(R/'generated'),'-I',str(R/'tests'),'-s','tb_telemetry','-o',str(b/'unit.vvp'),*map(str,sources)],b,env,b/'compile.log')
 out=run([vvp,str(b/'unit.vvp'),f'+seed={a.seed}'],b,env,b/'simulation.log');print(out)
 if 'PASS telemetry unit' not in out:raise RuntimeError('completion marker absent')
 paths=sources+list((R/'generated').glob('*'))+[R.parent/'pl_interface/schema.json']
 (b/'manifest.json').write_text(json.dumps({'passed':True,'seed':a.seed,'source_sha256':{os.path.relpath(p,R).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}},indent=2)+'\n')
if __name__=='__main__':main()
