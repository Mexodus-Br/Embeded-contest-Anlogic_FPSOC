import argparse,hashlib,json,os,shutil
from pathlib import Path
from run_sim import run
R=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--vectors',required=True);ap.add_argument('--tag',required=True);a=ap.parse_args()
b=R/'evidence'/('telem_software_'+a.tag);b.mkdir(exist_ok=False);cc=shutil.which('gcc');exe=b/'check.exe'
sources=[R/'software/rs485_gp.c',R/'software/rs485_telem.c',R/'tests/test_telem_software.c']
run([cc,'-std=c11','-Wall','-Wextra','-Werror','-pedantic','-O2',*map(str,sources),'-o',str(exe)],b,os.environ.copy(),b/'compile.log')
out=run([str(exe),str(Path(a.vectors).resolve())],b,os.environ.copy(),b/'test.log');print(out)
(b/'manifest.json').write_text(json.dumps({'passed':True,'vectors_sha256':hashlib.sha256(Path(a.vectors).read_bytes()).hexdigest(),'source_sha256':{p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}},indent=2)+'\n')
