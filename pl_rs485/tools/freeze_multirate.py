"""Bind generated constants, final simulation and both TD profiles to source bytes."""
import hashlib,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    before={p.name:h(p) for p in (R/'generated').glob('*')}
    for script in ['generate.py','generate_rates.py']:
        subprocess.run([sys.executable,str(R/'tools'/script)],check=True)
    assert before=={p.name:h(p) for p in (R/'generated').glob('*')},'stale generated constants'
    sim=json.loads((R/'evidence/sim_mr_release/manifest.json').read_text())
    names=['td_multirate_release','td_multirate_fast_release']
    reports=[json.loads((R/'evidence'/n/'summary.json').read_text()) for n in names]
    for report in [sim]+reports:
        for k,v in report['source_sha256'].items():assert h(R/k)==v,'stale source: '+k
    for n,t in zip(names,reports):
        assert t['route']['pass'],'routed timing failed: '+n
        assert t['rate_design_sha256']==h(R/'rate_design.json'),'stale rate specification'
        assert t['fixture_sha256']==h(R/'evidence'/n/'probe.v'),'stale fixture'
        assert t['constraint_sha256']==h(R/'evidence'/n/'clock.sdc'),'stale SDC'
    baseline=json.loads((R/'evidence/identity.json').read_text())['source_sha256']
    for k in ['rtl/rs485_master.v','rtl/uart_tx.v','rtl/uart_rx.v','rtl/record_fifo.v']:
        assert baseline[k]==h(R/k),'v1 reference changed: '+k
    paths=[R/'schema.json',R/'rate_design.json',R/'MULTIRATE_HANDOFF.md',R/'MULTIRATE_DESIGN.md',R/'build_td.py']
    paths += [p for f in ['rtl','generated','tests','tools'] for p in (R/f).glob('*') if p.is_file()]
    result={'identity':'servo42c-multirate-rtl-v1','source_sha256':{p.relative_to(R).as_posix():h(p) for p in paths},
        'simulation':'sim_mr_release','seed':sim['seed'],'benches':sim['passed'],
        'td_evidence':{n:h(R/'evidence'/n/'summary.json') for n in names},
        'unchanged_v1_commit':'75a2080','scope':'independent RTL; no motion/GP/DMA/DDR/board integration'}
    (R/'evidence/identity_multirate.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS multi-rate generated/source/simulation/TD identity and unchanged v1 RTL')
if __name__=='__main__':main()
