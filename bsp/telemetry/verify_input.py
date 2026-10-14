"""Read-only delivery/ABI migration gate; do not refresh frozen evidence."""
import hashlib,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 m=load(R/'pl_rs485/evidence/identity_telemetry.json')
 for field in ('source_sha256','evidence_sha256'):
  for name,h in m[field].items():
   assert sha(R/name)==h,(field,name)
 assert sha(R/'pl_interface/schema.json')==m['canonical_schema_sha256']
 for lib in m['vendor_libraries'].values():
  assert sha(Path(lib['source']))==lib['sha256']
  assert sha(Path(lib['staged']))==lib['sha256']
 old=json.loads(subprocess.check_output(['git','show','db5f75c:pl_interface/schema.json'],cwd=R))
 new=load(R/'pl_interface/schema.json');count=0
 def retained(a,b,path=''):
  nonlocal count
  if isinstance(a,dict):
   for k,v in a.items():assert k in b,path+'/'+k;retained(v,b[k],path+'/'+k)
  else:assert a==b,path;count+=1
 retained(old,new)
 # Whole old schema/header hashes have deliberately migrated. Every old value
 # above must still match; other frozen motion/GPIO sources remain immutable.
 gpio=load(R/'pl_motion/GPIO_RELEASE.json')
 migrated=[]
 for name,h in gpio['source_sha256_lf'].items():
  current=hashlib.sha256((R/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
  if current!=h:
   assert name in ('pl_interface/schema.json','pl_interface/generate.py','pl_interface/vendor_evidence.json','AGENT.md','PHASE0_CONSTRAINTS.md','HARDWARE.md') or name.startswith('pl_interface/generated/'),name
   migrated.append(name)
 for name,h in gpio['evidence_sha256'].items():assert sha(R/name)==h,name
 for name,h in gpio['vendor_ip_sha256'].items():assert sha(Path(name))==h,name
 for script in ('pl_interface/generate.py','pl_rs485/tools/generate_gp.py','pl_rs485/tools/generate_telem.py','pl_dma/generate_telemetry.py','pl_dma/generate_motion.py','pl_motion/generate_scope.py'):
  subprocess.run([sys.executable,str(R/script),'--check'],check=True,cwd=R)
 return {'status':'PASS','telemetry_identity':'f447116','schema_sha256':m['canonical_schema_sha256'],'old_leaf_values_equal':count,'old_whole_file_migrations':migrated,'vendor_ip_unchanged':True,'gpio_motion_core_unchanged':True}
if __name__=='__main__':print(json.dumps(main(),indent=2))
