"""Exact full-function identity/policy and unsafe approval negative cases."""
from pathlib import Path
import importlib.util,json,shutil,tempfile
H=Path(__file__).resolve().parent;R=H.parents[1]
spec=importlib.util.spec_from_file_location('task_safety_generator',R/'pl_safety/generate.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
for name,text in g.render(H/'config').items():assert (H/'generated'/name).read_text()==text,name
with tempfile.TemporaryDirectory(dir=H/'artifacts') as tmp:
    root=Path(tmp);assert root.resolve().is_relative_to((H/'artifacts').resolve())
    for p in (H/'config').glob('*.json'):shutil.copyfile(p,root/p.name)
    original=json.loads((root/'production.json').read_text());count=0
    for field,value in [('approval_scope','all_motion'),('machine_xyz_calibrated',True),('REFERENCE_POSITION',[0,0,0]),('SEARCH_MAX_STEPS',[501]*3),('HOME_DIRECTION',5),('RELEASE_CYCLES',0)]:
        c=dict(original);c[field]=value;(root/'production.json').write_text(json.dumps(c))
        try:g.render(root)
        except AssertionError:count+=1
        else:raise AssertionError('Unsafe production config accepted: '+field)
    c=dict(original);c['approved']=False;(root/'production.json').write_text(json.dumps(c));result=g.render(root)
    assert '#define HC_NORMAL_MOTION_APPROVED 0u' in result['home_calibration_policy.h']
assert '#define HC_NORMAL_MOTION_APPROVED 1u' in g.render(H/'config')['home_calibration_policy.h']
assert "C_HOME_ONLY=1'b0" in g.render(H/'config')['safety_parameters.vh']
print('PASS exact generated config identity, full-function policy and',count,'unsafe production variants rejected')
