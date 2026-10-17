"""Compare complete actual-top reports and exact routed pin inventories."""
import argparse,json,re,sys,hashlib
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[2];BASE=R/'pl_safety/evidence/predecode_top7_paused'
sys.path.insert(0,str(R/'pl_rs485/optimization/round2'));from analyze_top import paths
PAT={'lut6':r'^#lut6\s+','slice':r'^#slice\s+','slice_reg':r'^  #slice reg\s+','pad_reg':r'^  #pad reg\s+','eram':r'^#eram\s+','dsp':r'^#dsp\s+','io':r'^#IO\s+','gclk':r'^#gclk\s+','sclk':r'^#sclk\s+','lclk':r'^#lclk\s+','pll':r'^#pll\s+','ioclk':r'^#ioclk\s+','mlclk':r'^#mlclk\s+'}
def resources(d):
 t=(d/'route.area').read_text();rs={}
 for k,p in PAT.items():
  m=re.search(p+r'(\d+)(?:\s+out of\s+(\d+))?',t,re.M);assert m,k
  used=int(m[1]);total=int(m[2]) if m[2] else None;rs[k]={'used':used,'total':total,'percent':used*100/total if total else None,'remaining':total-used if total else None}
 return rs

def stage(d,n):
 t=(d/(n+'.timing')).read_text();ps=paths(t);setup=sorted((p for p in ps if p['Check Type'] in ['setup','recovery']),key=lambda p:float(p['Slack'][:-2]));hold=sorted((p for p in ps if p['Check Type'] in ['hold','removal']),key=lambda p:float(p['Slack'][:-2]))
 for p in ps:
  level=p.get('Logic Level','');adder=re.search(r'\bADDER\s*=\s*(\d+)',level);p['adder_stages_tool_reported']=int(adder[1]) if adder else 0
  delay=p.get('Data Path Delay','');cell=re.search(r'cell\s+([\d.]+)ns',delay);net=re.search(r'net\s+([\d.]+)ns',delay)
  p['cell_delay_ns']=float(cell[1]) if cell else None;p['net_delay_ns']=float(net[1]) if net else None
 worst_slack=setup[0]['Slack'] if setup else None
 hit=re.search(r'^Slack\s*:\s*'+re.escape(worst_slack or 'NONE'),t,re.M)
 groups=re.findall(r'^Path Group\s*:\s*([^\n]+)',t[:hit.start()] if hit else '',re.M)
 return {'worst_path_group':groups[-1] if groups else None,'setup_ns':float(re.search(r'SWNS:\s*([-\d.]+)ns',t)[1]),'hold_ns':float(re.search(r'HWNS:\s*([-\d.]+)ns',t)[1]),'stns_ns':float(re.search(r'STNS:\s*([-\d.]+)ns',t)[1]),'htns_ns':float(re.search(r'HTNS:\s*([-\d.]+)ns',t)[1]),'coverage':re.search(r'STA coverage\s*:\s*(.*)',t)[1],'reported_worst_setup':setup[:10],'reported_worst_hold':hold[:3],'path_group_violation_statistics':[x.strip() for x in t.splitlines() if 'Viol Endpoints' in x]}
def routing(d):
 logs=pnr_logs(d);place=next((x for p,x in logs if p.name=='parent_place_run.log'),None)
 route=next((x for p,x in reversed(logs) if 'finish command "route"' in x),logs[-1][1])
 if place is None:place=next((x for p,x in logs if 'most congested 1%' in x),route)
 return {'pnr_log_sources':[str(p) for p,t in logs],'local_congestion':[x.strip() for x in place.splitlines() if 'most congested 1%' in x],'wire_length':re.findall(r'\|\s*Wire length\s*\|\s*(\d+)',route)[-1:],'route_iterations':[x.strip() for x in route.splitlines() if 'Path[overflow' in x]}

def pnr_logs(d):
 result=[]
 for name in ['parent_place_run.log','parent_full_run.log','run.log']:
  p=d/name
  if p.exists():
   t=p.read_text(errors='replace')
   if name=='parent_place_run.log':t=t.split('RUN-1002 : start command "route"')[0]
   result.append((p,t))
 return result

def warnings(d):
 result={}
 for line in '\n'.join(t for p,t in pnr_logs(d)).splitlines():
  if 'WARNING' not in line:continue
  hit=re.search(r'\b([A-Z]+-\d+)\b',line);code=hit[1] if hit else 'UNCODED'
  item=result.setdefault(code,{'occurrences':0,'examples':[]});item['occurrences']+=1
  if line not in item['examples'] and len(item['examples'])<8:item['examples'].append(line)
 return result

def check_diagnostics(d):
 t=(d/'route.check').read_text();top=t.split('1. checking nets')[0]
 return {name.strip():int(count) for name,count in re.findall(r'^\d+\.\s+(.*?)\((\d+)\)\s+\((?:HIGH|MEDIUM|LOW)\)',top,re.M)}

def clocks(d):
 t=(d/'route.timing').read_text();section=t.split('Clock Summary',1)[1].split('Notes',1)[0]
 return {name:{'frequency_mhz':float(freq),'loads':int(loads)} for freq,loads,name in re.findall(r'^\s+clk\d+:\s+([\d.]+)\s+(\d+)\s+(\S+)',section,re.M)}

def control_nets(path):
 rows=[x.split('\t') for x in path.read_text().splitlines()[1:]];result={}
 families=['pulse_event','phase_time','phase_deadline','search_at','search_before','count_full','checked_bad','stop_kernel','rx_error','rx_error_candidate','rx_without_dma','non_dma_abort']
 patterns={f:re.compile('/'+f+r'(?:\[|_|$)') for f in families};assigned={f:[] for f in families}
 for n,flat,drivers,clock in rows:
  if not n.startswith('control/core/fabric/dma_core/motion/'):continue
  for f in sorted(families,key=len,reverse=True):
   if patterns[f].search(n):assigned[f].append({'name':n,'loads':int(flat)-int(drivers),'drivers':int(drivers),'clock':clock});break
 for family in families:
  ns=assigned[family]
  ns.sort(key=lambda x:x['loads'],reverse=True)
  result[family]={'matching_nets':len(ns),'max_loads':max((n['loads'] for n in ns),default=None),'nets':ns}
 return result
def net_stats(path):
 m=json.loads(path.read_text());assert m['passed'];r={}
 for category in ['ordinary_data','ce','reset','clock','constant']:
  ns=[n for n in m['nets'] if n['category']==category]
  r[category]={'nets_ge64':len(ns),'max_loads':max((n['loads'] for n in ns),default=0),'bins':{f'{lo}-{hi}':sum(lo<=n['loads']<=hi for n in ns) for lo,hi in [(64,127),(128,255),(256,511),(512,1023),(1024,1000000)]},'top_nets':ns[:4]}
 return r

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--build',required=True);ap.add_argument('--pins',required=True);ap.add_argument('--nets',required=True);ap.add_argument('--warnings');a=ap.parse_args();d=R/'pl_safety/build'/a.build
 for n in ['gp/gp.sdc','gp/gp.adc','gp/ps-generated-properties.tcl']:
  assert (d/n).read_bytes()==(BASE/n).read_bytes(),n
 before=resources(BASE);after=resources(d);summary=json.loads((d/'summary.json').read_text());assert summary['threads']==16
 m={'baseline':'5ccd875/predecode_top7','build':a.build,'resources_before':before,'resources_after':after,'absolute_delta':{k:after[k]['used']-before[k]['used'] for k in before},'timing_before':{n:stage(BASE,n) for n in ['gate','place','route']},'timing_after':{n:stage(d,n) for n in ['gate','place','route']},'routing_before':routing(BASE),'routing_after':routing(d),'high_net_scope':'all nets >=64 loads; categorized by physical load pin type; clock property takes priority; mixed load counts retained','fanout_before':net_stats(E/'baseline_pins2/result.json'),'fanout_after':net_stats(E/a.pins/'result.json'),'original_constraints_byte_equal':True,'target_pass':summary['timing_target_pass'],'signoff_pass':False}
 m['check_timing_before']=check_diagnostics(BASE);m['check_timing_after']=check_diagnostics(d)
 m['check_timing_delta']={k:m['check_timing_after'][k]-v for k,v in m['check_timing_before'].items()}
 m['clocks_before']=clocks(BASE);m['clocks_after']=clocks(d)
 assert {k:v['frequency_mhz'] for k,v in m['clocks_before'].items()}=={k:v['frequency_mhz'] for k,v in m['clocks_after'].items()},'Clock identities/frequencies changed'
 assert json.loads((E/a.nets/'result.json').read_text())['build']==a.build
 m['control_net_families_before']=control_nets(E/'baseline_nets1/nets.tsv');m['control_net_families_after']=control_nets(E/a.nets/'nets.tsv')
 m['control_net_scope']='Exact surviving logical name families plus equivalent physical copies; absent name is N/A, never evidence of a deleted function or zero fanout.'
 m['warnings_before']=warnings(BASE);m['warnings_after']=warnings(d);m['new_warning_codes']=sorted(set(m['warnings_after'])-set(m['warnings_before']))
 if m['new_warning_codes']:
  assert a.warnings,'New diagnostic codes require explicit final-DB reconciliation'
  review=json.loads((E/a.warnings/'result.json').read_text());assert review['passed'] and review['build']==a.build and review['route_db_sha256']==hashlib.sha256((d/'route.db').read_bytes()).hexdigest()
  assert set(m['new_warning_codes'])<=set(review['reviewed_codes']),('Unexplained diagnostics',m['new_warning_codes'])
  m['warning_review']=review;m['warning_review_tag']=a.warnings
 (E/('comparison_'+a.build+'.json')).write_text(json.dumps(m,indent=2)+'\n')
 print(json.dumps({'delta':m['absolute_delta'],'route':m['timing_after']['route'],'target_pass':m['target_pass']},indent=2))
if __name__=='__main__':main()
