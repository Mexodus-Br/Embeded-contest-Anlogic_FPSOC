"""Reject stale source/IP/timing evidence before BSP integration."""
import hashlib,json,subprocess,sys
from pathlib import Path
from prepare_ip import ROOT,prepare,digest
for script,args in [('pl_interface/generate.py',['--check']),('pl_dma/generate_top.py',['--check']),('pl_dma/generate_shared.py',['--check']),('pl_dma/generate_dts.py',['--check'])]:
 subprocess.run([sys.executable,str(ROOT.parent/script),*args],cwd=ROOT.parent,check=True)
td=json.loads((ROOT/'TD_RESULTS.json').read_text());sim=json.loads((ROOT/'SHARED_SIM_RESULTS.json').read_text());ip=prepare()
if td['ip']!=ip or sim['real_ip']!=ip:raise SystemExit('IP/schema identity changed')
for n,expected in td['inputs'].items():
 p=ROOT.parent/n if n!='shared_header' else ROOT.parent/'pl_interface/generated/interface_defs.vh'
 if digest(p)!=expected:raise SystemExit('TD source changed '+n)
for record in [sim,json.loads((ROOT/'SIM_RESULTS.json').read_text())]:
 if record['real_ip']!=ip:raise SystemExit('simulation IP changed')
 for n,expected in record['source_sha256'].items():
  if digest(ROOT/n)!=expected:raise SystemExit('simulation source changed '+n)
if sim['status']!='PASS' or not sim.get('gp_regression') or not td['route']['pass']:raise SystemExit('required validation missing')
for name in ['SIM_RESULTS.json','COMPONENT_RESULTS.json','REGRESSION_RESULTS.json']:
 if json.loads((ROOT/name).read_text())['status']!='PASS':raise SystemExit('failed/missing '+name)
if json.loads((ROOT/'HP0_PORTS.json').read_text())['status']!='ACTUAL_GENERATED_HP0_PORTS_AUDITED':raise SystemExit('HP0 audit missing')
soc=json.loads((ROOT/'SOC_REFERENCE_RESULTS.json').read_text())
if soc['ip']!=ip or soc['critical_warnings'] or not soc['stages']['route']['timing_pass']:raise SystemExit('real PS reference incomplete')
for n,expected in soc['inputs'].items():
 if digest(ROOT.parent/n)!=expected:raise SystemExit('PS reference source changed '+n)
if soc['shared_header']!=digest(ROOT.parent/'pl_interface/generated/interface_defs.vh'):raise SystemExit('PS reference definitions changed')
print('PASS delivery sources, vendor IP, unique schema, real-IP simulation and routed 10ns evidence match')
