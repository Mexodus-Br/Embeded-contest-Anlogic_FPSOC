"""One-time authoring migration; future edits belong in the sole schema."""
import json
from pathlib import Path
R=Path(__file__).resolve().parents[1];p=R.parent/'pl_interface/schema.json'
s=json.loads(p.read_text(encoding='utf-8'))
if 'rs485_telemetry' in s:raise RuntimeError('migration already applied')
regs={}
def block(b,names):regs.update({n:b+4*i for i,n in enumerate(names.split())})
block(0,'VERSION PROFILE CAPS FEATURES STATUS IRQ_PENDING IRQ_MASK ACCESS_ERROR')
block(0x40,'ENABLE RECOVER_GEN RECOVER CANCEL PACKET_ID PACKET_GEN PACKET_COUNT PACKET_BYTES ARM_ID ARM_GEN ARM_BYTES ARM COMPLETE_ID COMPLETE_GEN COMPLETE_RESULT COMPLETE SNAP_REQ_ID SNAP_SUBMIT SNAP_STATUS SNAP_ID FIFO_LEVEL FULL_DROP DISABLED_DROP CANCEL_DROP STREAM_RECORDS STREAM_PACKETS DMA_OK DMA_FAILED PARSE_ERRORS SERIAL_LO SERIAL_HI TRANSPORT_GEN')
q=json.loads((R/'rate_design.json').read_text())
params=s['dma_loopback_profiles']['dma_loopback_v1']['parameters'].copy();params['AL_INCLUDE_MM2S']=0;params['AL_INCLUDE_S2MM']=1
wo=set('RECOVER CANCEL ARM COMPLETE SNAP_SUBMIT'.split());rw=set('ENABLE IRQ_MASK RECOVER_GEN ARM_ID ARM_GEN ARM_BYTES COMPLETE_ID COMPLETE_GEN COMPLETE_RESULT SNAP_REQ_ID'.split())
row={'FLAGS':0,'ADDRESS_QUERY':4,'VALID_GENERATION':8,'VALID_REVISION':12,'RESULT_GENERATION':16,'RESULT_REVISION':20,'UPDATES':24,'RESERVED':28,'VALID_RAW':32,'RESULT_RAW':64,'SIGNED':96,'CARRY':104,'VALUE_ENUM':108,'AGE':112,'STALE_LIMIT':120}
frame={'MAGIC':(0,4),'VERSION':(4,2),'LENGTH':(6,2),'COLLECTOR_GENERATION':(8,4),'REVISION':(12,4),'TRANSPORT_GENERATION':(16,4),'SERIAL':(20,8),'RAW':(28,32),'CRC':(60,4)}
head='TIME_LO TIME_HI GENERATION REVISION MASK TRANSPORT_GEN STATUS FIFO_LEVEL FULL_DROP DISABLED_DROP CANCEL_DROP STREAM_RECORDS STREAM_PACKETS DMA_OK DMA_FAILED PARSE_ERRORS SERIAL_LO SERIAL_HI PACKET_ID PACKET_GEN PACKET_COUNT PACKET_BYTES WAIT_ARM_MAX_US BACKPRESSURE_CYCLES_MAX READY_LATENESS_MAX_US'.split()
s['rs485_telemetry']={'status':'USER_CONFIRMED','confirmation_date':'2026-10-14','documentation':'pl_rs485/DMA_INDEPENDENT_ADDENDUM.md',
 'base':0x80800000,'size':4096,'irq_line':5,'irq_spi':87,'irq_intid':119,'version':1,'profile':0x31544352,'caps':31,'features':31,
 'clock_hz':100000000,'fifo_depth':256,'batch_max':16,'flush_us':10000,'stale_floor_us':100000,'stale_periods':3,
 'record_bytes':64,'record_magic':0x31543452,'record_version':1,'crc_bytes':60,'crc_poly':0xedb88320,'crc_init':0xffffffff,'crc_xorout':0xffffffff,
 'rows':15,'row_base':0x200,'row_stride':128,'snapshot_base':0x100,'snapshot_words':32,'registers':regs,
 'register_access':{n:'WO' if n in wo else 'RW' if n in rw else 'W1C' if n=='IRQ_PENDING' else 'RO' for n in regs},
 'row_offsets':row,'snapshot_header':{n:i for i,n in enumerate(head)},'frame_fields':{n:{'offset':o,'size':nbytes} for n,(o,nbytes) in frame.items()},
 'flag_bits':{n:i for i,n in enumerate('VALID_SEEN RESULT_SEEN RESULT_VALID ENUM_KNOWN STALE DISABLED'.split())},
 'status_bits':{n:i for i,n in enumerate('OPEN ENABLE PACKET_READY SENDING STREAM_DONE CANCEL_PENDING DMA_READY EXHAUSTED'.split())},
 'irq_bits':{n:i for i,n in enumerate('PACKET_READY PACKET_RESULT FAULT PARSE_ERROR FIFO_DROP'.split())},
 'errors':{n:i for i,n in enumerate('NONE ADDRESS ALIGN ACCESS STROBE RESERVED BUSY ID GENERATION LENGTH STATE EXHAUSTED'.split())},
 'dma':{'name':'dma_rs485_s2mm_v1','base':0x80900000,'size':4096,'register_span':1024,'irq_line':6,'irq_spi':88,'irq_intid':120,'hp_port':1,'parameters':params,
 'read_offsets':[0x30,0x34,0x48,0x4c,0x58],'write_offsets':[0x30,0x34,0x48,0x4c,0x58],'reset_scope':'independent controller only; common system reset remains shared'},
 'semantics':{'event':'immutable completion, independent of diagnostic FIFO admission','record':'raw GP word order, LE envelope, source BE payload retained','rx':'freeze exact N*64 then RX descriptor before ARM; no short residue assumption','cache':'local collector reset invalidates; DMA reset preserves','cancel':'held VALID stable until handshake or primary reset; recover explicit after DDR quiescence','stale':'max(3*active_period,100000); disabled and unseen stale; modulo64 age','counter':'u32 saturating; serial u64 no wrap; IDs and generations u32 no wrap'}}
p.write_bytes((json.dumps(s,ensure_ascii=False,indent=2)+'\n').encode())
