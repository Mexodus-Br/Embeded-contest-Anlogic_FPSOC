"""Verify generated constants and evidence identity, then record immutable hashes."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--simulation',default='sim_release');a=ap.parse_args()
    old={p.name:digest(p) for p in (ROOT/'generated').glob('*')}
    subprocess.run([sys.executable,str(ROOT/'tools/generate.py')],check=True)
    assert old=={p.name:digest(p) for p in (ROOT/'generated').glob('*')},'generated files stale'
    td=json.loads((ROOT/'evidence/td/summary.json').read_text())
    sim=json.loads((ROOT/'evidence'/a.simulation/'manifest.json').read_text())
    for report in [td,sim]:
        for k,h in report['source_sha256'].items():assert digest(ROOT/k)==h,'stale evidence: '+k
    assert td['route']['pass'] and len(sim['passed'])==3
    paths=[ROOT/'schema.json',ROOT/'PROTOCOL_CONTRACT.md',ROOT/'build_td.py']
    paths += [p for folder in ['rtl','generated','tests','tools'] for p in (ROOT/folder).glob('*') if p.is_file()]
    data={'identity':'servo42c-readonly-v1','source_sha256':{p.relative_to(ROOT).as_posix():digest(p) for p in paths},
          'simulation':a.simulation,'seed':sim['seed'],'td_summary_sha256':digest(ROOT/'evidence/td/summary.json'),
          'boundaries':'standalone PL collector; no board download or system integration'}
    (ROOT/'evidence/identity.json').write_text(json.dumps(data,indent=2)+'\n')
    print('PASS generated identity and final simulation/TD source hashes')
if __name__=='__main__':main()
