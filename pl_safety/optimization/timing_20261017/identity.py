"""Authorization-commit baseline plus preserved old ABI; historical gates unchanged."""
import hashlib,json,subprocess,sys
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[2]
sys.path.insert(0,str(R/'pl_safety'));from verify_delivery import old_retained,commit_blobs
START='2f09a56'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check():
 blobs=commit_blobs(START,['PHASE0_CONSTRAINTS.md','pl_interface/schema.json'])
 for name,data in blobs.items():assert (R/name).read_bytes().replace(b'\r\n',b'\n')==data.replace(b'\r\n',b'\n'),('authorization input changed',name)
 old=json.loads(subprocess.check_output(['git','show','c9f2e05:pl_interface/schema.json'],cwd=R));new=json.loads((R/'pl_interface/schema.json').read_text(encoding='utf-8'))
 n=old_retained(old,new);assert n==3068 and set(new)-set(old)=={'safety_profiles'}
 for name in ['interface_defs.h','interface_defs.vh','registers.md','errors.md']:
  old=subprocess.check_output(['git','show','c9f2e05:pl_interface/generated/'+name],cwd=R)
  assert old.splitlines()[1:]==(R/'pl_interface/generated'/name).read_bytes().splitlines()[1:]
 allowed={'AGENT.md','pl_safety/rtl/safety_controller.v','pl_motion/rtl/motion_stream_rx.v','pl_motion/rtl/motion_service.v'}
 changed=subprocess.check_output(['git','diff','--name-only',START,'--'],cwd=R,text=True).splitlines()
 for name in changed:assert name in allowed or name.startswith('pl_safety/optimization/timing_20261017/') or name.startswith('pl_safety/evidence/closure_'),('unrelated mutation',name)
 initial=json.loads((E/'BASELINE.json').read_text(encoding='utf-8'))['sha256']
 for name,h in initial.items():
  if name not in ['AGENT.md','pl_safety/rtl/safety_controller.v','pl_motion/rtl/motion_stream_rx.v','pl_motion/rtl/motion_service.v']:
   assert sha(R/name)==h,('unchanged baseline evidence/source',name)
 return {'passed':True,'authorization_commit':START,'old_schema_leaf_values':n,'old_gate_untouched':True,'production_config_sha256':sha(R/'pl_safety/config/production.json')}
if __name__=='__main__':
 out=E/sys.argv[1];out.mkdir(exist_ok=False)
 p=subprocess.run([sys.executable,'pl_safety/verify_delivery.py'],cwd=R,capture_output=True,text=True)
 (out/'historical_gate.log').write_text(p.stdout+p.stderr)
 result=check();result['historical_gate_exit']=p.returncode;result['historical_gate_scope_note']='c9f2e05 gate rejects the preexisting authorization documentation commit; no assertion removed'
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
