
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
#define ANLOGIC_DMA_DMASR_ALL_ERR_MASK 0x8ff0
#define ANLOGIC_DMA_DMASR_ERR_RECOVER_MASK 0x8900
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
#define to_anlogic_chan(p) (&c)
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

#define ANLOGIC_DMA_DMASR_EOL_LATE_ERR		BIT(15)
#define ANLOGIC_DMA_DMASR_ERR_IRQ		BIT(14)
#define ANLOGIC_DMA_DMASR_DLY_CNT_IRQ		BIT(13)
#define ANLOGIC_DMA_DMASR_FRM_CNT_IRQ		BIT(12)
#define ANLOGIC_DMA_DMASR_SOF_LATE_ERR		BIT(11)
#define ANLOGIC_DMA_DMASR_SG_DEC_ERR		BIT(10)
#define ANLOGIC_DMA_DMASR_SG_SLV_ERR		BIT(9)
#define ANLOGIC_DMA_DMASR_EOF_EARLY_ERR		BIT(8)
#define ANLOGIC_DMA_DMASR_SOF_EARLY_ERR		BIT(7)
#define ANLOGIC_DMA_DMASR_DMA_DEC_ERR		BIT(6)
#define ANLOGIC_DMA_DMASR_DMA_SLAVE_ERR		BIT(5)
#define ANLOGIC_DMA_DMASR_DMA_INT_ERR		BIT(4)
#define ANLOGIC_DMA_DMASR_SG_MASK		BIT(3)
#define ANLOGIC_DMA_DMASR_IDLE			BIT(1)
#define ANLOGIC_DMA_DMASR_HALTED		BIT(0)
#define ANLOGIC_DMA_DMASR_DELAY_MASK		GENMASK(31, 24)
#define ANLOGIC_DMA_DMASR_FRAME_COUNT_MASK	GENMASK(23, 16)
#define ANLOGIC_DMA_DMASR_ALL_ERR_MASK	\
#define ANLOGIC_DMA_DMASR_ERR_RECOVER_MASK	\
static irqreturn_t anlogic_dma_irq_handler(int irq, void *data)
{
	struct anlogic_dma_chan *chan = data;
	struct anlogic_dma_device *al_dev = chan->al_dev;
	u32 status;

	/* Read the status and ack the interrupts. */
	status = dma_ctrl_read(chan, ANLOGIC_DMA_REG_DMASR);

	if (!(status & ANLOGIC_DMA_DMAXR_ALL_IRQ_MASK))
		return IRQ_NONE;

    if (chan->telemetry && (status & (ANLOGIC_DMA_DMASR_FRM_CNT_IRQ | ANLOGIC_DMA_DMASR_ERR_IRQ))) {
        unsigned long flags;struct anlogic_dma_tx_descriptor *d;
        spin_lock_irqsave(&chan->lock,flags);
        /* Latch BEFORE W1C, callback or any future BTT programming. */
        if (!list_empty(&chan->active_list) && !chan->telemetry_valid) {
            d=list_first_entry(&chan->active_list,struct anlogic_dma_tx_descriptor,node);
            chan->telemetry_cookie=d->async_tx.cookie;
            chan->telemetry_actual=dma_ctrl_read(chan,ANLOGIC_DMA_REG_BTT);
            chan->telemetry_status=status;
            chan->telemetry_valid=true;chan->telemetry_hold=true;
        }
        spin_unlock_irqrestore(&chan->lock,flags);
    }
	dma_ctrl_write(chan, ANLOGIC_DMA_REG_DMASR,
			status & ANLOGIC_DMA_DMAXR_ALL_IRQ_MASK);

	if (status & ANLOGIC_DMA_DMASR_ERR_IRQ) {
        /* Motion STOP precedes controller recovery; ordinary IOC never stops. */
        if (chan->motion_fault_stop)
            chan->motion_fault_stop(chan->motion_fault_data);

		/*
		 * An error occurred. If C_FLUSH_ON_FSYNC is enabled and the
		 * error is recoverable, ignore it. Otherwise flag the error.
		 *
		 * Only recoverable errors can be cleared in the DMASR register,
		 * make sure not to write to other error bits to 1.
		 */
		u32 errors = status & ANLOGIC_DMA_DMASR_ALL_ERR_MASK;

		dma_ctrl_write(chan, ANLOGIC_DMA_REG_DMASR,
				errors & ANLOGIC_DMA_DMASR_ERR_RECOVER_MASK);

		if (!chan->flush_on_fsync ||
		    (errors & ~ANLOGIC_DMA_DMASR_ERR_RECOVER_MASK)) {
            if (chan->telemetry)
                dev_err(chan->dev,"Independent S2MM errors %x; latched length %u (no SG register reads)\n",errors,chan->telemetry_actual);
            else dev_err(chan->dev,
				"Channel %p has errors %x, cdr %x tdr %x\n",
				chan, errors,
				dma_ctrl_read(chan, ANLOGIC_DMA_REG_CURDESC),
				dma_ctrl_read(chan, ANLOGIC_DMA_REG_TAILDESC));
			chan->err = true;
		}
	}

	if (status & ANLOGIC_DMA_DMASR_DLY_CNT_IRQ) {
		/*
		 * Device takes too long to do the transfer when user requires
		 * responsiveness.
		 */
		dev_dbg(chan->dev, "Inter-packet latency too long\n");
	}

	if ((status & ANLOGIC_DMA_DMASR_FRM_CNT_IRQ) || (chan->telemetry && (status & ANLOGIC_DMA_DMASR_ERR_IRQ))) {
		spin_lock(&chan->lock);
		al_dev->desc_ops.complete_descriptor(chan);
		chan->idle = true;
		chan->start_transfer(chan);
		spin_unlock(&chan->lock);
	}

	tasklet_schedule(&chan->tasklet);

	return IRQ_HANDLED;
}


int bsp_telem_dma_result(struct dma_chan *rx,dma_cookie_t cookie,struct bsp_telem_result *out)
{
 struct anlogic_dma_chan *c=to_anlogic_chan(rx);unsigned long flags;int ret=0;
 if(!c->telemetry || c->direction!=DMA_DEV_TO_MEM || c->has_sg) return -EINVAL;
 spin_lock_irqsave(&c->lock,flags);
 if(!c->telemetry_valid || c->telemetry_cookie!=cookie) ret=-ESTALE;
 else {out->cookie=c->telemetry_cookie;out->actual=c->telemetry_actual;out->status=c->telemetry_status;}
 spin_unlock_irqrestore(&c->lock,flags);return ret;
}
EXPORT_SYMBOL_GPL(bsp_telem_dma_result);
int bsp_telem_dma_exact(struct dma_chan *rx,int cookie,unsigned int requested,struct bsp_telem_result *out)
{
 int ret=bsp_telem_dma_result(rx,cookie,out);
 if(ret)return ret;
 if(!(out->status & ANLOGIC_DMA_DMASR_FRM_CNT_IRQ) ||
    (out->status & (ANLOGIC_DMA_DMASR_ALL_ERR_MASK|ANLOGIC_DMA_DMASR_ERR_IRQ)) ||
    out->actual!=requested)return -EMSGSIZE;
 return 0;
}
EXPORT_SYMBOL_GPL(bsp_telem_dma_exact);
int bsp_telem_dma_retire(struct dma_chan *rx,dma_cookie_t cookie)
{
 struct anlogic_dma_chan *c=to_anlogic_chan(rx);unsigned long flags;int ret=0;
 if(!c->telemetry) return -EINVAL;
 synchronize_irq(c->irq);tasklet_kill(&c->tasklet);
 spin_lock_irqsave(&c->lock,flags);
 if(!c->telemetry_valid || c->telemetry_cookie!=cookie || !list_empty(&c->active_list) || !list_empty(&c->done_list) || !list_empty(&c->pending_list)) ret=-EBUSY;
 else {c->telemetry_valid=false;c->telemetry_hold=false;}
 spin_unlock_irqrestore(&c->lock,flags);return ret;
}
EXPORT_SYMBOL_GPL(bsp_telem_dma_retire);
int bsp_telem_dma_quiescent(struct dma_chan *rx)
{
 struct anlogic_dma_chan *c=to_anlogic_chan(rx);unsigned long flags;u32 sr,cr;int i;
 if(!c->telemetry || c->direction!=DMA_DEV_TO_MEM || c->has_sg) return -EINVAL;
 for(i=0;i<2;i++) {
  synchronize_irq(c->irq);tasklet_kill(&c->tasklet);
  sr=dma_ctrl_read(c,ANLOGIC_DMA_REG_DMASR);cr=dma_ctrl_read(c,ANLOGIC_DMA_REG_DMACR);
  if(!(sr & ANLOGIC_DMA_DMASR_HALTED) || (sr & ANLOGIC_DMA_DMASR_ALL_ERR_MASK) || (cr & (ANLOGIC_DMA_DMACR_RUNSTOP|ANLOGIC_DMA_DMACR_RESET))) return -EBUSY;
  spin_lock_irqsave(&c->lock,flags);
  if(!list_empty(&c->active_list)||!list_empty(&c->pending_list)||!list_empty(&c->done_list)){spin_unlock_irqrestore(&c->lock,flags);return -EBUSY;}
  spin_unlock_irqrestore(&c->lock,flags);
  if(!i)msleep(10);
 }
 /* Reset/HALTED + drained IRQ/tasklets/descriptors is controller evidence.
  * Real HP1 DDR drain and mapped silicon still require board validation. */
 c->telemetry_valid=false;c->telemetry_hold=false;
 dma_ctrl_write(c,ANLOGIC_DMA_REG_DMASR,ANLOGIC_DMA_DMAXR_ALL_IRQ_MASK);
 dma_ctrl_set(c,ANLOGIC_DMA_REG_DMACR,ANLOGIC_DMA_DMAXR_ALL_IRQ_MASK);
 return 0;
}
EXPORT_SYMBOL_GPL(bsp_telem_dma_quiescent);


static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"FAIL %u %s\n",checks,#x);exit(1);}}while(0)
static void one(unsigned state,unsigned actual,unsigned requested,int expected){
 struct anlogic_dma_tx_descriptor d={.async_tx={.cookie=17}};struct anlogic_dma_device dev={.desc_ops={.complete_descriptor=done}};
 struct bsp_telem_result r;int ret;
 memset(&c,0,sizeof(c));c.telemetry=true;c.direction=DMA_DEV_TO_MEM;c.al_dev=&dev;c.start_transfer=start;c.active_list.count=1;c.active_list.desc=&d;
 sr=state;cr=0;length=actual;acks=starts=bad_reads=callbacks=0;
 anlogic_dma_irq_handler(1,&c);
 ret=bsp_telem_dma_exact(&c.common,17,requested,&r);CHECK(ret==expected);CHECK(!bad_reads);
 if(state&0x5000){CHECK(r.actual==actual);CHECK(c.telemetry_hold);CHECK(!starts);CHECK(acks==1);CHECK(length==0xdead);
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
