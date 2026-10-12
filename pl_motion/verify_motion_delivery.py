"""Verify frozen source/IP identity, generated wiring and required evidence."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def raw(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def lf(p):return hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
def main():
 release=json.loads((ROOT/'pl_motion/MOTION_RELEASE.json').read_text())
 for n,d in release['source_sha256_lf'].items():
  if lf(ROOT/n)!=d:raise RuntimeError('release source differs '+n)
 for n,d in release['evidence_sha256'].items():
  if raw(ROOT/n)!=d:raise RuntimeError('evidence differs '+n)
 for n,d in release['vendor_ip_sha256'].items():
  if raw(Path(n))!=d:raise RuntimeError('installed IP differs '+n)
 for script,args in [('pl_interface/generate.py',['--check']),('pl_dma/generate_motion.py',['--check'])]:
  subprocess.run([sys.executable,str(ROOT/script),*args],cwd=ROOT,check=True)
 motion=json.loads((ROOT/'pl_motion/MOTION_SIM_RESULTS.json').read_text());dma=json.loads((ROOT/'pl_dma/MOTION_DMA_SIM_RESULTS.json').read_text());sta=json.loads((ROOT/'pl_dma/MOTION_SOC_RESULTS.json').read_text())
 if motion['status']!='PASS' or dma['status']!='PASS' or not dma['probe_regression']:raise RuntimeError('required simulation absent')
 if not sta['stages']['route']['timing_pass'] or sta['critical_warnings']:raise RuntimeError('routed timing / critical diagnostics failed')
 if sta['clock_period_ns']!=10:raise RuntimeError('clock differs')
 source_commit=release['source_commit']
 subprocess.run(['git','cat-file','-e',source_commit+'^{commit}'],cwd=ROOT,check=True)
 for n,d in release['source_sha256_lf'].items():
  blob=subprocess.check_output(['git','show',source_commit+':'+n],cwd=ROOT)
  if hashlib.sha256(blob.replace(b'\r\n',b'\n')).hexdigest()!=d:raise RuntimeError('commit blob differs '+n)
 print('PASS fixed motion source/IP/evidence, generated definitions/wiring, real-IP/probe simulation and routed 100MHz')
if __name__=='__main__':main()
