"""Independent complete PL input; never consumes product dirty RTL."""
from pathlib import Path
import argparse,importlib.util
import json
import re
import shutil

H=Path(__file__).resolve().parent
R=H.parents[1]
F=R/'integration/controlled_v1_20261021/frozen/pl'
parser=argparse.ArgumentParser();parser.add_argument('--directory',default='hardware');parser.add_argument('--executor-cofactor',action='store_true');args=parser.parse_args()
assert re.fullmatch('[a-zA-Z0-9_]+',args.directory)
P=H/args.directory
assert not P.exists(), 'Preserve prior attempts'
# The task's versioned config is authoritative; never regenerate it from a
# different task's current working-tree production settings.
config=H/'config'
assert all((config/(n+'.json')).is_file() for n in ['production','simulation','resource_fixture'])
assert json.loads((config/'production.json').read_text())['approval_scope']=='runtime_calibrated_motion'
spec=importlib.util.spec_from_file_location('safety_generator',R/'pl_safety/generate.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
out=H/'generated';out.mkdir(exist_ok=True)
for n,t in g.render(config).items():(out/n).write_bytes(t.encode())
shutil.copytree(F,P)
if args.executor_cofactor:shutil.copyfile(H/'rtl/motion_executor.v',P/'gp/motion_executor.v')
shutil.copyfile(R/'integration/controlled_v1_20261021/hardware/gp/gp.adc',P/'gp/gp.adc')
shutil.copyfile(out/'safety_parameters.vh',P/'gp/safety_parameters.vh')
s=(P/'gp/safety_motion_service.v').read_text()
assert s.count('.safety_inhibit(normal_inhibit)')==1
s=s.replace('.safety_inhibit(normal_inhibit)','.safety_inhibit(normal_inhibit || C_HOME_ONLY)')
(P/'gp/safety_motion_service.v').write_text(s)
w=P/'system/hdl/system_wrapper.v';s=w.read_text()
assert s.count('.CONFIG_PROFILE(2)')==1
s=s.replace('.CONFIG_PROFILE(2)','.CONFIG_PROFILE(0)')
for k in ['STEP_HIGH_CYCLES','STEP_LOW_CYCLES']:
    old='.'+k+"({64'd0,{3{64'd500}}})";assert s.count(old)==1
    s=s.replace(old,'.'+k+"({64'd0,{3{64'd3125}}})")
old=".MAX_STEP_HZ({64'd0,{3{64'd100000}}})";assert s.count(old)==1
s=s.replace(old,".MAX_STEP_HZ({64'd0,{3{64'd16000}}})")
w.write_text(s)
project=P/'system.al'
project.write_text(re.sub(r'(<Project [^>]*Path=")[^"]*',lambda m:m[1]+P.as_posix(),project.read_text(),count=1))
script=re.sub(r'^cd .*',lambda m:'cd '+P.as_posix(),(F/'run.tcl').read_text(),count=1,flags=re.M)
(P/'run.tcl').write_text(script)
assert script.count('set_param flow thread 16')>=5
changed=[p.relative_to(F).as_posix() for p in F.rglob('*') if p.is_file() and p.read_bytes()!=(P/p.relative_to(F)).read_bytes()]
expected={'gp/gp.adc','gp/safety_parameters.vh','gp/safety_motion_service.v','system/hdl/system_wrapper.v','system.al','run.tcl'}
if args.executor_cofactor:expected.add('gp/motion_executor.v')
assert set(changed)==expected,changed
(H/(args.directory+'-inputs.json')).write_text(json.dumps(dict(base_commit='a21751d',frozen_origin=str(F),changes=changed,dirty_product_rtl_included=False,threads=16,normal_motion_policy='runtime_calibrated_motion',executor_cofactor=args.executor_cofactor,board_tested=False),indent=2)+'\n')
print(P)
