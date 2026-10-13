"""Verify raw motion acceptance evidence; never rewrite raw logs."""
from pathlib import Path
import hashlib,json,re
B=Path(__file__).resolve().parents[1];E=B/'evidence'
def log(n):
 p=E/n;b=p.read_bytes();m=json.loads(p.with_suffix(p.suffix+'.json').read_text())
 assert hashlib.sha256(b).hexdigest()==m['sha256'] and len(b)==m['received_bytes'],n
 # Console printk can split a userspace line; normalize only in memory.
 t=b.decode(errors='replace').replace('\r','')
 t=re.sub(r'\[\s*\d+\.\d+\][^\n]*\n','',t)
 return t,m
def snapshot(t,tag):
 row=re.search(r'^SNAP '+tag+r' (.+)$',t,re.M)[1]
 return {k:int(v,16 if k in ('status','error','valid') else 10) for k,v in re.findall(r'(\w+)=(-?\w+)',row)}
def supply(n):
 t,m=log(n);assert m['script_exit']==0
 row=re.search(r'^SUPPLY_RESULT (.+)$',t,re.M)[1];v={k:int(x) for k,x in re.findall(r'(\w+)=(\d+)',row)}
 entries=[{k:int(x) for k,x in re.findall(r'(\w+)=(\d+)',r)} for r in re.findall(r'^SUPPLY (.+)$',t,re.M)]
 assert len(entries)==6400 and [x['batch'] for x in entries]==list(range(6400))
 assert max(x['gap_ns'] for x in entries)==v['max_success_gap_ns']
 assert v['points']==102432 and v['target_met']==1 and v['max_success_gap_ns']<=2000000
 assert all(x['closed_ns']>=x['ioc_ns']>=x['submit_ns'] for x in entries)
 v['batches']=len(entries);v['raw_sha256']=m['sha256'];v['script_exit']=m['script_exit']
 v['estimated_sample_margin_ns']=v['min_sampled_watermark']*100000-v['max_success_gap_ns']
 for k in ('gap_ns','submit_ns','ioc_ns','closed_ns'):
  a=sorted(x[k] for x in entries);v[k]={'min':a[0],'max':a[-1],'p99':a[int(.99*(len(a)-1))]}
 return v,t
old,_=supply('motion-board-accept-20261013-02.log')
fifo,t=supply('motion-supply-fifo50-20261013-01.log')
a=snapshot(t,'initial');z=snapshot(t,'sustained-END');expected=[0]*4;prior=[0]*4
for seq in range(102432):
 pos=[seq%40-20,seq%30-15,0,seq%10-5]
 for i in range(4):expected[i]+=abs(pos[i]-prior[i])
 prior=pos
assert [z['pos'+str(i)] for i in range(4)]==prior
actual=[z['pulse'+str(i)]-a['pulse'+str(i)] for i in range(4)]
assert actual==expected and z['accepted']==z['active']==z['done']==102431
assert z['error']==0 and z['buffered']==0 and z['ends']==a['ends']+1
irq={}
for ident in (114,115,116,117):
 rows=re.findall(r'^\s*\d+:\s+(\d+)\s+(\d+)\s+GICv3\s+'+str(ident)+r'\s+Level',t,re.M)
 assert len(rows)>=2 and rows[-1]==rows[-2]
 irq[str(ident)]=[int(x) for x in rows[-1]]
assert irq['116']==[0,0] and irq['115'][0]>0 and irq['117'][0]>0
assert 'bsp_motion ' not in t[t.rfind('Err:'):]
assert 'BSP_MOTION_FIFO50_FINISHED_BUFFERS_RELEASED_RESULT=0' in t
failed,fm=log('motion-board-accept-20261013-03.log');assert fm['script_exit']==1 and 'MOTION_ACCEPT_FAIL sustained fault' in failed
assert len(re.findall(r'MOTION_ACCEPT_PASS checks=\d+',failed))==2 and failed.count('MOTION_EVENT_POLL_PASS')==2
safe,sm=log('motion-final-failure-safe-release-20261013-01.log');assert sm['script_exit']==0 and 'BSP_MOTION_FAILURE_SAFE_RELEASE_COMPLETE' in safe
bad=snapshot(safe,'initial');assert bad['error']==0x202 and bad['done']==238
_,bm=log('motion-coldboot-20261013-03.log');boot=(E/'motion-coldboot-20261013-03.log').read_bytes().decode(errors='replace');assert 'root=PARTUUID=2176bfe4-02' in boot and 'Mark FSBL is completed' in boot and 'U-Boot 2021.01' in boot
out={'scope':'ISOLATED_INTERNAL_MOTION_TEST_ONLY','final_root_partuuid':'2176bfe4-02','coldboot':bm,'final_dynamic_cancel_recovery':{'status':'PASS','pass_checks':[int(x) for x in re.findall(r'MOTION_ACCEPT_PASS checks=(\d+)',failed)],'event_poll_passes':2,'raw':fm},'ordinary_scheduler_final_supply':{'status':'FAIL_UNDERRUN_0x202','snapshot':bad,'raw':fm,'safe_release_raw':sm,'automatically_resumed_old_trajectory':False},'previous_ordinary_scheduler_supply_success':old,'final_fifo50_two_normal_cpu_loads_supply':fifo,'long_trajectory':{'positions':prior,'expected_pulse_deltas':expected,'actual_pulse_deltas':actual,'accepted_active_done':102431,'end_count_delta':1},'final_irq_idle_stable':irq,'final_state':{'motion_client':'UNLOADED','coherent_motion_buffer':'RELEASED','gp_provider':'LOADED','dma_provider':'LOADED','active_dma':'NONE','uart':'CLOSED'},'limits':['finite measurement, not Linux worst-case bound','watermark sampled, not continuous minimum','FIFO50 is explicit isolation test scheduling configuration','no physical motor IO or driver synchronization verified']}
(E/'motion-board-result-20261013.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'status':'RAW_EVIDENCE_VERIFIED','final_fifo50':fifo,'pulse_deltas':actual,'irq':irq},indent=2))
