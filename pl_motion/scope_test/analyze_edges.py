"""Independent edge/count oracle for scope captures; no motion RTL changes."""
import csv,json,re,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
def expected():
 c=json.loads((OUT/'CONFIG.json').read_text(encoding='utf-8'))
 delta=[b-a for a,b in zip(c['origin_steps'],c['endpoint_steps'])]
 counts=[abs(x) for x in delta];master=max(counts);guard=1002;cycles=c['duration_tick']*100
 rows=[]
 for phase in (1,2):
  acc=[master-n for n in counts]
  for slot in range(master):
   rising=guard+slot*(cycles-guard)//master
   for axis,n in enumerate(counts):
    acc[axis]+=n
    if n and acc[axis]>=master:
     acc[axis]-=master
     direction=int(delta[axis]>0) if phase==1 else int(delta[axis]<0)
     for kind,t in [('rise',rising),('fall',rising+500)]:
      rows.append({'phase':phase,'axis':axis,'slot':slot,'edge':kind,'relative_cycle':t,'relative_us':t/100,'dir':direction})
 return c,rows
def main():
 c,expected_rows=expected()
 with (OUT/'expected_edges.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(expected_rows[0]));w.writeheader();w.writerows(expected_rows)
 sim=ROOT/'pl_motion/build/scope_dma'
 if not (sim/'observed_edges.csv').exists():sim=OUT/'evidence'
 p=sim/'observed_edges.csv'
 observed=list(csv.DictReader(p.open()))
 matches=[]
 for phase in (1,2):
  actual=[(int(x['axis']),int(x['relative_cycle']),x['value']) for x in observed if x['signal']=='step' and int(x['phase'])==phase]
  wanted=[(x['axis'],x['relative_cycle'],'1' if x['edge']=='rise' else '0') for x in expected_rows if x['phase']==phase]
  assert sorted(actual)==sorted(wanted),'phase edge oracle differs '+str(phase)
  matches.append({'phase':phase,'step_counts':[sum(x['axis']==a and x['edge']=='rise' and x['phase']==phase for x in expected_rows) for a in range(4)],'edge_table_matches':True})
 stop=[x for x in observed if x['signal']=='step' and int(x['phase'])==3]
 for axis in range(3):
  a=[x for x in stop if int(x['axis'])==axis];assert len(a)==2
  assert a[0]['value']=='1' and a[1]['value']=='0' and int(a[1]['cycle'])-int(a[0]['cycle'])==500
 assert not any(int(x['axis'])==3 and x['signal']=='step' for x in observed)
 # Check minimum GPIO guards independently from the slot/count oracle.
 direction=[1]*4;enable=[0]*4;high=[False]*4
 last_dir=[0]*4;last_en=[0]*4;last_fall=[None]*4
 margins={'dir_setup_cycles':[],'en_setup_cycles':[],'dir_hold_cycles':[],'en_disable_cycles':[]}
 for x in observed:
  axis=int(x['axis']);cycle=int(x['cycle']);value=int(x['value']);signal=x['signal']
  if signal=='dir':
   assert not high[axis],'DIR changes during high pulse'
   if last_fall[axis] is not None:
    gap=cycle-last_fall[axis];assert gap>=500;margins['dir_hold_cycles'].append(gap)
   direction[axis]=value;last_dir[axis]=cycle
  elif signal=='en':
   if not value and last_fall[axis] is not None:
    gap=cycle-last_fall[axis];assert gap>=500 and not high[axis];margins['en_disable_cycles'].append(gap)
   enable[axis]=value;last_en[axis]=cycle
  elif signal=='step':
   if value:
    assert enable[axis] and cycle-last_dir[axis]>=500 and cycle-last_en[axis]>=500
    assert direction[axis]==(int(axis==2) if x['phase']=='2' else int(axis!=2))
    margins['dir_setup_cycles'].append(cycle-last_dir[axis]);margins['en_setup_cycles'].append(cycle-last_en[axis])
   else:last_fall[axis]=cycle
   high[axis]=bool(value)
 assert enable[:3]==[0,0,0] and not any(high)
 log=(sim/'simulation.log').read_text(encoding='utf-8')
 assert 'PASS scope_gpio' in log and len(re.findall(r'duration_cycles=50000000',log))==2
 snaps={int(p):([int(x) for x in pos.split(',')],[int(x) for x in pulses.split(',')],int(end))
        for p,end,pos,pulses in re.findall(r'SNAP phase=(\d+).*?ends=(\d+).*?pos=([\d,-]+) pulse=([\d,]+)',log)}
 assert snaps[1]==([-1089,-966,-1213],[1,124,123],1)
 assert snaps[2]==([-1090,-1090,-1090],[2,248,246],2)
 assert snaps[3]==([-1089,-1089,-1091],[3,249,247],2)
 result={'status':'PASS','fixed_vector':c,'delta':[1,124,-123,0],'step_counts':[1,124,123,0],'outbound_dir':[1,1,0],'return_dir':[0,0,1],
 'phases':matches,'stop_counts':[1,1,1,0],'stop_high_cycles':500,'first_corresponding_edges_skew_cycles':0,'duration_cycles':50000000,
 'guard_cycles':1002,'slot_period_quotient':49998998//124,'slot_period_remainder':49998998%124,
 'gp_snapshot_counts_positions_end':snaps,
 'minimum_observed_gpio_guards_cycles':{k:min(v) for k,v in margins.items()},'final_en':[0,0,0,0],
 'reference':'RTL logical output only; GPIO/driver electrical waveform not measured',
 'observed_csv_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'vcd_sha256':hashlib.sha256((p.parent/'scope_outputs.vcd').read_bytes()).hexdigest()}
 (OUT/'EDGE_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print('PASS independent scope edge oracle: outgoing/return exact counts, cycles and STOP high width')
if __name__=='__main__':main()
