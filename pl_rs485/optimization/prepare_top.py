"""Clone exact actual GPIO/RS485/dual-HP baseline inputs into a new project.

Only two allowlisted RTL implementations may change. No IP regeneration, pins,
PS attributes, device, speed, clock, or architecture changes are performed here.
"""
import argparse,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'pl_rs485/optimization'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);ap.add_argument('--baseline',action='store_true');a=ap.parse_args()
 assert a.tag.replace('_','').isalnum()
 B=R/'bsp/work/telemetry_soc_prj';W=R/'bsp/work'/('telemetry_opt_'+a.tag)
 W.mkdir(exist_ok=False);E=O/('top_'+a.tag);E.mkdir(exist_ok=False)
 baseline=json.loads((O/'baseline/manifest.json').read_text(encoding='utf-8'))
 names=['pl_rs485/rtl/rs485_latest_cache.v','pl_rs485/rtl/rs485_telemetry.v']
 candidate={'baseline_commit':'7681c69','tag':a.tag,'mode':'baseline_replay' if a.baseline else 'optimized','changed_source_sha256':{n:sha(R/n) for n in names if sha(R/n)!=baseline['inputs_sha256'][n]}}
 (E/'candidate.json').write_text(json.dumps(candidate,indent=2)+'\n',encoding='utf-8')
 p=subprocess.run([sys.executable,str(R/'bsp/telemetry/verify_input.py'),'--optimization-manifest',str(E/'candidate.json')],cwd=R,capture_output=True,text=True,encoding='utf-8')
 (E/'input_gate.log').write_text(p.stdout+p.stderr,encoding='utf-8');assert p.returncode==0,p.stdout+p.stderr
 # Start from the archived project/PS inputs, so a fresh checkout does not
 # depend on an ignored historical work directory or regenerate PS parameters.
 P=O/'baseline/project'
 for n,h in json.loads((O/'baseline/project_identity.json').read_text(encoding='utf-8')).items():assert sha(P/n)==h,n
 shutil.copytree(P/'system',W/'system');(W/'gp').mkdir()
 shutil.copyfile(P/'system.al',W/'system.al');shutil.copyfile(O/'baseline/connections.json',W/'connections.json')
 for src,dest in [('gp.adc','gp.adc'),('gp.sdc','gp.sdc'),('ps-generated-properties.tcl','ps-generated-properties.tcl')]:shutil.copyfile(O/'baseline'/src,W/'gp'/dest)
 frozen=baseline['actual_top_review']['constraints_sha256']
 for name,key in [('gp.adc','adc'),('gp.sdc','sdc'),('ps-generated-properties.tcl','ps_properties')]:assert sha(W/'gp'/name)==frozen[key]
 assert sha(W/'system/hdl/system_wrapper.v')==baseline['reports_sha256']['system_wrapper.v']
 header=(R/'pl_interface/generated/interface_defs.vh').read_text(encoding='utf-8')
 inputs={}
 for folder in ['pl_rs485','pl_motion','pl_dma']:
  for src in (R/folder/'rtl').glob('*.v'):
   effective=O/'baseline'/(src.stem+'_baseline.v') if a.baseline and src.relative_to(R).as_posix() in names else src
   if effective!=src:assert sha(effective)==baseline['inputs_sha256'][src.relative_to(R).as_posix()]
   text=effective.read_text(encoding='utf-8').replace('`include "generated/interface_defs.vh"',header)
   text=re.sub(r'`include "([^"]+)"',lambda m:(R/'pl_rs485/generated'/m[1]).read_text(encoding='utf-8'),text)
   dest=W/'gp'/src.name
   key=src.relative_to(R).as_posix()
   if key not in candidate['changed_source_sha256']:
    if key.startswith('pl_motion/rtl/'):
     gpio=json.loads((R/'pl_motion/GPIO_RELEASE.json').read_text(encoding='utf-8'))
     assert hashlib.sha256(src.read_bytes().replace(b'\r\n',b'\n')).hexdigest()==gpio['source_sha256_lf'][key],('unchanged canonical motion RTL differs',src)
    else:assert sha(src)==baseline['inputs_sha256'][key],('unchanged frozen RTL differs',src)
   dest.write_text(text,encoding='utf-8');inputs[src.relative_to(R).as_posix()]=sha(effective)
 # Verify all copied protected sources against installed/staged identities.
 ip=json.loads((R/'pl_dma/build/ip/manifest.json').read_text(encoding='utf-8'))
 for lib in ip['libraries'].values():
  src=Path(lib['staged']);assert sha(src)==lib['sha256'];shutil.copyfile(src,W/'gp'/src.name)
 for n,h in ip['headers'].items():
  src=R/'pl_dma/build/ip'/n;assert sha(src)==h['sha256'];shutil.copyfile(src,W/'gp'/n)
 manifest={'work_dir':W.name,'inputs_sha256':inputs,'project_inputs_sha256':{p.relative_to(W).as_posix():sha(p) for p in W.rglob('*') if p.is_file()},'candidate':candidate,'constraints_unchanged':True,'wrapper_unchanged':True,'vendor_unchanged':True}
 (E/'inputs.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
 print('PASS independent exact-board candidate prepared:',W)
if __name__=='__main__':main()
