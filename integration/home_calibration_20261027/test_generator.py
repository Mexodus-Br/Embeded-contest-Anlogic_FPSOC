from pathlib import Path
import importlib.util,json,shutil,tempfile
H=Path(__file__).resolve().parent;R=H.parents[1]
spec=importlib.util.spec_from_file_location('home_generator',R/'pl_safety/generate.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
with tempfile.TemporaryDirectory(dir=H/'artifacts') as tmp:
 root=Path(tmp);(root/'pl_interface').mkdir();(root/'pl_safety/config').mkdir(parents=True)
 shutil.copyfile(R/'pl_interface/schema.json',root/'pl_interface/schema.json')
 for p in (R/'pl_safety/config').glob('*.json'):shutil.copyfile(p,root/'pl_safety/config'/p.name)
 g.R=root;g.D=root/'pl_safety';p=g.D/'config/production.json';original=json.loads(p.read_text())
 assert 'C_HOME_ONLY=CONFIG_PROFILE==0' in g.render()['safety_parameters.vh']
 count=0
 for field,value in [('approval_scope','all_motion'),('REFERENCE_POSITION',[0,0,0]),('SEARCH_MAX_STEPS',[501]*3),('machine_xyz_calibrated',True),('RELEASE_CYCLES',0)]:
  cfg=dict(original);cfg[field]=value;p.write_text(json.dumps(cfg))
  try:g.render()
  except AssertionError:count+=1
  else:raise AssertionError('unsafe approval accepted: '+field)
 cfg=dict(original);cfg['approved']=False;p.write_text(json.dumps(cfg))
 assert "CONFIG_PROFILE==0 ? 1'b0" in g.render()['safety_parameters.vh']
 print('PASS exact calibration approval, '+str(count)+' rejected unsafe variants, explicit unapproved/unknown profile gate')
