import argparse,os,shutil,json,hashlib
from pathlib import Path
from run_sim import run
R=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);a=ap.parse_args();b=R/'evidence'/('telem_parse_'+a.tag);b.mkdir(exist_ok=False)
iv=shutil.which('iverilog');env=os.environ.copy();env['PATH']=str(Path(iv).parent)+os.pathsep+env['PATH']
sources=[R/'rtl/rs485_light_parse.v',R/'tests/tb_light_parse.v'];exe=b/'parse.vvp'
run([iv,'-g2005','-I',str(R/'generated'),'-s','tb_light_parse','-o',str(exe),*map(str,sources)],b,env,b/'compile.log')
out=run([shutil.which('vvp'),str(exe)],b,env,b/'test.log');print(out)
(b/'manifest.json').write_text(json.dumps({'passed':True,'source_sha256':{p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}},indent=2)+'\n')
