"""Execute actual RX/cancel/frame-check functions with native kernel/DMA mocks.

This is a software lifecycle test, not proof of physical HP1/DDR quiescence.
No files are hashed and no device is opened.
"""
from pathlib import Path
import argparse,subprocess
H=Path(__file__).resolve().parent;R=H.parents[1]
S=R/'integration/home_calibration_20261027/software/telemetry'
parser=argparse.ArgumentParser();parser.add_argument('--tag',required=True);args=parser.parse_args();assert args.tag.replace('-','').isalnum()
out=H/'artifacts'/('rx-owner-'+args.tag);out.mkdir(exist_ok=False)
source=(S/'client/bsp_rs485.c').read_text()
structure=source[source.index('struct rs485_owner {'):source.index('static u32 tr(')]
functions=source[source.index('static void quarantine('):source.index('static int config(')]
defines='\n'.join(line for name in ['telem_defs.h','rs485_defs.h'] for line in (S/'generated'/name).read_text().splitlines() if not line.startswith(('#include','#define UINT','#pragma once')))
decoder='\n'.join(line for line in (S/'client/record_decode.h').read_text().splitlines() if not line.startswith('#include'))
frame=bytes.fromhex((R/'ps_app/ps_partner_v1_1_20261022_005289b/ps_partner_v1/samples/telemetry_rtl_frames.hex').read_text().splitlines()[0])[::-1]
assert len(frame)==64
pre=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#ifndef ESTALE
#define ESTALE 116
#endif
typedef uint8_t u8;typedef uint16_t u16;typedef uint32_t u32;typedef uint64_t u64;
typedef int32_t s32;typedef int64_t s64;typedef uintptr_t dma_addr_t;typedef int dma_cookie_t,spinlock_t,wait_queue_head_t;
struct mutex{int depth;};struct completion{int value;};struct device{int unused;};struct dma_chan{int unused;};struct miscdevice{int unused;};
struct dmaengine_result{unsigned result;};struct dma_async_tx_descriptor{void (*callback_result)(void *,const struct dmaengine_result *);void *callback_param;};
struct bsp_telem_result{int cookie;unsigned actual,status;};
#define __iomem
#define RR(x) RT_REG_##x
#define RX_CAPACITY (RT_RECORD_BYTES*RT_BATCH_MAX)
#define U64_MAX UINT64_MAX
#define U32_MAX UINT32_MAX
#define THIS_MODULE 0
#define DMA_TRANS_NOERROR 0
#define DMA_TRANS_ABORTED 1
#define DMA_DEV_TO_MEM 0
#define DMA_PREP_INTERRUPT 1
#define DMA_CTRL_ACK 2
#define spin_lock_irqsave(lock,flags) do{(void)(lock);(flags)=0;}while(0)
#define spin_unlock_irqrestore(lock,flags) do{(void)(lock);(void)(flags);}while(0)
#define wake_up_interruptible(wait) ((void)(wait))
#define dev_err(dev,fmt,error) do{(void)(dev);(void)(fmt);(void)(error);}while(0)
#define dma_wmb() ((void)0)
#define dma_rmb() ((void)0)
#define READ_ONCE(x) (x)
static int wait_ok=1,exact_error=0,quiet_error=0,terminate_error=0,callback_result=0,pins=0,issue=0,corrupt=0,checks=0;
static struct dma_async_tx_descriptor descriptor;
static void mutex_lock(struct mutex*m){m->depth++;}static void mutex_unlock(struct mutex*m){m->depth--;}
static void complete(struct completion*c){c->value=1;}static void complete_all(struct completion*c){c->value=1;}static void reinit_completion(struct completion*c){c->value=0;}
static unsigned msecs_to_jiffies(unsigned x){return x;}
static unsigned wait_for_completion_timeout(struct completion*c,unsigned t){(void)t;return wait_ok&&c->value;}
static void __module_get(int m){(void)m;pins++;}
static int dmaengine_terminate_sync(struct dma_chan*c){(void)c;return terminate_error;}
static int bsp_telem_dma_quiescent(struct dma_chan*c){(void)c;return quiet_error;}
static struct dma_async_tx_descriptor *dmaengine_prep_slave_single(struct dma_chan*c,dma_addr_t d,unsigned n,int dir,unsigned flags){(void)c;(void)d;(void)n;(void)dir;(void)flags;return &descriptor;}
static int dmaengine_submit(struct dma_async_tx_descriptor*d){(void)d;return 9;}
static int dma_submit_error(int cookie){return cookie<0?cookie:0;}
static void dma_async_issue_pending(struct dma_chan*c){(void)c;issue=1;}
static int bsp_telem_dma_result(struct dma_chan*c,int cookie,struct bsp_telem_result*r){(void)c;r->cookie=cookie;r->actual=64;r->status=0;return 0;}
static int bsp_telem_dma_exact(struct dma_chan*c,int cookie,unsigned n,struct bsp_telem_result*r){(void)c;(void)cookie;(void)n;(void)r;return exact_error;}
static void *u64_to_user_ptr(u64 p){return(void*)(uintptr_t)p;}
static int copy_to_user(void*d,const void*s,unsigned n){memcpy(d,s,n);return 0;}
static uint16_t get_unaligned_le16(const void*p){const u8*b=p;return(uint16_t)b[0]|(uint16_t)b[1]<<8;}
static uint32_t get_unaligned_le32(const void*p){const u8*b=p;return(uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;}
static uint32_t crc32_le(uint32_t crc,const void*p,unsigned n){const u8*b=p;for(unsigned i=0;i<n;i++){crc^=b[i];for(int j=0;j<8;j++)crc=(crc>>1)^((crc&1)?0xedb88320u:0);}return crc;}
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
'''
middle=r'''
static struct rs485_owner *current;
static u32 registers[1024];
static u32 tr(struct rs485_owner*m,u32 offset){(void)m;return registers[offset/4];}
static void tw(struct rs485_owner*m,u32 offset,u32 value){registers[offset/4]=value;
 if(offset==RR(ARM)&&value){CHECK(issue);memcpy(m->buffer,frame,64);if(corrupt)((u8*)m->buffer)[63]^=1;registers[RR(STATUS)/4]|=RT_STATUS_STREAM_DONE;struct dmaengine_result r={callback_result};descriptor.callback_result(descriptor.callback_param,&r);}
 if(offset==RR(RECOVER)&&value){registers[RR(STATUS)/4]=RT_STATUS_OPEN;registers[RR(TRANSPORT_GEN)/4]=registers[RR(RECOVER_GEN)/4];}}
static u32 readl(const void*p){return *(const u32*)p;}
#define readl_poll_timeout(addr,value,condition,delay,timeout) ((void)(delay),(void)(timeout),(value)=readl(addr),(condition)?0:-ETIMEDOUT)
static void rearm_telem(struct rs485_owner*m){(void)m;}
struct rs485_packet{u32 id,generation,bytes,actual,status,records;u64 data;};
'''
test=r'''
static struct rs485_owner owner;
static u8 storage[RX_CAPACITY],user[RX_CAPACITY];
static void reset(void){memset(&owner,0,sizeof(owner));memset(registers,0,sizeof(registers));owner.buffer=storage;owner.telem=(void*)registers;owner.generation=1;owner.epoch=1;current=&owner;
 registers[RR(STATUS)/4]=RT_STATUS_PACKET_READY;registers[RR(PACKET_ID)/4]=7;registers[RR(PACKET_GEN)/4]=1;registers[RR(PACKET_COUNT)/4]=1;registers[RR(PACKET_BYTES)/4]=64;
 wait_ok=1;exact_error=quiet_error=terminate_error=callback_result=pins=issue=corrupt=0;
}
static int receive_one(void){struct rs485_packet p={0};p.data=(u64)(uintptr_t)user;int ret=receive(&owner,&p);if(!ret){CHECK(p.records==1&&p.bytes==64&&p.actual==64);CHECK(memcmp(user,frame,64)==0);}return ret;}
int main(void){
 reset();CHECK(receive_one()==0);CHECK(owner.owned&&owner.received&&owner.dma_done&&!owner.quarantine);CHECK(owner.producer.depth==0&&owner.life.depth==0);
 CHECK(cancel(&owner,false)==0);CHECK(!owner.owned&&!owner.quarantine&&owner.buffer==storage);
 reset();owner.owned=true;CHECK(cancel(&owner,false)==-EOPNOTSUPP);CHECK(owner.quarantine&&owner.blocked&&owner.owned&&owner.buffer==storage&&pins==1);
 reset();owner.owned=true;owner.drain_validated=true;CHECK(cancel(&owner,false)==0);CHECK(!owner.owned&&!owner.quarantine);
 reset();quiet_error=-EBUSY;CHECK(cancel(&owner,false)==-EBUSY);CHECK(owner.quarantine&&owner.buffer==storage);
 reset();wait_ok=0;CHECK(receive_one()==-ETIMEDOUT);CHECK(owner.quarantine&&owner.owned&&!owner.dma_done);
 reset();exact_error=-EMSGSIZE;CHECK(receive_one()==-EMSGSIZE);CHECK(owner.quarantine&&owner.buffer==storage);
 reset();callback_result=DMA_TRANS_ABORTED;CHECK(receive_one()==-EIO);CHECK(owner.quarantine&&owner.owned);
 reset();corrupt=1;CHECK(receive_one()==-EBADMSG);CHECK(!owner.received&&!owner.owned&&owner.dma_done==false&&!owner.quarantine);
 reset();registers[RR(PACKET_COUNT)/4]=RT_BATCH_MAX+1;CHECK(receive_one()==-EPROTO);CHECK(!owner.owned&&!issue);
 reset();registers[RR(PACKET_GEN)/4]=2;CHECK(receive_one()==-EPROTO);CHECK(!owner.owned&&!issue);
 reset();CHECK(cancel(&owner,true)==0);CHECK(owner.generation==2&&!owner.blocked&&!owner.quarantine);
 printf("PASS %d actual RX/cancel/CRC/length/recovery/quarantine checks; physical DDR drain NOT tested\n",checks);return 0;
}
'''
program=pre+'\n'+defines+'\n'+decoder+'\n'+structure+'\nstatic const u8 frame[64]={'+','.join(str(v) for v in frame)+'};\n'+middle+'\n'+functions+'\n'+test
(out/'test.c').write_text(program)
subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-function',str(out/'test.c'),'-o',str(out/'test.exe')],check=True)
subprocess.run([str(out/'test.exe')],check=True)
