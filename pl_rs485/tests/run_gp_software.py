"""Compile standalone C11 helpers with strict warnings and run mock vectors."""
import argparse,hashlib,json,os,shutil
from pathlib import Path
from run_sim import run
R=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);a=ap.parse_args()
    if not a.tag.replace('_','').isalnum():raise ValueError('tag')
    b=R/'evidence'/('software_'+a.tag);b.mkdir(exist_ok=False)
    cc=shutil.which('gcc')
    if not cc:raise RuntimeError('GCC required')
    sources=[R/'software/rs485_gp.c',R/'software/example.c',R/'tests/test_gp_software.c']
    exe=b/'test.exe';env=os.environ.copy()
    run([cc,'-std=c11','-Wall','-Wextra','-Werror','-pedantic','-O2',*[str(p) for p in sources],'-o',str(exe)],b,env,b/'compile.log')
    out=run([str(exe)],b,env,b/'test.log');print(out,end='')
    paths=sources+[R/'software/rs485_gp.h',R/'generated/gp_defs.h',R/'generated/rs485_defs.h']
    (b/'manifest.json').write_text(json.dumps({'source_sha256':{p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'passed':True},indent=2)+'\n')
if __name__=='__main__':main()
