"""Integrate module-validated RTL29 only if candidate21 source ownership matches."""
import json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def lf(data):return data.replace(b'\r\n',b'\n')
def main():
 c=E/'rtl29_candidate_r1';out=E/'rtl29_integration_r1';out.mkdir(exist_ok=False)
 required=['rtl28_service_r1','rtl28_suite_r1','rtl28_control_r1','rtl28_stats_r1','rtl28_cache3_r1','rtl28_cache1_r1','rtl27_rx_reset_r2','rtl29_transport_r4']
 for tag in required:assert json.loads((E/tag/'result.json').read_text())['passed'],tag
 locations={}
 for f in c.glob('*.v'):
  folder='pl_safety/generated' if f.name.startswith('interlock_') else 'pl_motion/rtl' if f.name in ['continuous_motion.v','motion_service.v','motion_stream_rx.v'] else 'pl_safety/rtl' if f.name in ['safety_controller.v','safety_motion_service.v'] else 'pl_rs485/rtl'
  target=R/folder/f.name;assert target.is_file(),target
  assert lf(target.read_bytes())==lf((R/'pl_safety/build/reset_path21/gp'/f.name).read_bytes()),('Concurrent source change',target)
  locations[target]=f
 generator=R/'pl_safety/generate_top.py';fixture=R/'pl_safety/tests/interlock_motion_fixture.py'
 for f in [generator,fixture]:
  assert lf(f.read_bytes())==lf(subprocess.check_output(['git','show','07745a8:'+f.relative_to(R).as_posix()],cwd=R)),('Concurrent source change',f)
 fixture_new=fixture.read_text();needle=".collector_config_pending(1'b0),";assert fixture_new.count(needle)==1
 fixture_new=fixture_new.replace(needle,needle+".collector_config_stored_pending(1'b0),")
 # Save just the directly changed sources before integration, never logs/DB hashes.
 for target in list(locations)+[generator,fixture]:
  saved=out/'before'/target.relative_to(R);saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(target.read_bytes())
 for target,source in locations.items():target.write_bytes(source.read_bytes())
 generator.write_bytes((c/'generate_top.py').read_bytes());fixture.write_text(fixture_new)
 changed=[f.relative_to(R).as_posix() for f in list(locations)+[generator,fixture]]
 result={'integrated':True,'accepted':False,'signoff_pass':False,'hashes_computed':False,'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),
  'candidate':'rtl29_candidate_r1','source_files':changed,'module_results':required,'before_sources_saved':True,
  'reason':'RTL integration checkpoint only; full P&R/real-IP/physical CDC audit pending'}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('Integrated RTL29 after exact candidate21 ownership checks:',len(changed),'files')
if __name__=='__main__':main()
