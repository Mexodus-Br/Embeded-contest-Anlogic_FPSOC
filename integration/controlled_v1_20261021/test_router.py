"""Reuse six-way ownership oracle with exact seven-way actual routed decoder."""
from pathlib import Path
import shutil
import subprocess
import argparse
import json
H=Path(__file__).resolve().parent
R=H.parents[1]
p=argparse.ArgumentParser();p.add_argument('--tag',default='seven-router');p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
assert a.tag.replace('-','').replace('_','').isalnum()
out=H/'evidence'/a.tag
out.mkdir(exist_ok=False)
text=(R/'bsp/telemetry/tb_router.v').read_text()
for old,new in [('[197:0]','[230:0]'),('[191:0]','[223:0]'),('[23:0]','[27:0]'),
                ('[5:0]','[6:0]'),('[11:0]','[13:0]'),('=63','=127'),
                ('axi_lite_six_way dut','safety_axi_lite_seven_way dut'),
                ('i<6','i<7'),('j<6','j<7'),
                ("transaction(33'h080a00000,1);","transaction(33'h180a00000,1);transaction(33'h080a01000,1);"),
                ('six-way','seven-way')]:text=text.replace(old,new)
(out/'tb.v').write_text(text)
gp=H/'hardware/gp'
# Relative paths keep commands portable. This Windows Icarus requires execution
# outside the restricted sandbox (0xC0000005 inside it); preserve failed attempts.
def rel(p):return p.relative_to(R).as_posix()
commands=[[shutil.which('iverilog'),'-g2005','-I',rel(gp),'-I',rel(gp.parent),'-s','tb_router','-o',rel(out/'test.vvp'),rel(gp/'safety_axi_lite_seven_way.v'),rel(out/'tb.v')],
          [shutil.which('vvp'),rel(out/'test.vvp')]]
records=[]
if a.prepare_only:
    print(out)
    raise SystemExit(0)
for i,command in enumerate(commands):
    result=subprocess.run(command,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
    (out/('compile.log' if i==0 else 'simulation.log')).write_bytes(result.stdout)
    records.append({'command':command,'exit_code':result.returncode})
    (out/'result.json').write_text(json.dumps({'commands':records,'passed':i==1 and result.returncode==0,'hashes_computed':False},indent=2)+'\n')
    assert result.returncode==0,(command,result.returncode,result.stdout.decode(errors='replace'))
print(result.stdout.decode())
