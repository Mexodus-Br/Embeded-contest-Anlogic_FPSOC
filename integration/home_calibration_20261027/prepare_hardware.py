"""Isolate reviewed complete frozen PL; apply only calibration-specific changes."""
from pathlib import Path
import json
import re
import shutil
import subprocess

H=Path(__file__).resolve().parent
R=H.parents[1]
F=R/'integration/controlled_v1_20261021/frozen/pl'
P=H/'hardware'
assert not P.exists(), 'Preserve prior attempt'
subprocess.run(['python',str(R/'pl_safety/generate.py'),'--check'],check=True)
shutil.copytree(F,P)
# Use previously reviewed fixed J12 constraints, not current dirty RTL.
shutil.copyfile(R/'integration/controlled_v1_20261021/hardware/gp/gp.adc',P/'gp/gp.adc')
shutil.copyfile(R/'pl_safety/generated/safety_parameters.vh',P/'gp/safety_parameters.vh')
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
assert s.count(".MAX_STEP_HZ({64'd0,{3{64'd100000}}})")==1
s=s.replace(".MAX_STEP_HZ({64'd0,{3{64'd100000}}})",".MAX_STEP_HZ({64'd0,{3{64'd16000}}})")
w.write_text(s)
project=P/'system.al'
project.write_text(re.sub(r'(<Project [^>]*Path=")[^"]*',lambda m:m[1]+P.as_posix(),project.read_text(),count=1))
script=(F/'run.tcl').read_text()
script=re.sub(r'^cd .*',lambda m:'cd '+P.as_posix(),script,count=1,flags=re.M)
(P/'run.tcl').write_text(script)
assert script.count('set_param flow thread 16')>=5
changed=[]
for p in F.rglob('*'):
 if p.is_file() and p.read_bytes()!=(P/p.relative_to(F)).read_bytes():changed.append(p.relative_to(F).as_posix())
assert set(changed)=={'gp/gp.adc','gp/safety_parameters.vh','gp/safety_motion_service.v','system/hdl/system_wrapper.v','system.al','run.tcl'},changed
assert (P/'gp/gp.sdc').read_bytes()==(F/'gp/gp.sdc').read_bytes()
(H/'hardware-inputs.json').write_text(json.dumps(dict(base_commit='05686d4',frozen_origin=str(F),changes=changed,dirty_product_rtl_included=False,threads=16,home_only=True),indent=2)+'\n')
print(P)
