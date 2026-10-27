// SPDX-License-Identifier: GPL-2.0
/* Independent HP1 S2MM owner. No motion control, arbitrary MMIO or mmap. */
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/of.h>
#include <linux/interrupt.h>
#include <linux/io.h>
#include <linux/iopoll.h>
#include <linux/dmaengine.h>
#include <linux/dma-mapping.h>
#include <linux/miscdevice.h>
#include <linux/fs.h>
#include <linux/uaccess.h>
#include <linux/capability.h>
#include <linux/mutex.h>
#include <linux/completion.h>
#include <linux/poll.h>
#include <linux/crc32.h>
#include <linux/delay.h>
#include <asm/unaligned.h>
#include "rs485_uapi.h"
#include "provider_api.h"
#include "generated/gp_defs.h"
#include "generated/interlock_defs.h"
#include "record_decode.h"
#define RR(x) RT_REG_##x
#define GR(x) RG_REG_##x
#define RX_CAPACITY (RT_RECORD_BYTES*RT_BATCH_MAX)
struct rs485_owner {
 struct device *dev,*dma_dev;struct dma_chan *rx;void __iomem *gp,*telem;
 struct miscdevice misc;struct mutex producer,life,gp_lock,snap;
 spinlock_t lock;struct completion completion;void *buffer;dma_addr_t dma;
 dma_cookie_t cookie;u64 epoch,cb_epoch;u32 generation,txn,snap_id,packet_id,bytes,actual,status,cb_result;
 bool blocked,owned,quarantine,opened,released,pinned,received,dma_done,drain_validated;
 wait_queue_head_t wait;u32 gp_pending,telem_pending;int gp_irq,telem_irq;
};
static u32 tr(struct rs485_owner *m,u32 r){return readl(m->telem+r);}
static void tw(struct rs485_owner *m,u32 r,u32 v){writel(v,m->telem+r);}
static u32 gr(struct rs485_owner *m,u32 r){return readl(m->gp+r);}
static void gw(struct rs485_owner *m,u32 r,u32 v){writel(v,m->gp+r);}
static void rearm_telem(struct rs485_owner *m)
{
 unsigned long flags;spin_lock_irqsave(&m->lock,flags);
 tw(m,RR(IRQ_MASK),0);tw(m,RR(IRQ_PENDING),31);tr(m,RR(IRQ_PENDING));
 m->telem_pending=0;
 if(!m->blocked)tw(m,RR(IRQ_MASK),RT_IRQ_PACKET_READY|RT_IRQ_PACKET_RESULT|RT_IRQ_FAULT|RT_IRQ_PARSE_ERROR|RT_IRQ_FIFO_DROP);
 spin_unlock_irqrestore(&m->lock,flags);
}
static irqreturn_t irq(int number,void *data)
{
 struct rs485_owner *m=data;unsigned long flags;u32 bits;
 spin_lock_irqsave(&m->lock,flags);
 if(number==m->gp_irq){bits=gr(m,GR(IRQ_PENDING))&gr(m,GR(IRQ_MASK));if(bits){gw(m,GR(IRQ_MASK),0);gr(m,GR(IRQ_MASK));m->gp_pending|=bits;}}
 else{bits=tr(m,RR(IRQ_PENDING))&tr(m,RR(IRQ_MASK));if(bits){tw(m,RR(IRQ_MASK),0);tr(m,RR(IRQ_MASK));m->telem_pending|=bits;}}
 spin_unlock_irqrestore(&m->lock,flags);if(!bits)return IRQ_NONE;wake_up_interruptible(&m->wait);return IRQ_HANDLED;
}
static __poll_t poll_owner(struct file *f,poll_table *p)
{
 struct rs485_owner *m=f->private_data;poll_wait(f,&m->wait,p);
 return m->quarantine?EPOLLERR:(m->gp_pending||m->telem_pending||tr(m,RR(STATUS))&RT_STATUS_PACKET_READY)?EPOLLIN|EPOLLRDNORM:0;
}
static void quarantine(struct rs485_owner *m,int error)
{
 m->blocked=true;m->quarantine=true;
 if(!m->pinned){__module_get(THIS_MODULE);m->pinned=true;}
 dev_err(m->dev,"HP1 stop proof failed %d; retain module/channel/buffer; no motion STOP or restart\n",error);
}
static void cb(void *data,const struct dmaengine_result *r)
{
 struct rs485_owner *m=data;unsigned long flags;
 spin_lock_irqsave(&m->lock,flags);
 if(m->cb_epoch==m->epoch && !m->blocked){m->cb_result=r?r->result:DMA_TRANS_ABORTED;complete(&m->completion);}
 spin_unlock_irqrestore(&m->lock,flags);
 wake_up_interruptible(&m->wait);
}
/* life covers submit/ARM only, never a receive wait. CANCEL is independent. */
static int cancel(struct rs485_owner *m,bool reopen)
{
 int ret;unsigned long flags;u32 value;bool uncertain;
 mutex_lock(&m->life);
 spin_lock_irqsave(&m->lock,flags);m->blocked=true;
 if(m->epoch!=U64_MAX)m->epoch++;
 spin_unlock_irqrestore(&m->lock,flags);
 uncertain=m->owned&&!m->dma_done;
 tw(m,RR(ENABLE),0);tw(m,RR(CANCEL),1);tr(m,RR(STATUS));complete_all(&m->completion);
 tw(m,RR(IRQ_MASK),0);
 ret=dmaengine_terminate_sync(m->rx);
 if(!ret)ret=bsp_telem_dma_quiescent(m->rx);
 /* Controller proof is necessary, but an interrupted RX also needs a
  * qualified reset-to-HP1/DDR drain guarantee. A delay or hp_idle alone is
  * insufficient. Unqualified cancellation retains the buffer in quarantine. */
 if(!ret && uncertain && !m->drain_validated)ret=-EOPNOTSUPP;
 if(ret){quarantine(m,ret);goto out;}
 m->owned=false;m->received=false;m->dma_done=false;
 if(reopen){
  if(m->epoch==U64_MAX){ret=-EOVERFLOW;goto out;}
  if(m->generation==U32_MAX){ret=-EOVERFLOW;goto out;}
  tw(m,RR(RECOVER_GEN),++m->generation);tw(m,RR(RECOVER),1);
  ret=readl_poll_timeout(m->telem+RR(STATUS),value,value&RT_STATUS_OPEN,10,2000000);
  if(!ret && tr(m,RR(TRANSPORT_GEN))!=m->generation)ret=-ESTALE;
  if(!ret){tw(m,RR(ENABLE),1);m->blocked=false;rearm_telem(m);}
 }
out:mutex_unlock(&m->life);return ret;
}
static int frame_check(struct rs485_owner *m)
{
 u8 *b=m->buffer;unsigned i;
 for(i=0;i<m->bytes;i+=RT_RECORD_BYTES){
  u8 *p=b+i;u32 raw[8];rs485_decoded decoded;unsigned k;
  if(get_unaligned_le32(p+RT_FRAME_MAGIC_OFFSET)!=RT_RECORD_MAGIC ||
     get_unaligned_le16(p+RT_FRAME_VERSION_OFFSET)!=RT_RECORD_VERSION ||
     get_unaligned_le16(p+RT_FRAME_LENGTH_OFFSET)!=RT_RECORD_BYTES ||
     get_unaligned_le32(p+RT_FRAME_TRANSPORT_GENERATION_OFFSET)!=m->generation ||
     get_unaligned_le32(p+RT_FRAME_CRC_OFFSET)!=(crc32_le(RT_CRC_INIT,p,RT_CRC_BYTES)^RT_CRC_XOROUT))return -EBADMSG;
  for(k=0;k<8;k++)raw[k]=get_unaligned_le32(p+RT_FRAME_RAW_OFFSET+4*k);
  if(rs485_decode(raw,&decoded))return -EBADMSG;
 }
 return 0;
}
static int receive(struct rs485_owner *m,struct rs485_packet *p)
{
 struct dma_async_tx_descriptor *d;struct bsp_telem_result result;unsigned long flags;
 u32 count,gen,id,status;int ret=0;
 mutex_lock(&m->producer);mutex_lock(&m->life);
 if(m->blocked||m->quarantine||m->owned||m->released){ret=-EBUSY;goto unlock;}
 status=tr(m,RR(STATUS));id=tr(m,RR(PACKET_ID));gen=tr(m,RR(PACKET_GEN));count=tr(m,RR(PACKET_COUNT));
 m->bytes=tr(m,RR(PACKET_BYTES));
 if(!(status&RT_STATUS_PACKET_READY)){ret=-EAGAIN;goto unlock;}
 if(gen!=m->generation||!id||!count||count>RT_BATCH_MAX||m->bytes!=count*RT_RECORD_BYTES||tr(m,RR(PACKET_ID))!=id){ret=-EPROTO;goto unlock;}
 m->packet_id=id;m->actual=0;m->status=0;m->cb_result=DMA_TRANS_ABORTED;m->dma_done=false;
 reinit_completion(&m->completion);memset(m->buffer,0,RX_CAPACITY);dma_wmb();
 d=dmaengine_prep_slave_single(m->rx,m->dma,m->bytes,DMA_DEV_TO_MEM,DMA_PREP_INTERRUPT|DMA_CTRL_ACK);
 if(!d){ret=-EIO;goto unlock;}
 d->callback_result=cb;d->callback_param=m;
 spin_lock_irqsave(&m->lock,flags);m->cb_epoch=m->epoch;spin_unlock_irqrestore(&m->lock,flags);
 m->cookie=dmaengine_submit(d);ret=dma_submit_error(m->cookie);if(ret)goto unlock;
 m->owned=true;dma_async_issue_pending(m->rx);
 /* Device RX is issued before granting the stream credit. */
 tw(m,RR(ARM_ID),id);tw(m,RR(ARM_GEN),gen);tw(m,RR(ARM_BYTES),m->bytes);tw(m,RR(ARM),1);tr(m,RR(STATUS));
 mutex_unlock(&m->life);
 if(!wait_for_completion_timeout(&m->completion,msecs_to_jiffies(2000)))ret=-ETIMEDOUT;
 mutex_lock(&m->life);
 if(m->blocked||m->cb_epoch!=m->epoch)ret=-ECANCELED;
 if(!ret)ret=bsp_telem_dma_result(m->rx,m->cookie,&result);
 if(!ret){m->actual=result.actual;m->status=result.status;
  ret=bsp_telem_dma_exact(m->rx,m->cookie,m->bytes,&result);
  if(m->cb_result!=DMA_TRANS_NOERROR)ret=-EIO;
  if(!ret)m->dma_done=true;
 }
 if(!ret && (!(tr(m,RR(STATUS))&RT_STATUS_STREAM_DONE)||tr(m,RR(PACKET_ID))!=id||tr(m,RR(PACKET_GEN))!=gen))ret=-EPROTO;
 if(!ret){dma_rmb();ret=frame_check(m);}
 if(!ret && copy_to_user(u64_to_user_ptr(p->data),m->buffer,m->bytes))ret=-EFAULT;
 if(!ret){m->received=true;p->id=id;p->generation=gen;p->bytes=m->bytes;p->records=count;p->actual=m->actual;p->status=m->status;}
unlock:mutex_unlock(&m->life);mutex_unlock(&m->producer);
 if(ret && READ_ONCE(m->owned))cancel(m,false);
 return ret;
}
static int config(struct rs485_owner *m,struct rs485_config *c)
{
 u32 value,gen;int ret=0,i;
 if(c->mask&~RG_QUERY_VALID_MASK||c->run>1)return -EINVAL;
 for(i=0;i<5;i++)if(c->periods[i] && (c->periods[i]<1000||c->periods[i]>2147483647U))return -ERANGE;
 mutex_lock(&m->gp_lock);gen=gr(m,GR(GENERATION));
 if(gr(m,GR(RUN))){ret=-EBUSY;goto out;}
 if(m->txn==U32_MAX){ret=-EOVERFLOW;goto out;}
 c->id=++m->txn;
 for(i=0;i<5;i++)gw(m,GR(SHADOW_PERIOD0)+4*i,c->periods[i]);
 gw(m,GR(SHADOW_MASK),c->mask);gw(m,GR(TXN_ID),c->id);gw(m,GR(CFG_SUBMIT),1);
 ret=readl_poll_timeout(m->gp+GR(CFG_STATE),value,(value&(RG_CFG_APPLIED|RG_CFG_REJECTED))!=0,10,2000000);
 if(!ret && (gr(m,GR(CFG_TXN))!=c->id||gr(m,GR(GENERATION))!=gen))ret=-ESTALE;
 c->generation=gr(m,GR(CFG_GENERATION));c->revision=gr(m,GR(CFG_REVISION));c->apply_sequence=gr(m,GR(CFG_SEQUENCE));c->error=gr(m,GR(CFG_ERROR));
 c->notified_us=(u64)gr(m,GR(CFG_TIME_HI))<<32|gr(m,GR(CFG_TIME_LO));
 if(!ret && c->error)ret=-EINVAL;
 if(!ret){gw(m,GR(RUN),c->run);if(gr(m,GR(RUN))!=c->run)ret=-EACCES;}
out:mutex_unlock(&m->gp_lock);return ret;
}
static int snapshot(struct rs485_owner *m,struct rs485_snapshot *s)
{
 u32 gen;int i,ret=0;mutex_lock(&m->snap);
 if(m->snap_id==U32_MAX){ret=-EOVERFLOW;goto out;}
 s->id=++m->snap_id;gen=gr(m,GR(GENERATION));
 tw(m,RR(SNAP_REQ_ID),s->id);tw(m,RR(SNAP_SUBMIT),1);tr(m,RR(SNAP_STATUS));
 for(i=0;i<32;i++)s->word[i]=tr(m,RT_SNAPSHOT_BASE+4*i);
 for(i=0;i<480;i++)s->word[32+i]=tr(m,RT_ROW_BASE+4*i);
 s->generation=gen;
 if(!tr(m,RR(SNAP_STATUS))||tr(m,RR(SNAP_ID))!=s->id||gr(m,GR(GENERATION))!=gen||s->word[RT_SNAP_GENERATION]!=gen)ret=-ESTALE;
out:mutex_unlock(&m->snap);return ret;
}
static int set_run(struct rs485_owner *m,struct rs485_run *r)
{
 int ret=0;
 if(r->run>1)return -EINVAL;
 mutex_lock(&m->gp_lock);
 gw(m,GR(RUN),r->run);
 if(gr(m,GR(RUN))!=r->run)ret=-EACCES;
 r->generation=gr(m,GR(GENERATION));r->revision=gr(m,GR(CFG_REVISION));
 r->busy=gr(m,GR(STATUS));
 mutex_unlock(&m->gp_lock);return ret;
}
static int diag(struct rs485_owner *m,struct rs485_diag *d)
{
 int i,ret=0;u32 gen;gen=gr(m,GR(GENERATION));
 if(!(gr(m,GR(CAPTURE_STATUS))&RG_CAP_VALID_MASK)){
  if(!gr(m,GR(FIFO_LEVEL))){ret=-EAGAIN;goto out;}gw(m,GR(CAPTURE),1);
 }
 d->id=gr(m,GR(CAPTURE_ID));d->generation=gr(m,GR(CAPTURE_GENERATION));d->revision=gr(m,GR(CAPTURE_REVISION));
 for(i=0;i<8;i++)d->word[i]=gr(m,GR(WORD0)+4*i);
 if(gen!=gr(m,GR(GENERATION))||gen!=d->generation||d->id!=gr(m,GR(CAPTURE_ID)))ret=-ESTALE;
 /* Only consume after caller has received all words (ioctl dispatch below). */
out:return ret;
}
static long io(struct file *f,unsigned int op,unsigned long arg)
{
 struct rs485_owner *m=f->private_data;void __user *u=(void __user *)arg;int ret=0;
 if(!capable(CAP_SYS_RAWIO))return -EPERM;
 if(m->quarantine && op!=RS485_STATE)return -EIO;
 switch(op){
 case RS485_RUN:{struct rs485_run r;if(copy_from_user(&r,u,sizeof(r)))return -EFAULT;ret=set_run(m,&r);if(copy_to_user(u,&r,sizeof(r)))return -EFAULT;return ret;}
 case RS485_STATE:{struct rs485_state s={m->blocked,m->owned,m->quarantine,m->generation,m->packet_id,m->bytes,m->actual,m->status};return copy_to_user(u,&s,sizeof(s))?-EFAULT:0;}
 case RS485_CONFIG:{struct rs485_config c;if(copy_from_user(&c,u,sizeof(c)))return -EFAULT;ret=config(m,&c);if(copy_to_user(u,&c,sizeof(c)))return -EFAULT;return ret;}
 case RS485_SNAPSHOT:{struct rs485_snapshot *s=kzalloc(sizeof(*s),GFP_KERNEL);if(!s)return -ENOMEM;ret=snapshot(m,s);if(!ret&&copy_to_user(u,s,sizeof(*s)))ret=-EFAULT;kfree(s);return ret;}
 case RS485_DIAG:{struct rs485_diag d;mutex_lock(&m->gp_lock);ret=diag(m,&d);if(!ret){if(d.generation!=gr(m,GR(GENERATION))||d.id!=gr(m,GR(CAPTURE_ID)))ret=-ESTALE;else if(copy_to_user(u,&d,sizeof(d)))ret=-EFAULT;else gw(m,GR(CONSUME_ID),d.id);}mutex_unlock(&m->gp_lock);return ret;}
 case RS485_RX:{struct rs485_packet p;if(copy_from_user(&p,u,sizeof(p)))return -EFAULT;ret=receive(m,&p);if(!ret&&copy_to_user(u,&p,sizeof(p)))return cancel(m,false)?:-EFAULT;return ret;}
 case RS485_COMPLETE:{struct rs485_packet p;if(copy_from_user(&p,u,sizeof(p)))return -EFAULT;mutex_lock(&m->producer);mutex_lock(&m->life);
  if(m->blocked||!m->owned||!m->received||p.id!=m->packet_id||p.generation!=m->generation||p.bytes!=m->bytes)ret=-ESTALE;
  else{tw(m,RR(COMPLETE_ID),p.id);tw(m,RR(COMPLETE_GEN),p.generation);tw(m,RR(COMPLETE_RESULT),0);tw(m,RR(COMPLETE),1);tr(m,RR(STATUS));ret=bsp_telem_dma_retire(m->rx,m->cookie);if(!ret){m->owned=false;m->received=false;rearm_telem(m);}}
  mutex_unlock(&m->life);mutex_unlock(&m->producer);if(ret&&m->owned)cancel(m,false);return ret;}
 case RS485_RECOVER:return cancel(m,true);
 case RS485_CANCEL:return cancel(m,false);
 case RS485_RELEASE:ret=cancel(m,false);if(!ret){mutex_lock(&m->gp_lock);gw(m,GR(RUN),0);mutex_unlock(&m->gp_lock);mutex_lock(&m->producer);if(m->buffer){dma_free_coherent(m->dma_dev,RX_CAPACITY,m->buffer,m->dma);m->buffer=NULL;}m->released=true;mutex_unlock(&m->producer);}return ret;
 default:return -ENOTTY;
 }
}
static int open_owner(struct inode *inode,struct file *f)
{
 struct rs485_owner *m=container_of(f->private_data,struct rs485_owner,misc);int ret=0;
 if(!capable(CAP_SYS_RAWIO))return -EPERM;
 mutex_lock(&m->life);if(m->opened||m->released||m->quarantine)ret=-EBUSY;else{m->opened=true;f->private_data=m;}mutex_unlock(&m->life);return ret;
}
static int close_owner(struct inode *inode,struct file *f)
{
 struct rs485_owner *m=f->private_data;int ret=cancel(m,false);
 mutex_lock(&m->gp_lock);gw(m,GR(RUN),0);mutex_unlock(&m->gp_lock);
 if(!ret)m->opened=false;
 return ret;
}
static const struct file_operations ops={.owner=THIS_MODULE,.open=open_owner,.release=close_owner,.unlocked_ioctl=io,.poll=poll_owner,.llseek=no_llseek};
/* Read-only lifecycle observation; no open, cancel, consume or MMIO side effect. */
static ssize_t integration_state_show(struct device *dev,struct device_attribute *attr,char *buf)
{
 struct rs485_owner *m=dev_get_drvdata(dev);ssize_t n;
 mutex_lock(&m->life);
 n=sysfs_emit(buf,"{\"blocked\":%u,\"owned\":%u,\"quarantine\":%u,\"buffer_allocated\":%u,\"generation\":%u,\"packet_id\":%u,\"packet_bytes\":%u,\"actual\":%u,\"dma_status\":%u,\"dma_done\":%u,\"drain_validated\":%u}\n",
 m->blocked,m->owned,m->quarantine,m->buffer!=NULL,m->generation,m->packet_id,m->bytes,m->actual,m->status,m->dma_done,m->drain_validated);
 mutex_unlock(&m->life);return n;
}
static DEVICE_ATTR_RO(integration_state);
static struct attribute *integration_attrs[]={&dev_attr_integration_state.attr,NULL};
static const struct attribute_group integration_group={.attrs=integration_attrs};
static int probe(struct platform_device *p)
{
 struct rs485_owner *m;struct resource *a,*b;int ret;
 a=platform_get_resource(p,IORESOURCE_MEM,0);b=platform_get_resource(p,IORESOURCE_MEM,1);
 if(!a||!b||a->start!=RG_BASE||resource_size(a)!=RG_SIZE||b->start!=RT_BASE||resource_size(b)!=RT_SIZE)return -EINVAL;
 m=devm_kzalloc(&p->dev,sizeof(*m),GFP_KERNEL);if(!m)return -ENOMEM;
 m->dev=&p->dev;m->gp=devm_platform_ioremap_resource(p,0);m->telem=devm_platform_ioremap_resource(p,1);
 m->drain_validated=of_property_read_bool(p->dev.of_node,"bsp,validated-hp1-reset-drain");
 if(IS_ERR(m->gp)||IS_ERR(m->telem))return -EINVAL;
 if(gr(m,GR(VERSION))!=SI_COLLECTOR_VERSION||gr(m,GR(PROFILE))!=SI_COLLECTOR_PROFILE||gr(m,GR(CAPS))!=SI_COLLECTOR_CAPS||gr(m,GR(FEATURES))!=SI_COLLECTOR_FEATURES||tr(m,RR(VERSION))!=RT_VERSION||tr(m,RR(PROFILE))!=RT_PROFILE||tr(m,RR(CAPS))!=RT_CAPS||tr(m,RR(FEATURES))!=RT_FEATURES)return -ENODEV;
 mutex_init(&m->life);mutex_init(&m->producer);mutex_init(&m->gp_lock);mutex_init(&m->snap);spin_lock_init(&m->lock);init_completion(&m->completion);m->blocked=true;
 init_waitqueue_head(&m->wait);
 m->gp_irq=platform_get_irq(p,0);m->telem_irq=platform_get_irq(p,1);
 if(m->gp_irq<0||m->telem_irq<0)return -EINVAL;
 ret=devm_request_irq(&p->dev,m->gp_irq,irq,0,"bsp-rs485-gp",m);if(ret)return ret;
 ret=devm_request_irq(&p->dev,m->telem_irq,irq,0,"bsp-rs485-cache",m);if(ret)return ret;
 gw(m,GR(IRQ_MASK),0);tw(m,RR(IRQ_MASK),0);gw(m,GR(RUN),0);tw(m,RR(ENABLE),0);
 m->rx=dma_request_chan(&p->dev,"telemetry");if(IS_ERR(m->rx))return PTR_ERR(m->rx);
 m->dma_dev=dmaengine_get_dma_device(m->rx);ret=dma_set_mask_and_coherent(m->dma_dev,DMA_BIT_MASK(32));if(ret)goto channel;
 ret=dmaengine_terminate_sync(m->rx);if(!ret)ret=bsp_telem_dma_quiescent(m->rx);if(ret)goto channel;
 m->buffer=dma_alloc_coherent(m->dma_dev,RX_CAPACITY,&m->dma,GFP_KERNEL);if(!m->buffer){ret=-ENOMEM;goto channel;}
 if((m->dma&7)||upper_32_bits(m->dma)){ret=-EINVAL;goto buffer;}
 m->txn=gr(m,GR(CFG_TXN));m->snap_id=tr(m,RR(SNAP_ID));m->generation=tr(m,RR(TRANSPORT_GEN));
 m->misc=(struct miscdevice){.minor=MISC_DYNAMIC_MINOR,.name="bsp-rs485",.fops=&ops,.parent=&p->dev,.mode=0600};ret=misc_register(&m->misc);if(ret)goto buffer;
 platform_set_drvdata(p,m);ret=devm_device_add_group(&p->dev,&integration_group);if(ret){misc_deregister(&m->misc);goto buffer;}return 0;
buffer:dma_free_coherent(m->dma_dev,RX_CAPACITY,m->buffer,m->dma);
channel:dma_release_channel(m->rx);return ret;
}
static int remove_owner(struct platform_device *p)
{
 struct rs485_owner *m=platform_get_drvdata(p);int ret;
 if(m->opened||m->quarantine)return -EBUSY;
 ret=cancel(m,false);if(ret)return ret;
 misc_deregister(&m->misc);if(m->buffer)dma_free_coherent(m->dma_dev,RX_CAPACITY,m->buffer,m->dma);dma_release_channel(m->rx);return 0;
}
static const struct of_device_id ids[]={{.compatible="bsp,rs485-telemetry-r5s2"},{}};
MODULE_DEVICE_TABLE(of,ids);
static struct platform_driver rs485_driver={.probe=probe,.remove=remove_owner,.driver={.name="bsp-rs485",.of_match_table=ids,.suppress_bind_attrs=true}};
module_platform_driver(rs485_driver);
MODULE_LICENSE("GPL");MODULE_DESCRIPTION("Independent no-motor HP1 RS485 telemetry owner");
