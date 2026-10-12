"""Validate and summarize raw UART DMA evidence without changing the raw log."""
import argparse
import hashlib
import json
from pathlib import Path
import re

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('log', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
raw = a.log.read_bytes()
meta = json.loads(a.log.with_suffix(a.log.suffix+'.json').read_text())
assert meta['sha256'] == hashlib.sha256(raw).hexdigest()
assert meta['script_exit'] == 0 and meta['arguments'] == ['a3d29e67-02']
s = raw.decode('utf-8', errors='replace').replace('\r', '')
# Console printk can interrupt an application line mid-word. Remove only each
# timestamped kernel record and its newline, preserving adjoining app bytes.
s = re.sub(r'\[\s*\d+\.\d+\] [^\n]*\n', '', s)
keys = ['length','pattern','scenario','result','mismatch','tx_callbacks',
        'rx_callbacks','submit_ns','tx_complete_ns','rx_complete_ns','total_ns',
        'errors','timeouts','recoveries','generation']
pattern = (r'DMA len=(\d+) pattern=(\d+) scenario=(\d+) result=(\d+) '
           r'mismatch=(\d+) callbacks=(\d+)/(\d+) submit_ns=(\d+) '
           r'complete_ns=(\d+)/(\d+) total_ns=(\d+) errors=(\d+) '
           r'timeouts=(\d+) recoveries=(\d+) generation=(\d+)')
rows = [dict(zip(keys, map(int, m.groups()))) for m in re.finditer(pattern,s)]
pairs = [tuple(map(int, m.groups())) for m in re.finditer(
    r'PAIR before_status=(\d+)/(\d+) quiescent=(\d+) inflight_observed=(\d+)',s)]
assert len(rows) == len(pairs) == 444
assert all(r['result'] == r['errors'] == 0 for r in rows)
assert all(q[2] == 1 for q in pairs)
normal = [r for r in rows if r['scenario'] == 0]
assert len(normal) == 426
assert all(r['tx_callbacks'] == r['rx_callbacks'] == 1 and
           r['mismatch'] == 0xffffffff for r in normal)
assert all(q[3] == 1 for r,q in zip(rows,pairs) if r['scenario'])
assert all(sum(r['scenario'] == n for r in rows) == 6 for n in (1,2,3))
assert rows[221]['timeouts'] == rows[443]['timeouts'] == 6
assert s.count('GP_ACCEPT_PASS checks=41') == 2
for marker in ('BSP_DMA_BUFFERS_RELEASED_AND_REACQUIRED_PASS',
               'GP_EPOCH_PRESERVED_ACROSS_DMA_RECOVERY',
               'BSP_DMA_BOARD_ACCEPT_COMPLETE_NO_MOTION','BSP_SERIAL_EXIT=0'):
    assert marker in s, marker
epochs = {key: int(re.search(r'GP_EPOCH_'+key+r'=(\d+)',s)[1])
          for key in ('BEFORE','AFTER')}
assert epochs['AFTER'] > epochs['BEFORE']
latency = [max(r['tx_complete_ns'],r['rx_complete_ns']) for r in normal]
irq = {}
for intid in (114,115,116):
    counts = [int(m[1]) for m in re.finditer(
        r'^\s*\d+:\s*(\d+)\s+\d+\s+GICv3 '+str(intid)+r' Level',s,re.M)]
    assert counts
    irq[str(intid)] = counts
assert irq['115'][-1] == irq['116'][-1] == 426
summary = {
    'status':'PASS_INDEPENDENT_DMA_LOOPBACK_AND_CONTROLLED_RECOVERY',
    'raw_log':str(a.log),'raw_sha256':meta['sha256'],
    'root_partuuid':'a3d29e67-02','tests':444,'normal_transfers':426,
    'payload_bytes':sum(r['length'] for r in normal),
    'expected_timeouts':12,'explicit_inflight_terminations':6,'errors':0,
    'all_pair_quiescent_checks':444,'abnormal_inflight_checks':18,
    'buffers_released_and_reacquired':True,'gp_checks_before_and_after':41,
    'gp_epoch':epochs,'gic_counts_in_accept_log':irq,
    'submit_ns_min':min(r['submit_ns'] for r in normal),
    'submit_ns_max':max(r['submit_ns'] for r in normal),
    'completion_ns_min':min(latency),'completion_ns_max':max(latency),
    'completion_ns_mean':sum(latency)/len(latency),
    'aggregate_payload_MBps':1000*sum(r['length'] for r in normal)/sum(latency),
    'throughput_scope':'payload / accumulated submit-to-IRQ completion; not sustained bus bandwidth',
    'emmc':'NOT_MODIFIED','motion_fifo_and_motors':'NOT_CONNECTED'}
a.output.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
