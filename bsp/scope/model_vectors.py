"""Create ARM inputs and compare frozen host references without rewriting them."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--results',type=Path);a=p.parse_args()
v=json.loads((ROOT/'golden_model/vectors/firmware_host.json').read_text())['cases']
out=ROOT/'bsp/scope/vectors';out.mkdir(exist_ok=True)
if a.prepare:
 (out/'inputs.txt').write_bytes(('\n'.join(x['mode']+' '+' '.join(x['tokens']) for x in v)+'\n').encode())
 print('Prepared',len(v),'frozen cases')
if a.results:
 models=[json.loads(x) for x in (a.results/'model.jsonl').read_text().splitlines()]
 oracles=[json.loads(x) for x in (a.results/'oracle.jsonl').read_text().splitlines()]
 assert len(models)==len(oracles)==len(v)
 diff=[];extract=[];valid=0
 for case,m,o in zip(v,models,oracles):
  expected=case['expected'];valid+=m['valid']
  oracle_valid=all(x is not None for x in o['angles_rad']+o['absolute_steps'])
  if m['valid']!=oracle_valid:extract.append({'id':case['id'],'field':'valid','model':m['valid'],'oracle':oracle_valid})
  for field in ['angles_rad','absolute_steps']:
   got=m[field] if field=='angles_rad' or m['valid'] else o[field]
   if o[field]!=expected[field]:diff.append({'id':case['id'],'field':field,'host':expected[field],'arm_oracle':o[field]})
   if got!=o[field]:extract.append({'id':case['id'],'field':field,'arm_model':got,'arm_oracle':o[field]})
 result={'status':'PASS' if not diff and not extract else 'FAIL','numeric_profile':'ARM_AArch64_Linaro7.5_float32_double64_O0_no_fast_math_no_FMA',
 'cases':len(v),'valid':valid,'invalid':len(v)-valid,'cross_host_differences':diff,'arm_extraction_differences':extract,
 'integer_comparison':'exact; no tolerance or baseline update','golden_read_only':True}
 (a.results/'model-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['status','cases','valid','invalid']}));assert result['status']=='PASS','ARM difference gate failed; inspect all differences'
