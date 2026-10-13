"""Read-only GPIO/Golden identity gate for the coordinate BSP candidate."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 r=json.loads((ROOT/'pl_motion/GPIO_RELEASE.json').read_text(encoding='utf-8'))
 assert r['source_commit']=='df17b4ebd6e358d6626a227b5c0c152c1f6cb9ed'
 for n,h in r['source_sha256_lf'].items():
  assert hashlib.sha256((ROOT/n).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==h,n
 for n,h in r['evidence_sha256'].items():assert sha(ROOT/n)==h,n
 for n,h in r['vendor_ip_sha256'].items():assert sha(Path(n))==h,n
 m=json.loads((ROOT/'golden_model/baseline/manifest.json').read_text(encoding='utf-8-sig'))
 for x in m['files']:assert sha(ROOT/'golden_model/baseline'/x['file'])==x['sha256'],x['file']
 for script in ['pl_interface/generate.py','pl_dma/generate_motion.py','pl_motion/generate_scope.py']:
  subprocess.run(['python',str(ROOT/script),'--check'],check=True,cwd=ROOT)
 print('PASS read-only GPIO source/release/IP/evidence and Golden baseline gate')
if __name__=='__main__':main()
