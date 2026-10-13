"""Authoring migration: additive confirmed profile, never rewrites old values."""
import json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
P=R.parent/'pl_interface/schema.json'
s=json.loads(P.read_text(encoding='utf-8'))
regs={}
def block(base,names):
    regs.update({n:base+4*i for i,n in enumerate(names.split())})
block(0,'VERSION PROFILE CAPS FEATURES RUN STATUS GENERATION LOCAL_RESET IRQ_PENDING IRQ_MASK LAST_ACCESS_ERROR FIFO_LEVEL')
block(0x40,'SHADOW_PERIOD0 SHADOW_PERIOD1 SHADOW_PERIOD2 SHADOW_PERIOD3 SHADOW_PERIOD4 SHADOW_MASK TXN_ID CFG_SUBMIT')
block(0x60,'CFG_STATE CFG_TXN CFG_ERROR CFG_REVISION CFG_SEQUENCE CFG_TIME_LO CFG_TIME_HI CFG_GENERATION')
block(0x80,'CURRENT_PERIOD0 CURRENT_PERIOD1 CURRENT_PERIOD2 CURRENT_PERIOD3 CURRENT_PERIOD4 CURRENT_MASK CURRENT_LOAD')
block(0xa0,'CAPTURE CAPTURE_ID CAPTURE_STATUS CAPTURE_GENERATION CAPTURE_REVISION CONSUME_ID ABANDON_ID LAST_CONSUMED_ID')
block(0xc0,'WORD0 WORD1 WORD2 WORD3 WORD4 WORD5 WORD6 WORD7')
block(0x100,'SNAP_REQ_ID SNAP_SUBMIT SNAP_STATUS SNAP_ID')
rw={'RUN','IRQ_MASK','SHADOW_MASK','TXN_ID','SNAP_REQ_ID'}|{f'SHADOW_PERIOD{i}' for i in range(5)}
wo={'LOCAL_RESET','CFG_SUBMIT','CAPTURE','CONSUME_ID','ABANDON_ID','SNAP_SUBMIT'}
head='TIME_LO TIME_HI GENERATION REVISION APPLY_SEQUENCE MASK PERIOD0 PERIOD1 PERIOD2 PERIOD3 PERIOD4 LOAD FIFO_LEVEL DROPPED ACCEPTED ERRORS IGNORED_RX BUS_BUSY OFFLINE CFG_STATE CFG_TXN CFG_ERROR CFG_TIME_LO CFG_TIME_HI CFG_GENERATION RUN CAPTURE_ID CAPTURE_STATUS SLAVE_COUNT FIFO_DEPTH RESERVED0 RESERVED1'.split()
p=dict(status='USER_CONFIRMED',confirmation={'date':'2026-10-14','answer':'三组方案均接受'},documentation='pl_rs485/GP_PROFILE_PROPOSAL.md',
 base=0x80700000,size=4096,address_width=33,data_width=32,clock_hz=100000000,irq_line=4,irq_spi=86,irq_intid=118,
 version=1,profile=0x31533552,caps=31,features=31,irq_valid_mask=127,query_valid_mask=31,
 fifo_depth=8,max_nodes=10,max_tasks=50,node_base=0x280,node_stride=16,task_base=0x340,task_stride=32,snapshot_base=0x200,snapshot_words=480,
 registers=regs,register_access={n:'RW' if n in rw else 'WO' if n in wo else 'W1C' if n=='IRQ_PENDING' else 'RO' for n in regs},
 snapshot_header={n:i for i,n in enumerate(head)},task_fields={n:i for i,n in enumerate('SCHEDULED SENT VALID MISSED MAX_LATENESS RESERVED0 RESERVED1 RESERVED2'.split())},
 node_fields={'FLAGS':0,'COOLDOWN_LO':1,'COOLDOWN_HI':2,'BACKOFF':3},
 errors={n:i for i,n in enumerate('NONE ADDRESS ALIGN ACCESS STROBE RESERVED BUSY ID PAYLOAD EMPTY PARTIAL EXHAUSTED RESET_STATE'.split())},
 cfg_errors={'NONE':0,'RANGE':1,'LOAD':2,'REVISION':3},
 irq_bits={n:i for i,n in enumerate('DATA CFG_RESULT COMM_ERROR PROTECT_OBSERVED FIFO_DROP BUS_DIAGNOSTIC RESET_DONE'.split())},
 cfg_bits={'ACCEPTED':0,'PENDING':1,'APPLIED':2,'REJECTED':3},
 status_bits={'RUN':0,'BUSY':1,'CFG_PENDING':2,'COLLECTOR_READY':3,'CAPTURE_VALID':4,'RESETTING':5},
 capture_fields={'VALID':[0,1],'READ_BITMAP':[8,8]},node_flag_fields={'FAILURES':[0,8],'OFFLINE':[8,1]},
 constraints={'zero_strobe':'OKAY no effect','full_strobe':'WO and W1C require 0xf','ids':'nonzero monotonic no wrap; latest same payload idempotent','record_word_order':'word0=record[31:0]','local_reset':'RUN=0, collector idle and cfg_ready, no bridge config pending; system time preserved','metadata':'revision at enqueue, generation at capture; collector FIFO reset on local reset','snapshot':'same edge registered values; no sequential sampling','deployment':'candidate resources; final BSP HPF/DT/IRQ audit required; not integrated'})
if 'rs485_gp_profiles' in s:raise RuntimeError('migration already performed')
s['rs485_gp_profiles']={'gp_rs485_v1':p}
P.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
