"""Repeatable host-only suite. No device access, deployment or hashes."""
from pathlib import Path
import json, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/partner'
OUT.mkdir(parents=True,exist_ok=True)
steps=[('build',['tools/build_ps.py','--server']),('schema',['tools/ps_schema.py','--check']),('reference',['tools/verify_partner.py']),('core',['tests/ps_core.py']),('service',['tests/ps_service.py']),('boundary',['tests/ps_boundary.py'])]
records=[]
for name,args in steps:
    start=time.monotonic()
    # Preserve every run, including a failed attempt, without overwriting evidence.
    filename=name+'-'+str(time.time_ns())+'.log'
    with (OUT/filename).open('wb') as output:
        result=subprocess.run([sys.executable,'-B',*args],cwd=ROOT,stdout=output,stderr=subprocess.STDOUT)
    records.append(dict(name=name,exit_code=result.returncode,seconds=time.monotonic()-start,log=filename))
    print(name,result.returncode,flush=True)
report=dict(passed=all(r['exit_code']==0 for r in records),scope='host_only',steps=records)
(OUT/'host_checks_report.json').write_text(json.dumps(report,indent=2))
sys.exit(not report['passed'])
