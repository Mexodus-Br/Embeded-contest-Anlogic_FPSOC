"""Archive full-top reports without databases/images; never overwrite evidence."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'pl_safety'
TESTS=['rxcarry_units1','rxcarry_phases1','inputs_freeze1','overflow_frozen1','router_final1','rxcarry_real1','timing_regress1','rxcarry_resource1','rxcarry_equivalence1']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--build',required=True);ap.add_argument('--tag');a=ap.parse_args()
 b=D/'build'/a.build;summary=json.loads((b/'summary.json').read_text());out=D/'evidence'/(a.tag or a.build)
 out.mkdir(exist_ok=False)
 paths=['inputs.json','summary.json','run.tcl','run.log','system.al','system/hdl/system_wrapper.v','gp/gp.adc','gp/gp.sdc','gp/ps-generated-properties.tcl','gate.area','gate.timing','place.timing','route.timing','route.area','route.check']
 paths+=sorted(p.name for p in b.iterdir() if p.is_file() and (p.name.startswith('td_') and p.suffix in ['.log','.logw'] or p.suffix=='.qor'))
 for n in paths:
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(b/n,p)
 # This TD version prints route status to stdout even with -file.
 log=(b/'run.log').read_text(errors='replace')
 match=re.search(r'RUN-1002 : start command "report_route_status.*?RUN-1003 : finish command "report_route_status[^\n]*',log,re.S)
 assert match,'Missing original route status output'
 (out/'route_status.log').write_text(match[0]+'\n')
 trials=[]
 for trial in sorted((D/'build').iterdir()):
  if not trial.is_dir() or trial==b or not (trial/'run.tcl').exists():continue
  entry={'tag':trial.name,'completed':(trial/'summary.json').exists()}
  if entry['completed']:
   previous=json.loads((trial/'summary.json').read_text())
   entry['route_timing_pass']=all(previous['stages']['route'][k]>=0 for k in ['setup_ns','hold_ns'])
  for n in ['run.tcl','run.log','inputs.json','summary.json','gate.area','gate.timing','place.timing','route.timing']:
   if (trial/n).exists():
    p=out/'prior_build_attempts'/trial.name/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(trial/n,p)
  trials.append(entry)
 checks={}
 for name in TESTS:
  test=json.loads((D/'evidence'/name/'result.json').read_text());assert test['passed'],name
  for p,h in test.get('source_sha256',{}).items():assert sha(R/p)==h,(name,p)
  checks[name]={'passed':True,'result_sha256':sha(D/'evidence'/name/'result.json')}
 # Independently index every retained failed/incomplete trial, without excluding it.
 prior_tests=[]
 for result in sorted((D/'evidence').glob('*/result.json')):
  t=json.loads(result.read_text())
  if not t.get('passed'):prior_tests.append({'tag':result.parent.name,'result_sha256':sha(result),'failure':t.get('failure','see original logs')})
 logs='\n'.join(p.read_text(errors='replace') for p in (D/'evidence/rxcarry_phases1').glob('mode*.log'))
 latency={}
 for key in ['pad_qualified','executor_inhibit_bound','qualified_drain','qualified_en_off']:
  values=[int(v) for v in re.findall(key+r'=(\d+)',logs)]
  latency[key]={'min_cycles':min(values),'max_cycles':max(values)}
 area=(b/'route.area').read_text()
 resources={k:int(re.search(pattern,area,re.M)[1]) for k,pattern in {
  'lut6_equivalent':r'^#lut6\s+(\d+)', 'slices':r'^#slice\s+(\d+)',
  'registers_total':r'^#reg\s+(\d+)', 'slice_registers':r'^  #slice reg\s+(\d+)',
  'pad_registers':r'^  #pad reg\s+(\d+)', 'eram':r'^#eram\s+(\d+)',
  'dsp':r'^#dsp\s+(\d+)', 'io':r'^#IO\s+(\d+)'}.items()}
 timing_pass=all(summary['stages']['route'][k]>=0 for k in ['setup_ns','hold_ns'])
 data={'passed':True,'meaning':'RTL self-checks and complete resource/STA run; NOT hardware release signoff','timing_100mhz_pass':timing_pass,'wns_target_ns_exclusive':1.0,'timing_target_pass':summary['stages']['route']['setup_ns']>1.0 and summary['stages']['route']['hold_ns']>=0,'threads':summary.get('threads','historical_default'),'resources':resources,'tests':checks,'full_top':summary,'fixture_latency':latency,'prior_build_attempts':trials,'prior_failed_tests':prior_tests,'reports_sha256':{p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}}
 (out/'result.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'archived':str(out),'latency':latency,'full_top':summary},indent=2))
if __name__=='__main__':main()
