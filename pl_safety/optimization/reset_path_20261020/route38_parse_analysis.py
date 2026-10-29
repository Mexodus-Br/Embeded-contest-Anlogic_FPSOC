"""Parse physical load pin classes/coordinates and near-critical routed arcs."""
import argparse,collections,csv,json,re
from pathlib import Path
E=Path(__file__).resolve().parent

def paths(file):
 t=file.read_text();rows=[]
 for b in re.split(r'(?=Slack\s+:)',t):
  if not re.match(r'Slack\s+:',b) or not re.search(r'Check Type\s+: setup',b):continue
  def field(k):return re.search(r'^'+re.escape(k)+r'\s*:\s*(.+)',b,re.M)[1]
  d=re.search(r'Data Path Delay\s+: ([\d.]+)ns \(cell ([\d.]+)ns .*?net ([\d.]+)ns',b)
  r=dict(file=file.name,slack_ns=float(field('Slack').removesuffix('ns')),
   start=field('Begin Point').split(' (')[0],end=field('End Point').split(' (')[0],
   cell_ns=float(d[2]),net_ns=float(d[3]),data_ns=float(d[1]),
   levels=field('Logic Level'),max_fanout=int(field('Max Fanout')),arcs=[])
  if 'clk2q' not in b:
   rows.append(r);continue
  text=b[b.index('clk2q'):];text=text[:text.index('Arrival')];lines=text.splitlines()
  driver=None;loc=None
  for i,line in enumerate(lines):
   m=re.match(r'(?:clk2q|LUT\w*|ADDER|PAD.*?|ERAM\S*)\s+(x\d+y\d+(?:z\d+)?)\s+.*?pin:\s*(\S+)',line)
   if m:loc=m[1];driver=m[2]
   m=re.match(r'net \(fo=(\d+)\)\s+([\d.]+)\s+[\d.]+\s+net: (.*?),\s+',line)
   if m and driver:
    sink=re.search(r'pin:\s*(\S+)',lines[i+1]);assert sink
    sl=re.search(r'\b(x\d+y\d+(?:z\d+)?)\b',lines[i+2])
    r['arcs'].append(dict(net=m[3],delay_ns=float(m[2]),fanout=int(m[1]),driver=driver,
     sink=sink[1],driver_location=loc,sink_location=sl[1] if sl else None))
  rows.append(r)
 return rows

def main():
 p=argparse.ArgumentParser();p.add_argument('--tag',required=True);a=p.parse_args();o=E/a.tag
 assert json.loads((o/'result.json').read_text())['passed']
 table=list(csv.DictReader((o/'nets.tsv').open(),delimiter='\t'));lookup={r['name']:r for r in table}
 log=(o/'audit.log').read_text(errors='replace');nets=[]
 for block in log.split('NET_AUDIT_BEGIN ')[1:]:
  name,body=block.split('\n',1);body=body.split('NET_AUDIT_END ')[0];name=name.strip();row=lookup[name]
  def pins(s):return re.findall(r'RUN-1001 :\s+\d+\s+\|\s+(\S+)\s+\|[^\n]*',s)
  loads=body.split('Load pin(s):')[1];ps=pins(loads)
  drivers=pins(body.split('Driver pin(s):')[1].split('Load pin(s):')[0])
  assert len(ps)==int(row['flat_pins'])-int(row['drivers']),(name,len(ps),row)
  assert len(drivers)==int(row['drivers'])
  cats=collections.Counter()
  for pin in ps:
   t=pin.rsplit('.',1)[-1].lower()
   k='clock' if re.fullmatch(r'(?:clk[ab]?|[ows]?s?clk|clkin(?:\[.*)?)',t) else 'ce' if re.fullmatch(r'(?:ce[a-d]?|ce\[\d+\])',t) else 'async_reset' if t=='asr' else 'sync_reset' if t=='ssr' else 'other'
   cats[k]+=1
  category='clock' if row['clock']=='1' else 'constant' if re.search(r'is_(?:const0|const1|tielow)\s+\|\s+True',body) else 'reset' if cats['async_reset'] or cats['sync_reset'] else 'ce' if cats['ce'] else 'data'
  xy=[tuple(map(int,m)) for m in re.findall(r'\|\s*\[\s*(\d+)\s+(\d+)\s*\]',loads)]
  bbox=[min(x for x,y in xy),min(y for x,y in xy),max(x for x,y in xy),max(y for x,y in xy)] if xy else None
  nets.append(dict(name=name,loads=len(ps),category=category,pin_types=dict(cats),driver_pins=drivers,load_bbox=bbox))
 allpaths=[p for f in [o/'expanded.timing',*sorted(o.glob('axis*.timing'))] for p in paths(f)]
 endpoint=[]
 for f in sorted(o.glob('axis*.timing')):
  ps=paths(f);assert ps;endpoint.append(min(ps,key=lambda x:x['slack_ns']))
 arcs={}
 for p in allpaths:
  if p['slack_ns']>=1:continue
  for arc in p['arcs']:
   key=(arc['driver'],arc['sink'])
   if key not in arcs or arc['delay_ns']>arcs[key]['delay_ns']:arcs[key]=arc
 summary={}
 for category in ['data','ce','reset','clock','constant']:
  selected=sorted([n for n in nets if n['category']==category],key=lambda n:n['loads'],reverse=True)
  summary[category]=dict(nets_ge64=len(selected),max_loads=selected[0]['loads'] if selected else 0,top=selected[:5])
 result=dict(build='rtl_path38',hashes_computed=False,threads=16,read_only=True,
  high_net_threshold=64,active_driven_net_count=len(table),high_nets=sorted(nets,key=lambda n:n['loads'],reverse=True),
  fanout_summary=summary,axis_endpoints=endpoint,
  unique_nearcritical_arcs=sorted(arcs.values(),key=lambda n:n['delay_ns'],reverse=True),
  setup_paths_reported=len(allpaths),nearcritical_reported_path_count=sum(p['slack_ns']<1 for p in allpaths))
 (o/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
 print('HIGH FANOUT',[(k,v['nets_ge64'],v['max_loads']) for k,v in summary.items()])
 for k in ['data','ce','reset']:
  print(k,json.dumps(summary[k]['top'][:2]))
 print('LONG ARCS',json.dumps(result['unique_nearcritical_arcs'][:9],indent=2))
 print('AXES',[(r['file'],r['slack_ns'],r['net_ns']) for r in endpoint])
if __name__=='__main__':main()
