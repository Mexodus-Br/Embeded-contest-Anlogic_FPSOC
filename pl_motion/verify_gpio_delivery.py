"""Verify additive GPIO delivery and retain the sealed internal release identity."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CHANGED={'pl_dma/generate_motion.py','pl_dma/rtl/motion_dma_lite_top.v','pl_dma/rtl/motion_shared_lite_top.v','pl_dma/rtl/motion_gp_full_top.v','pl_dma/rtl/motion_gp_ps_top.v'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def lf(b):return hashlib.sha256(b.replace(b'\r\n',b'\n')).hexdigest()
def baseline():
 old=json.loads((ROOT/'pl_motion/MOTION_RELEASE.json').read_text(encoding='utf-8'))
 for n,h in old['source_sha256_lf'].items():
  b=subprocess.check_output(['git','show',old['source_commit']+':'+n],cwd=ROOT);assert lf(b)==h,n
  if n not in CHANGED:assert lf((ROOT/n).read_bytes())==h,'baseline algorithm/ABI changed '+n
 for n,h in old['evidence_sha256'].items():assert sha(ROOT/n)==h,'old evidence changed '+n
 for n,h in old['vendor_ip_sha256'].items():assert sha(Path(n))==h,'installed IP changed '+n
 for n in CHANGED-{'pl_dma/generate_motion.py'}:
  text=(ROOT/n).read_text(encoding='utf-8')
  assert 'motion_step' in text and 'motion_dir' in text and 'motion_en' in text
  assert not re.search(r'assign\s+motion_(?:step|dir|en)\s*=\s*\w+\.',text),'hierarchical GPIO reference'
 for script,args in [('pl_interface/generate.py',['--check']),('pl_dma/generate_motion.py',['--check']),('pl_motion/generate_scope.py',['--check'])]:
  subprocess.run([sys.executable,str(ROOT/script),*args],cwd=ROOT,check=True)
 print('PASS original source commit/IP/ABI/evidence retained; only additive GPIO wiring changed')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--baseline-only',action='store_true');a=ap.parse_args();baseline()
 if a.baseline_only:return
 release=json.loads((ROOT/'pl_motion/GPIO_RELEASE.json').read_text(encoding='utf-8'))
 for n,h in release['source_sha256_lf'].items():
  assert lf((ROOT/n).read_bytes())==h,n
  assert lf(subprocess.check_output(['git','show',release['source_commit']+':'+n],cwd=ROOT))==h,'fixed GPIO commit differs '+n
 for n,h in release['evidence_sha256'].items():assert sha(ROOT/n)==h,n
 for n,h in release['vendor_ip_sha256'].items():assert sha(Path(n))==h,n
 for name in ['SIM_RESULTS','DEFAULT_RESULTS','REGRESSION_RESULTS','EDGE_RESULTS']:
  assert json.loads((ROOT/'pl_motion/scope_test'/f'{name}.json').read_text())['status']=='PASS',name
 sta=json.loads((ROOT/'pl_motion/scope_test/STA_RESULTS.json').read_text());assert sta['timing_pass'] and sta['clock_period_ns']==10 and not sta['critical_warnings']
 assert sta['check_timing_diagnostics']['no_clock']==0 and sta['check_timing_diagnostics']['output_delay_missing']==0
 assert json.loads((ROOT/'pl_motion/scope_test/IO_AUDIT_RESULTS.json').read_text())['status']=='PASS_WITH_REVIEWED_REMAINING_DIAGNOSTICS'
 index=json.loads((ROOT/'pl_motion/scope_test/evidence/index.json').read_text())
 for n,row in index.items():assert sha(ROOT/'pl_motion/scope_test/evidence'/n)==row['sha256'],n
 subprocess.run([sys.executable,str(ROOT/'pl_motion/scope_test/audit_gpio_sta.py')],cwd=ROOT,check=True)
 subprocess.run([sys.executable,str(ROOT/'pl_motion/scope_test/analyze_edges.py')],cwd=ROOT,check=True)
 print('PASS GPIO fixed source, 500ms real-DMA vectors, reference-speed2 physical GPIO STA and evidence')
if __name__=='__main__':main()
