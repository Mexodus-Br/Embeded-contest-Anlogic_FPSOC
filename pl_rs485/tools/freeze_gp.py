"""Verify final evidence is tied to current sources, not earlier candidates."""
import hashlib,json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify_manifest(folder):
    m=json.loads((R/'evidence'/folder/'manifest.json').read_text())
    for n,h in m['source_sha256'].items():
        # Earlier generator/test helpers may be added after run; all recorded
        # sources must still match. Paths use / or Windows backslashes.
        if digest(R/n.replace('\\','/'))!=h:raise RuntimeError('stale '+folder+' '+n)
    return m
def main():
    for command in [['python',str(R.parent/'pl_interface/generate.py'),'--check'],['python',str(R/'tools/generate_gp.py'),'--check']]:
        subprocess.run(command,check=True)
    sim={name:verify_manifest(name) for name in ['sim_gp_final','sim_gp_legacy_release','sim_gp_multirate_release','software_gp_release']}
    td={}
    for name in ['td_gp_final','td_gp_fast_final']:
        e=R/'evidence'/name;m=json.loads((e/'summary.json').read_text())
        for n,h in m['source_sha256'].items():
            if digest(R/n.replace('\\','/'))!=h:raise RuntimeError('stale TD '+name+' '+n)
        if digest(e/'probe.v')!=m['fixture_sha256'] or digest(e/'clock.sdc')!=m['constraint_sha256']:raise RuntimeError('TD fixture')
        if not m['route']['pass'] or m['clock_MHz']!=100:raise RuntimeError('TD timing')
        td[name]=m
    baseline=json.loads((R/'evidence/identity_multirate.json').read_text())['source_sha256']
    for n in ['schema.json','rate_design.json','rtl/rs485_master.v','rtl/uart_tx.v','rtl/uart_rx.v','rtl/record_fifo.v','rtl/rs485_transaction.v','rtl/div_u64_u32.v']:
        if digest(R/n)!=baseline[n]:raise RuntimeError('retained source changed '+n)
    previous=json.loads(subprocess.check_output(['git','show','2792c66:pl_interface/schema.json'],cwd=R.parent))
    current=json.loads((R.parent/'pl_interface/schema.json').read_text(encoding='utf-8'));current.pop('rs485_gp_profiles')
    if previous!=current:raise RuntimeError('existing interface schema changed')
    old=subprocess.check_output(['git','show','2792c66:pl_rs485/rtl/rs485_multirate.v'],cwd=R.parent).decode().replace('\r\n','\n')
    new=(R/'rtl/rs485_multirate.v').read_text()
    new=new.replace('output wire [31:0] node_backoff_entries,\n output wire observe_push,output wire [255:0] observe_data,\n output wire [7999:0] observe_tasks,output wire [1279:0] observe_nodes);','output wire [31:0] node_backoff_entries);')
    a=new.index(' assign observe_push=push;');b=new.index(' genvar g;generate',a);new=new[:a]+new[b:]
    if new!=old:raise RuntimeError('collector delta exceeds read-only observation ports')
    files=[R/'GP_PROFILE_PROPOSAL.md',R/'GP_SERVICE_BUDGET.md',R/'RS485_GP_HANDOFF.md',R/'build_td.py',R/'schema.json',R/'rate_design.json',R.parent/'pl_interface/schema.json',R.parent/'pl_interface/generate.py']
    files += [p for d in ['rtl','generated','software','tests','tools'] for p in (R/d).glob('*') if p.is_file()]
    evidence=[p for name in ['sim_gp_final','sim_gp_legacy_release','sim_gp_multirate_release','software_gp_release','td_gp_final','td_gp_fast_final'] for p in (R/'evidence'/name).glob('*') if p.suffix not in ['.vvp','.exe']]
    evidence += [R/'evidence/GP_FAILURES.md',R/'evidence/GP_RESOURCE_AUDIT.json']
    artifact={'identity':'rs485-gp-v1','collector_baseline_commit':'2792c66','source_sha256':{str(p.relative_to(R)) if p.is_relative_to(R) else '../'+str(p.relative_to(R.parent)):digest(p) for p in files},
      'evidence_sha256':{p.relative_to(R).as_posix():digest(p) for p in evidence},'simulation':{k:v.get('passed') for k,v in sim.items()},
      'timing':{k:{s:v[s] for s in ['gate','place','route']} for k,v in td.items()},
      'retained_interface_schema_equal':True,'collector_observation_only_delta':True,'board_integrated':False}
    (R/'evidence/identity_gp.json').write_bytes((json.dumps(artifact,indent=2)+'\n').encode());print('PASS GP identity/evidence/compatibility freeze')
if __name__=='__main__':main()
