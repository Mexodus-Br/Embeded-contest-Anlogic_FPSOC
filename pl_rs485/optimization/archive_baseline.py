"""Archive immutable inputs and original actual-board reports before editing RTL."""
import hashlib,json,subprocess,sys,shutil
from pathlib import Path
R=Path(__file__).resolve().parents[2]
E=R/'pl_rs485/optimization/baseline'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def archive_project():
 """Also retain the generated hard-PS configuration needed by a fresh clone."""
 W=R/'bsp/work/telemetry_soc_prj';P=E/'project';P.mkdir(exist_ok=False)
 review=json.loads((E/'review.json').read_text(encoding='utf-8'))
 raw=W/'system/ip/system_ARM_Processor_System_0/RTL/ARM_Processor_System_f6ddd1d59490.v'
 assert sha(raw)==review['input_identity']['raw_ps_sha256']
 assert sha(W/'system/hdl/system_wrapper.v')==sha(E/'system_wrapper.v')
 shutil.copytree(W/'system',P/'system');shutil.copyfile(W/'system.al',P/'system.al')
 (E/'project_identity.json').write_text(json.dumps({p.relative_to(P).as_posix():sha(p) for p in P.rglob('*') if p.is_file()},indent=2)+'\n',encoding='utf-8')
def main():
 E.mkdir(exist_ok=False)
 p=subprocess.run([sys.executable,str(R/'bsp/telemetry/verify_input.py')],cwd=R,capture_output=True,text=True,encoding='utf-8')
 (E/'verify_input.log').write_text(p.stdout+p.stderr,encoding='utf-8')
 assert p.returncode==0,'Frozen input gate failed'
 release=json.loads((R/'pl_rs485/evidence/identity_telemetry.json').read_text(encoding='utf-8'))
 names=set(release['source_sha256'])|set(release['evidence_sha256'])
 names.update(subprocess.check_output(['git','ls-files','bsp/telemetry','pl_motion/rtl','pl_interface'],cwd=R,text=True).splitlines())
 inputs={n:sha(R/n) for n in sorted(names)}
 reports=R/'bsp/evidence/telemetry-hardware-20261014'
 for p in reports.iterdir():
  if p.is_file():shutil.copyfile(p,E/p.name)
 archive_project()
 for name in ('rs485_latest_cache','rs485_telemetry'):
  shutil.copyfile(R/f'pl_rs485/rtl/{name}.v',E/(name+'_baseline.v'))
 (E/'git-status.txt').write_bytes(subprocess.check_output(['git','status','--porcelain=v1'],cwd=R))
 (E/'manifest.json').write_text(json.dumps({'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'branch':subprocess.check_output(['git','branch','--show-current'],cwd=R,text=True).strip(),'inputs_sha256':inputs,'reports_sha256':{p.name:sha(p) for p in E.iterdir() if p.is_file()},'vendor_libraries':release['vendor_libraries'],'actual_top_review':json.loads((R/'bsp/telemetry/hardware-review.json').read_text(encoding='utf-8'))},indent=2)+'\n',encoding='utf-8')
 print('PASS baseline source/IP/evidence gate and actual board report archive')
if __name__=='__main__':main()
