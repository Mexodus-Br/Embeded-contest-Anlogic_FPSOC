// SPDX-License-Identifier: GPL-2.0
/* Isolated no-motor MOT2 client. No mmap or physical-address API. */
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/of.h>
#include <linux/interrupt.h>
#include <linux/irq.h>
#include <linux/io.h>
#include <linux/dmaengine.h>
#include <linux/dma-mapping.h>
#include <linux/miscdevice.h>
#include <linux/fs.h>
#include <linux/poll.h>
#include <linux/uaccess.h>
#include <linux/capability.h>
#include <linux/mutex.h>
#include <linux/delay.h>
#include <linux/ktime.h>
#include <linux/iopoll.h>
#include "motion_uapi.h"
#include "provider_api.h"
#include "generated/dma_defs.h"
#define P(x) PLI_MOTION_GP_MOTION_V1_##x
#define R(x) P(REG_##x)
#define CAPACITY (P(MAX_PACKET_RECORDS)*P(RECORD_BYTES))
struct motion {
 struct device *dev, *dma_dev;
 struct dma_chan *tx, *peer;
 void __iomem *gp;
 struct miscdevice misc;
 struct mutex writer, life, producer, snap;
 spinlock_t io;
 wait_queue_head_t wait;
 void *buffer;
 dma_addr_t dma;
 dma_cookie_t cookie;
 u64 cb_ns, submit_ns, session, events;
 u32 generation, cb_generation, txn, snap_id, cb_result;
 int irq;
 bool blocked, quarantine, owned, ioc, opened, dying, pinned, released;
};
static u32 rd(struct motion *m, u32 r) { return readl(m->gp+r); }
static void wr(struct motion *m, u32 r, u32 v) { writel(v,m->gp+r); }
/* IRQ-safe, independent of the mailbox writer and its PAUSE wait. */
static void stop_now(void *data)
{
 struct motion *m=data;
 unsigned long flags;
 spin_lock_irqsave(&m->io,flags);
 m->blocked=true;
 wr(m,R(STOP),1); rd(m,R(STATUS));
 m->events++;
 spin_unlock_irqrestore(&m->io,flags);
 wake_up_interruptible(&m->wait);
}
static void quarantine(struct motion *m, int reason)
{
 if (!m->quarantine) { m->quarantine=true; if(!m->pinned) {__module_get(THIS_MODULE);m->pinned=true;} }
 dev_err(m->dev,"stop proof failed %d: module/channels/buffer quarantined; no reuse or automatic restart\n",reason);
}
static int wait_stop(struct motion *m)
{
 u32 value;
 return readl_poll_timeout(m->gp+R(STATUS),value,
       value & P(STATUS_BITS_STOP_COMPLETE_MASK),10,2000000);
}
static void callback(void *data,const struct dmaengine_result *r)
{
 struct motion *m=data;
 unsigned long flags;
 spin_lock_irqsave(&m->io,flags);
 if (m->cb_generation==m->generation && !m->blocked) {
  m->cb_ns=ktime_get_ns(); m->cb_result=r?r->result:DMA_TRANS_NOERROR;
  m->ioc=true; m->events++;
 }
 spin_unlock_irqrestore(&m->io,flags);
 if (r && r->result!=DMA_TRANS_NOERROR) stop_now(m);
 wake_up_interruptible(&m->wait);
}
static irqreturn_t motion_irq(int irq,void *data)
{
 struct motion *m=data;
 unsigned long flags;
 u32 bits;
 spin_lock_irqsave(&m->io,flags);
 bits=rd(m,R(IRQ_PENDING)) & rd(m,R(IRQ_MASK));
 if (!bits) { spin_unlock_irqrestore(&m->io,flags);return IRQ_NONE; }
 /* Fault is a persistent source: mask pending events until explicit rearm. */
 wr(m,R(IRQ_MASK),0);rd(m,R(IRQ_MASK));m->events++;
 spin_unlock_irqrestore(&m->io,flags);
 if (bits & (P(IRQ_BITS_ERROR_MASK)|P(IRQ_BITS_CANCEL_MASK))) stop_now(m);
 wake_up_interruptible(&m->wait);
 return IRQ_HANDLED;
}
/* writer serializes payload only; io protects short MMIO sequences. */
static int command_locked(struct motion *m,struct motion_command *c)
{
 unsigned long flags;
 unsigned long deadline=jiffies+msecs_to_jiffies(c->timeout_ms);
 u32 id,gen,ack_before;int ret=0,i;
 spin_lock_irqsave(&m->io,flags);
 if (m->quarantine || m->dying ||
     (m->blocked && c->opcode!=PLI_CMD_LINK_RECOVER && c->opcode!=PLI_CMD_DISABLE && c->opcode!=PLI_CMD_CLEAR_FAULT)) {
  spin_unlock_irqrestore(&m->io,flags);return -EPIPE;
 }
 if (m->txn==U32_MAX) { spin_unlock_irqrestore(&m->io,flags);return -EOVERFLOW; }
 id=++m->txn;gen=m->generation;
 if (c->opcode==PLI_CMD_OPEN_SESSION) {
  /* boottime advances across module reloads within the same PL epoch. */
  u64 next=ktime_get_boottime_ns();
  m->session=max(next,m->session+1);c->session=m->session;
  wr(m,R(SESSION_LO),(u32)m->session);wr(m,R(SESSION_HI),m->session>>32);
 }
 if (c->opcode==PLI_CMD_REBASE) {
  wr(m,R(MAINT),1);
  for(i=0;i<4;i++) {
   wr(m,R(REBASE_0)+i*8,(u32)c->position[i]);
   wr(m,R(REBASE_0)+i*8+4,(u64)c->position[i]>>32);
  }
 }
 if(c->opcode==PLI_CMD_LINK_RECOVER) wr(m,R(RECOVER_GEN),gen);
 wr(m,R(OPCODE),c->opcode);wr(m,R(ARG),c->axis_mask);
 wr(m,R(TXN),id);wr(m,R(SUBMIT),1);rd(m,R(STATUS));
 spin_unlock_irqrestore(&m->io,flags);
 for (;;) {
  ack_before=rd(m,R(ACK_ID));
  c->ack_status=rd(m,R(ACK_STATUS));
  if(ack_before==id && rd(m,R(ACK_ID))==id && (c->ack_status&P(ACK_BITS_VALID_MASK)) &&
      !(c->ack_status&P(ACK_BITS_BUSY_MASK))) {
   c->ack_error=rd(m,R(ACK_ERROR));
   if(c->ack_error || !(c->ack_status&P(ACK_BITS_COMPLETED_MASK))) ret=-EREMOTEIO;
   break;
  }
  if (READ_ONCE(m->generation)!=gen ||
      (READ_ONCE(m->blocked) && c->opcode!=PLI_CMD_LINK_RECOVER && c->opcode!=PLI_CMD_DISABLE && c->opcode!=PLI_CMD_CLEAR_FAULT)) {ret=-ECANCELED;break;}
  if(time_after_eq(jiffies,deadline)) {ret=-ETIMEDOUT;break;}
  usleep_range(20,50);
 }
 if(c->opcode==PLI_CMD_REBASE) wr(m,R(MAINT),0);
 c->generation=gen;
 if(ret==-ETIMEDOUT) stop_now(m);
 return ret;
}
/* life excludes issuing DMA while STOP -> pulse-safe -> reset proof runs.
 * It never waits on the producer mutex: STOP can cancel a blocked packet. */
static int recover(struct motion *m,bool reopen_link)
{
 unsigned long flags;int ret,a,b;
 struct motion_command c={.opcode=PLI_CMD_LINK_RECOVER,.timeout_ms=2000};
 mutex_lock(&m->life);
 stop_now(m);
 if(m->quarantine) {ret=-EIO;goto out;}
 ret=wait_stop(m);if(ret) goto fail;
 spin_lock_irqsave(&m->io,flags);
 if(m->generation==U32_MAX) {spin_unlock_irqrestore(&m->io,flags);ret=-EOVERFLOW;goto fail;}
 ++m->generation; /* Invalidate callbacks before terminate and synchronize. */
 spin_unlock_irqrestore(&m->io,flags);
 a=dmaengine_terminate_sync(m->tx);b=dmaengine_terminate_sync(m->peer);
 ret=bsp_motion_dma_quiescent(m->tx,m->peer);
 if(a || b || ret) {ret=a?a:(b?b:ret);goto fail;}
 /* HALTED + controller-reset protocol + both synchronized descriptor queues
  * is the DMA ownership proof. PL queue empty alone cannot prove DDR idle. */
 dma_rmb();
 if (rd(m,R(BUFFERED)) || rd(m,R(STATUS))&P(STATUS_BITS_PACKET_BUSY_MASK)) {ret=-EBUSY;goto fail;}
 spin_lock_irqsave(&m->io,flags);m->owned=false;m->ioc=false;spin_unlock_irqrestore(&m->io,flags);
 if(reopen_link) {
  mutex_lock(&m->writer);ret=command_locked(m,&c);
  /* LINK_RECOVER is intentionally before clearing latched source. */
  if(!ret) {c.opcode=PLI_CMD_CLEAR_FAULT;c.axis_mask=15;ret=command_locked(m,&c);}
  mutex_unlock(&m->writer);
  if(!ret) {spin_lock_irqsave(&m->io,flags);m->blocked=false;spin_unlock_irqrestore(&m->io,flags);}
 }
 goto out;
fail: quarantine(m,ret);
out: mutex_unlock(&m->life);wake_up_interruptible(&m->wait);return ret;
}
static int packet(struct motion *m,struct motion_packet *p,bool injection)
{
 struct dma_async_tx_descriptor *d;
 unsigned long flags,deadline;
 u32 gen,before;int ret=0;
 if(!p->count || p->count>P(MAX_PACKET_RECORDS) || p->timeout_ms<10 || p->timeout_ms>2000 || (!injection && p->reserved) || (injection && (!p->reserved || p->reserved>3))) return -EINVAL;
 mutex_lock(&m->producer);
 mutex_lock(&m->life);
 if(!m->buffer || m->blocked || m->quarantine || m->owned) {ret=-EPIPE;goto unlock;}
 /* Before START/while paused, cap by credits to avoid IOC deadlock.
  * Running packets may use the full 1..910 range and receive backpressure. */
 if (!injection && !(rd(m,R(STATUS))&P(STATUS_BITS_RUNNING_MASK)) && (!m->buffer || rd(m,R(BUFFERED))>P(RAW_DEPTH)+P(PLAN_DEPTH)+1 || p->count > P(RAW_DEPTH)+P(PLAN_DEPTH)+1-rd(m,R(BUFFERED)))) {ret=-EAGAIN;goto unlock;}
 if (copy_from_user(m->buffer,u64_to_user_ptr(p->data),p->count*P(RECORD_BYTES))) {ret=-EFAULT;goto unlock;}
 dma_wmb();
 d=dmaengine_prep_slave_single(m->tx,m->dma,p->count*P(RECORD_BYTES)-(injection && p->reserved==1?8:0),DMA_MEM_TO_DEV,DMA_PREP_INTERRUPT|DMA_CTRL_ACK);
 if(!d) {ret=-ENOMEM;goto unlock;}
 spin_lock_irqsave(&m->io,flags);
 if(m->blocked) {spin_unlock_irqrestore(&m->io,flags); /* submit then cancel; provider owns descriptor */
  m->cookie=dmaengine_submit(d);m->owned=!dma_submit_error(m->cookie);ret=-ECANCELED;goto unlock_recover;}
 gen=m->generation;m->cb_generation=gen;m->ioc=false;m->cb_ns=0;m->cb_result=DMA_TRANS_ABORTED;
 before=rd(m,R(PACKET_COUNT));m->submit_ns=ktime_get_ns();
 d->callback_result=callback;d->callback_param=m;
 m->cookie=dmaengine_submit(d);
 if(dma_submit_error(m->cookie)) {ret=m->cookie;spin_unlock_irqrestore(&m->io,flags);goto unlock_recover;}
 m->owned=true;
 wr(m,R(PACKET_ARM),p->count+(injection && p->reserved==2?1:0));rd(m,R(STATUS));
 if(!(rd(m,R(STATUS))&P(STATUS_BITS_PACKET_BUSY_MASK))) {ret=-EIO;spin_unlock_irqrestore(&m->io,flags);goto unlock_recover;}
 dma_async_issue_pending(m->tx);
 p->submit_ns=ktime_get_ns()-m->submit_ns;
 spin_unlock_irqrestore(&m->io,flags);
 mutex_unlock(&m->life);
 deadline=jiffies+msecs_to_jiffies(p->timeout_ms);
 for(;;) {
  if(READ_ONCE(m->generation)!=gen || READ_ONCE(m->blocked)) {ret=-ECANCELED;break;}
  if(dma_async_is_tx_complete(m->tx,m->cookie,NULL,NULL)==DMA_ERROR) {stop_now(m);ret=-EIO;break;}
  if(READ_ONCE(m->ioc) && rd(m,R(PACKET_COUNT))!=before && !(rd(m,R(STATUS))&P(STATUS_BITS_PACKET_BUSY_MASK))) {
   p->closed_ns=ktime_get_ns()-m->submit_ns;p->ioc_ns=m->cb_ns-m->submit_ns;
   p->packet_count=rd(m,R(PACKET_COUNT));p->generation=gen;
   if(m->cb_result!=DMA_TRANS_NOERROR) ret=-EIO;
   else {spin_lock_irqsave(&m->io,flags);m->owned=false;spin_unlock_irqrestore(&m->io,flags);dma_rmb();}
   break;
  }
  if(time_after_eq(jiffies,deadline)) {stop_now(m);ret=-ETIMEDOUT;break;}
  usleep_range(10,25);
 }
 p->result=ret?-ret:0;
 mutex_unlock(&m->producer);
 return ret;
unlock_recover: stop_now(m);
unlock: mutex_unlock(&m->life);mutex_unlock(&m->producer);return ret;
}
static int snapshot(struct motion *m,struct motion_snapshot *s)
{
 u32 id,value;int ret,i;
 mutex_lock(&m->snap);
 if(m->snap_id==U32_MAX) {ret=-EOVERFLOW;goto out;}
 id=++m->snap_id;wr(m,R(SNAP_REQ),id);
 ret=readl_poll_timeout(m->gp+R(SNAP_ID),value,value==id,1,100000);
 if(ret || !rd(m,R(SNAP_VALID))) {ret=-ETIMEDOUT;goto out;}
 for(i=0;i<64;i++) s->words[i]=rd(m,R(SNAP_0)+i*4);
 if(rd(m,R(SNAP_ID))!=id) {ret=-EAGAIN;goto out;}
 s->id=id;s->generation=READ_ONCE(m->generation);s->quarantined=m->quarantine;s->dma_owned=m->owned;s->event_count=m->events;
out: mutex_unlock(&m->snap);return ret;
}
static int alloc_buffer(struct motion *m)
{
 m->buffer=dma_alloc_coherent(m->dma_dev,CAPACITY,&m->dma,GFP_KERNEL);
 if(!m->buffer) return -ENOMEM;
 if((m->dma&7) || upper_32_bits(m->dma+CAPACITY-1)) {
  dma_free_coherent(m->dma_dev,CAPACITY,m->buffer,m->dma);m->buffer=NULL;return -ERANGE;
 }
 return 0;
}
static long control(struct file *f,unsigned int op,unsigned long arg)
{
 struct motion *m=f->private_data;struct motion_command c;struct motion_packet p;struct motion_snapshot s={};
 int ret;
 if(!capable(CAP_SYS_RAWIO)) return -EPERM;
 if(m->released) return -ENODEV;
 switch(op) {
 case MOTION_RELEASE:
  WRITE_ONCE(m->dying,true);
  ret=recover(m,false);if(ret) return ret;
  mutex_lock(&m->producer);mutex_lock(&m->life);
  wr(m,R(IRQ_MASK),0);rd(m,R(IRQ_MASK));
  bsp_motion_dma_fault_hook(m->tx,NULL,NULL);
  dma_free_coherent(m->dma_dev,CAPACITY,m->buffer,m->dma);m->buffer=NULL;m->released=true;
  if(m->pinned) {m->pinned=false;module_put(THIS_MODULE);}
  mutex_unlock(&m->life);mutex_unlock(&m->producer);return 0;
 case MOTION_STOP: stop_now(m);return wait_stop(m);
 case MOTION_RECOVER:return recover(m,true);
 case MOTION_REALLOC:
  ret=recover(m,false);if(ret) return ret;
  mutex_lock(&m->producer);mutex_lock(&m->life);
  dma_free_coherent(m->dma_dev,CAPACITY,m->buffer,m->dma);m->buffer=NULL;
  ret=alloc_buffer(m);mutex_unlock(&m->life);mutex_unlock(&m->producer);return ret;
 case MOTION_SNAPSHOT:
  ret=snapshot(m,&s);if(ret) return ret;
  return copy_to_user((void __user *)arg,&s,sizeof(s))?-EFAULT:0;
 case MOTION_EVENTS:
  wr(m,R(IRQ_MASK),0);wr(m,R(IRQ_PENDING),P(IRQ_ALL_MASK));rd(m,R(IRQ_PENDING));
  wr(m,R(IRQ_MASK),P(IRQ_ALL_MASK));return 0;
 case MOTION_INJECT:
  if(!of_property_read_bool(m->dev->of_node,"bsp,isolated-motion-test")) return -EPERM;
  fallthrough;
 case MOTION_PACKET:
  if(copy_from_user(&p,(void __user *)arg,sizeof(p))) return -EFAULT;
  ret=packet(m,&p,op==MOTION_INJECT);p.result=ret?-ret:0;
  if(copy_to_user((void __user *)arg,&p,sizeof(p))) return -EFAULT;
  return ret;
 case MOTION_COMMAND:
  if(copy_from_user(&c,(void __user *)arg,sizeof(c))) return -EFAULT;
  if(c.timeout_ms<10 || c.timeout_ms>2000 || c.axis_mask>15) return -EINVAL;
  switch(c.opcode) {
  case PLI_CMD_REBASE:case PLI_CMD_ENABLE:case PLI_CMD_OPEN_SESSION:case PLI_CMD_START:
  case PLI_CMD_PAUSE:case PLI_CMD_RESUME:case PLI_CMD_DISABLE:case PLI_CMD_CLEAR_FAULT:case PLI_CMD_NOP:break;
  default:return -EINVAL;
  }
  mutex_lock(&m->writer);ret=command_locked(m,&c);mutex_unlock(&m->writer);
  if(copy_to_user((void __user *)arg,&c,sizeof(c))) return -EFAULT;
  return ret;
 default:return -ENOTTY;
 }
}
static int open_motion(struct inode *i,struct file *f)
{
 struct motion *m=container_of(f->private_data,struct motion,misc);int ret=0;
 if(!capable(CAP_SYS_RAWIO)) return -EPERM;
 mutex_lock(&m->life);if(m->opened || m->dying || m->quarantine) ret=-EBUSY;
 else {m->opened=true;f->private_data=m;}
 mutex_unlock(&m->life);return ret;
}
static int close_motion(struct inode *i,struct file *f)
{
 struct motion *m=f->private_data;int ret=m->released?0:recover(m,false);
 wr(m,R(IRQ_MASK),0);mutex_lock(&m->life);m->opened=false;mutex_unlock(&m->life);return ret;
}
static __poll_t poll_motion(struct file *f,poll_table *pt)
{
 struct motion *m=f->private_data;poll_wait(f,&m->wait,pt);
 if(m->quarantine) return EPOLLERR;
 return rd(m,R(IRQ_PENDING))?EPOLLIN|EPOLLRDNORM:0;
}
static const struct file_operations ops={.owner=THIS_MODULE,.open=open_motion,.release=close_motion,.unlocked_ioctl=control,.poll=poll_motion,.llseek=no_llseek};
static int probe(struct platform_device *pdev)
{
 struct motion *m;struct resource *r;int ret,irq;
 r=platform_get_resource(pdev,IORESOURCE_MEM,0);
 if(!r || r->start!=P(BASE) || resource_size(r)!=P(SIZE)) return -EINVAL;
 m=kzalloc(sizeof(*m),GFP_KERNEL);if(!m) return -ENOMEM;m->dev=&pdev->dev;
 m->gp=devm_ioremap_resource(m->dev,r);if(IS_ERR(m->gp)) {ret=PTR_ERR(m->gp);goto free;}
 if(rd(m,R(VERSION))!=P(VERSION) || rd(m,R(PROFILE))!=P(PROFILE_ID) || rd(m,R(CAPS))!=P(CAPS) || rd(m,R(FEATURES))!=P(FEATURES)) {ret=-ENODEV;goto free;}
 if(rd(m,R(RAW_CAPACITY))!=P(RAW_DEPTH) || rd(m,R(PLAN_CAPACITY))!=P(PLAN_DEPTH) || rd(m,R(START_THRESHOLD))!=P(START_MIN_POINTS)) {ret=-ENODEV;goto free;}
 mutex_init(&m->writer);mutex_init(&m->life);mutex_init(&m->producer);mutex_init(&m->snap);spin_lock_init(&m->io);init_waitqueue_head(&m->wait);
 m->txn=rd(m,R(ACK_ID));m->snap_id=rd(m,R(SNAP_ID));m->generation=rd(m,R(RECOVER_GEN));m->blocked=true;
 m->tx=dma_request_chan(m->dev,"tx");if(IS_ERR(m->tx)) {ret=PTR_ERR(m->tx);goto free;}
 m->peer=dma_request_chan(m->dev,"reset-peer");if(IS_ERR(m->peer)) {ret=PTR_ERR(m->peer);goto tx;}
 m->dma_dev=dmaengine_get_dma_device(m->tx);
 if(m->dma_dev!=dmaengine_get_dma_device(m->peer) || dma_get_mask(m->dma_dev)!=DMA_BIT_MASK(32)) {ret=-EINVAL;goto peer;}
 ret=alloc_buffer(m);if(ret) goto peer;
 ret=bsp_motion_dma_fault_hook(m->tx,stop_now,m);if(ret) goto buffer;
 ret=recover(m,false);if(ret) {platform_set_drvdata(pdev,m);return 0;} /* pinned quarantine retains devm GP mapping */
 irq=platform_get_irq(pdev,0);if(irq<0) {ret=irq;goto hook;}
 if(!irq_get_irq_data(irq) || irq_get_irq_data(irq)->hwirq!=P(IRQ_INTID) || irq_get_trigger_type(irq)!=IRQ_TYPE_LEVEL_HIGH) {ret=-ENODEV;goto hook;}
 ret=request_irq(irq,motion_irq,0,"bsp-motion",m);if(ret) goto hook;
 m->irq=irq;
 m->misc=(struct miscdevice){.minor=MISC_DYNAMIC_MINOR,.name="bsp-motion",.fops=&ops,.mode=0600,.parent=m->dev};
 ret=misc_register(&m->misc);if(ret) {free_irq(m->irq,m);goto hook;}
 platform_set_drvdata(pdev,m);
 __module_get(THIS_MODULE);m->pinned=true; /* requires explicit proven buffer release before unload */
 dev_info(m->dev,"MOT1 window verified; internal TEST config only; MM2S owner, S2MM reserved without RX; coherent mask32 aligned; closed until explicit recovery\n");return 0;
hook:bsp_motion_dma_fault_hook(m->tx,NULL,NULL);
buffer:dma_free_coherent(m->dma_dev,CAPACITY,m->buffer,m->dma);
peer:dma_release_channel(m->peer);
tx:dma_release_channel(m->tx);
free:kfree(m);return ret;
}
static int remove_motion(struct platform_device *p)
{
 struct motion *m=platform_get_drvdata(p);int ret;
 m->dying=true;misc_deregister(&m->misc);wr(m,R(IRQ_MASK),0);
 ret=m->released?0:recover(m,false);if(ret) return ret;
 free_irq(m->irq,m);
 bsp_motion_dma_fault_hook(m->tx,NULL,NULL);
 if(m->buffer) {dma_free_coherent(m->dma_dev,CAPACITY,m->buffer,m->dma);}
 dma_release_channel(m->peer);dma_release_channel(m->tx);kfree(m);return 0;
}
static const struct of_device_id ids[]={{.compatible="bsp,motion-gp-v1"},{}};
MODULE_DEVICE_TABLE(of,ids);
static struct platform_driver bsp_motion_driver={.probe=probe,.remove=remove_motion,.driver={.name="bsp-motion",.of_match_table=ids,.suppress_bind_attrs=true}};
module_platform_driver(bsp_motion_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Restricted MM2S MOT2 no-motor validation client");
