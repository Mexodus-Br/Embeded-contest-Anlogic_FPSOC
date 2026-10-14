"""Reuse exact-board audit predicates without writing old published evidence."""
import argparse,hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'pl_rs485/optimization'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);a=ap.parse_args()
 E=O/('top_'+a.tag);m=json.loads((E/'inputs.json').read_text(encoding='utf-8'));W=R/'bsp/work'/m['work_dir']
 for n,h in m['inputs_sha256'].items():
  p=O/'baseline'/(Path(n).stem+'_baseline.v') if m['candidate'].get('mode','optimized')=='baseline_replay' and n in m['candidate']['changed_source_sha256'] else R/n
  assert sha(p)==h,('source changed during build',n)
 for n,h in m['project_inputs_sha256'].items():assert sha(W/n)==h,('project input changed during build',n)
 source=(R/'bsp/telemetry/audit_hardware.py').read_text(encoding='utf-8')
 # Only paths are adapted: all original actual-clock, pad, area, timing,
 # diagnostics and function-retention audit assertions remain present.
 old="R=Path(__file__).resolve().parents[2];W=R/'bsp/work/telemetry_soc_prj';E=R/'bsp/evidence/telemetry-hardware-20261014'"
 assert old in source
 source=source.replace(old,"R=Path("+repr(str(R))+ ");W=R/"+repr('bsp/work/'+m['work_dir'])+";E=R/"+repr(E.relative_to(R).as_posix()+'/reports'))
 source=source.replace("(R/'bsp/telemetry/hardware-review.json')","(E/'hardware-review.json')")
 (E/'audit_actual_top.py').write_text(source,encoding='utf-8')
 exec(compile(source,str(E/'audit_actual_top.py'),'exec'),{'__file__':str(E/'audit_actual_top.py')})
 before=json.loads((O/'baseline/manifest.json').read_text(encoding='utf-8'))['actual_top_review']
 after=json.loads((E/'reports/review.json').read_text(encoding='utf-8'))
 assert before['constraints_sha256']==after['constraints_sha256'],'constraints changed'
 for k in ('pad','gclk','sclk'):assert before['resources'][k]==after['resources'][k],k
 delta={k:after['resources'][k]['used']-v['used'] for k,v in before['resources'].items()}
 result={'baseline_commit':'7681c69','actual_top':'system_wrapper','before':before['resources'],'after':after['resources'],'delta_after_minus_before':delta,'slice_saved':-delta['slice'],'slice_percentage_points_saved':round(-delta['slice']*100/52480,4),'before_stages':before['stages'],'after_stages':after['stages'],'constraints_unchanged':True,'wrapper_unchanged':True,'timing_pass':after['timing_pass'],'signoff_pass':after['signoff_pass'],'candidate':m['candidate'],'hierarchy':after['hierarchy'],'congestion_before':before['congestion_lines'],'congestion_after':after['congestion_lines']}
 (E/'comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 assert after['timing_pass'],'100MHz route failed'
 if m['candidate'].get('mode','optimized')!='baseline_replay':assert result['slice_saved']>0,'No actual top Slice benefit'
 print('PASS exact actual-top comparison, Slice saved:',result['slice_saved'])
if __name__=='__main__':main()
