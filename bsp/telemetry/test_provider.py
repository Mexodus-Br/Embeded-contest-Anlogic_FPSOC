"""Execute the actual provider IRQ/result/retire logic with guarded MMIO mocks.

This verifies software ordering/length decisions, not physical DDR quiescence.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'bsp/telemetry'
p=argparse.ArgumentParser();p.add_argument('--tag',required=True);a=p.parse_args();assert re.fullmatch('[a-zA-Z0-9_-]+',a.tag)
E=R/('bsp/evidence/telemetry-provider-'+a.tag);E.mkdir(exist_ok=False)
irq=(D/'provider/anlogic_dma.c').read_text(encoding='utf-8')
irq=irq[irq.index('static irqreturn_t anlogic_dma_irq_handler'):irq.index('dma_cookie_t anlogic_dma_tx_submit')]
api=(D/'provider/axi-dma.c').read_text(encoding='utf-8');api=api[api.index('int bsp_telem_dma_result'):]
vendor=(D/'provider/include/linux/dma/anlogic_dma.h').read_text(encoding='utf-8')
lines=vendor.splitlines();selected=[];i=0
while i<len(lines):
 if lines[i].startswith('#define ANLOGIC_DMA_DMASR_'):
  selected.append(lines[i])
  while lines[i].rstrip().endswith('\\'):i+=1;selected.append(lines[i])
 i+=1
defines='\n'.join(selected)
pre=r'''
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <stdint.h>
#include <errno.h>
#include <stdlib.h>
#ifndef ESTALE
#define ESTALE 116
#endif
#define BIT(n) (1U<<(n))
#define GENMASK(h,l) (((~0U)<<(l))&((~0U)>>(31-(h))))
#define IRQ_NONE 0
#define IRQ_HANDLED 1
#define DMA_DEV_TO_MEM 2
#define EXPORT_SYMBOL_GPL(x)
#define ANLOGIC_DMA_REG_DMASR 4
#define ANLOGIC_DMA_REG_DMACR 0
#define ANLOGIC_DMA_REG_BTT 40
#define ANLOGIC_DMA_REG_CURDESC 8
#define ANLOGIC_DMA_REG_TAILDESC 16
#define ANLOGIC_DMA_DMACR_RUNSTOP 1
#define ANLOGIC_DMA_DMACR_RESET 4
#define ANLOGIC_DMA_DMAXR_ALL_IRQ_MASK 0x7000
typedef unsigned u32;typedef int dma_cookie_t;typedef int irqreturn_t;
struct dma_chan {int unused;};
struct anlogic_dma_tx_descriptor {struct {int cookie;} async_tx;};
struct list_head {int count;struct anlogic_dma_tx_descriptor *desc;};
struct anlogic_dma_chan;
struct anlogic_dma_device {struct {void (*complete_descriptor)(struct anlogic_dma_chan *);} desc_ops;};
struct anlogic_dma_chan {
 struct dma_chan common;struct anlogic_dma_device *al_dev;
 bool telemetry,telemetry_valid,telemetry_hold,has_sg,err,idle,flush_on_fsync;
 int direction,lock,tasklet,irq;void *dev;void *motion_fault_data;void (*motion_fault_stop)(void *);
 void (*start_transfer)(struct anlogic_dma_chan *);
 struct list_head active_list,pending_list,done_list;
 int telemetry_cookie;u32 telemetry_actual,telemetry_status;
};
struct bsp_telem_result {int cookie;unsigned actual,status;};
static struct anlogic_dma_chan c;static unsigned sr,cr,length,acks,starts,bad_reads,callbacks;
#define to_anlogic_chan(p) ((struct anlogic_dma_chan *)(p))
#define list_empty(p) (!(p)->count)
#define list_first_entry(p,t,m) ((p)->desc)
#define spin_lock_irqsave(l,f) do{(f)=0;}while(0)
#define spin_unlock_irqrestore(l,f) do{(void)(f);}while(0)
#define spin_lock(l) do{}while(0)
#define spin_unlock(l) do{}while(0)
#define dev_err(...) do{}while(0)
#define dev_dbg(...) do{}while(0)
static unsigned dma_ctrl_read(struct anlogic_dma_chan *p,unsigned reg){(void)p;if(reg==4)return sr;if(reg==0)return cr;if(reg==40)return length;bad_reads++;return 0;}
static void dma_ctrl_write(struct anlogic_dma_chan *p,unsigned reg,unsigned v){(void)p;if(reg==4){sr&=~v;acks++;length=0xdead;}else if(reg==0)cr=v;}
static void dma_ctrl_set(struct anlogic_dma_chan *p,unsigned reg,unsigned v){(void)p;(void)reg;cr|=v;}
static void synchronize_irq(int n){(void)n;}
static void tasklet_kill(int *p){(void)p;if(c.done_list.count){callbacks++;c.done_list.count=0;}}
static void tasklet_schedule(int *p){(void)p;}
static void msleep(int n){(void)n;}
static void done(struct anlogic_dma_chan *p){p->active_list.count=0;p->done_list.count=1;}
static void start(struct anlogic_dma_chan *p){if(!p->telemetry_hold&&!p->err)starts++;}
'''
test=r'''
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"FAIL %u %s\n",checks,#x);exit(1);}}while(0)
static void one(unsigned state,unsigned actual,unsigned requested,int expected){
 struct anlogic_dma_tx_descriptor d={.async_tx={.cookie=17}};struct anlogic_dma_device dev={.desc_ops={.complete_descriptor=done}};
 struct bsp_telem_result r;int ret;
 memset(&c,0,sizeof(c));c.telemetry=true;c.direction=DMA_DEV_TO_MEM;c.al_dev=&dev;c.start_transfer=start;c.active_list.count=1;c.active_list.desc=&d;
 sr=state;cr=0;length=actual;acks=starts=bad_reads=callbacks=0;
 anlogic_dma_irq_handler(1,&c);
 ret=bsp_telem_dma_exact(&c.common,17,requested,&r);CHECK(ret==expected);CHECK(!bad_reads);
 if(state&0x5000){CHECK(r.actual==actual);CHECK(c.telemetry_hold);CHECK(!starts);CHECK(acks==((state&0x4000)?2U:1U));CHECK(length==0xdead);
  CHECK(bsp_telem_dma_result(&c.common,18,&r)==-ESTALE);
  CHECK(bsp_telem_dma_retire(&c.common,17)==0);CHECK(!c.telemetry_hold);CHECK(callbacks==1);
 }else{CHECK(!c.telemetry_valid);CHECK(!c.telemetry_hold);}
}
int main(void){
 one(0x1002,64,64,0);one(0x1002,1024,1024,0);one(0x1002,64,1024,-EMSGSIZE);
 one(0x4012,64,64,-EMSGSIZE);one(0x1002,192,192,0);one(0,128,128,-ESTALE);one(0x2002,128,128,-ESTALE);
 c.telemetry=false;CHECK(bsp_telem_dma_result(&c.common,17,&(struct bsp_telem_result){0})==-EINVAL);
 c.telemetry=true;c.has_sg=true;CHECK(bsp_telem_dma_result(&c.common,17,&(struct bsp_telem_result){0})==-EINVAL);
 printf("PASS actual provider IRQ latch/length/cookie/retire checks=%u; physical DDR drain NOT tested\n",checks);return 0;
}
'''
(E/'harness.c').write_text(pre+'\n'+defines+'\n'+irq+'\n'+api+'\n'+test,encoding='utf-8')
for name,cmd in [('compile',['gcc','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter',str(E/'harness.c'),'-o',str(E/'test.exe')]),('run',[str(E/'test.exe')])]:
 with (E/(name+'.log')).open('w',encoding='utf-8') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:raise SystemExit('provider '+name+' failed; preserve log')
(E/'result.json').write_text(json.dumps({'status':'PASS','provider_sources':{n:hashlib.sha256((D/n).read_bytes()).hexdigest() for n in ('provider/anlogic_dma.c','provider/axi-dma.c')},'real_functions_extracted':True,'physical_ddr_drain':'NOT_EXECUTED'},indent=2)+'\n',encoding='utf-8')
print((E/'run.log').read_text(encoding='utf-8'))
