// SPDX-License-Identifier: GPL-2.0
/* Explicit no-motor diagnostics. No automatic owner, heartbeat or motion. */
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/of.h>
#include <linux/io.h>
#include <linux/iopoll.h>
#include <linux/interrupt.h>
#include <linux/irq.h>
#include <linux/miscdevice.h>
#include <linux/fs.h>
#include <linux/uaccess.h>
#include <linux/capability.h>
#include <linux/mutex.h>
#include "safety_uapi.h"
#include "interlock_defs.h"
#include "safety_defs.h"
struct diag { void __iomem *base; struct miscdevice misc; struct mutex lock; bool opened; atomic_t irq_events; };
static u32 rd(struct diag *d,u32 off) { return readl(d->base+off); }
static void wr(struct diag *d,u32 off,u32 v) { writel(v,d->base+off); }
static int identify(struct diag *d)
{
 return rd(d,SAF_REGISTERS_VERSION)==SI_VERSION && rd(d,SAF_REGISTERS_PROFILE)==SI_PROFILE &&
 rd(d,SAF_REGISTERS_CAPS)==SI_CAPS && rd(d,SAF_REGISTERS_FEATURES)==SI_FEATURES ? 0:-ENODEV;
}
static irqreturn_t diagnostic_irq(int irq,void *data)
{
 struct diag *d=data;u32 bits=rd(d,SAF_REGISTERS_IRQ_PENDING)&rd(d,SAF_REGISTERS_IRQ_MASK);
 (void)irq;
 if(!bits)return IRQ_NONE;
 /* Preserve latched events/faults; mask an unexpected active source, never W1C. */
 wr(d,SAF_REGISTERS_IRQ_MASK,0);rd(d,SAF_REGISTERS_IRQ_MASK);
 atomic_inc(&d->irq_events);return IRQ_HANDLED;
}
static int snapshot(struct diag *d,struct saf2_snapshot *s)
{
 u32 id; unsigned i; int ret=identify(d); if(ret)return ret;
 s->version=SI_VERSION;s->profile=SI_PROFILE;s->caps=SI_CAPS;s->features=SI_FEATURES;
 s->config_valid=rd(d,SAF_REGISTERS_CONFIG_VALID);
 for(i=0;i<8;i++)s->config_id[i]=rd(d,SAF_REGISTERS_CONFIG_ID_0+4*i);
 s->irq_pending=rd(d,SAF_REGISTERS_IRQ_PENDING);s->irq_mask=rd(d,SAF_REGISTERS_IRQ_MASK);
 s->irq_events=atomic_read(&d->irq_events);
 s->config_accepted=rd(d,SI_REG_CONFIG_ACCEPTED);s->config_applied=rd(d,SI_REG_CONFIG_APPLIED);
 id=rd(d,SAF_REGISTERS_SNAP_REQ);if(id==U32_MAX)return -EOVERFLOW;s->global_id=id+1;
 wr(d,SAF_REGISTERS_SNAP_REQ,s->global_id);
 if(rd(d,SAF_REGISTERS_SNAP_REQ)!=s->global_id)return -ESTALE;
 for(i=0;i<64;i++)s->global[i]=rd(d,SAF_SNAPSHOT_BASE+4*i);
 if(rd(d,SAF_REGISTERS_SNAP_REQ)!=s->global_id || s->global[SAF_SNAPSHOT_SNAP_ID]!=s->global_id)return -ESTALE;
 id=rd(d,SI_REG_SNAP_ID);if(id==U32_MAX)return -EOVERFLOW;s->interlock_id=id+1;
 wr(d,SI_REG_SNAP_REQ,s->interlock_id);
 if(rd(d,SI_REG_SNAP_ID)!=s->interlock_id)return -ESTALE;
 for(i=0;i<32;i++)s->interlock[i]=rd(d,SI_SNAPSHOT_BASE+4*i);
 return rd(d,SI_REG_SNAP_ID)==s->interlock_id ? 0:-ESTALE;
}
static bool idle(struct diag *d)
{
 u32 s=rd(d,SI_REG_STATUS);
 return (s&SI_STATUS_DRAINED) && !(s&(SI_STATUS_OWNER_ACTIVE|SI_STATUS_POLL_RUN|SI_STATUS_CONFIG_PENDING));
}
static long control(struct file *f,unsigned int op,unsigned long arg)
{
 struct diag *d=f->private_data; int ret=0; u32 v;
 if(!capable(CAP_SYS_RAWIO))return -EPERM;
 mutex_lock(&d->lock);
 ret=identify(d);if(ret)goto out;
 switch(op){
 case SAF2_SNAPSHOT:{struct saf2_snapshot s={0};ret=snapshot(d,&s);
  if(!ret && copy_to_user((void __user *)arg,&s,sizeof(s)))ret=-EFAULT;
  break;}
 case SAF2_CONFIG:{struct saf2_config c;
  if(copy_from_user(&c,(void __user *)arg,sizeof(c))){ret=-EFAULT;break;}
  if(!c.txn || !c.axes || c.axes>7 || c.feedback_us<SI_TIMEOUT_MIN_US || c.feedback_us>SI_TIMEOUT_MAX_US ||
     c.watchdog_us<SI_TIMEOUT_MIN_US || c.watchdog_us>SI_TIMEOUT_MAX_US){ret=-EINVAL;break;}
  if(!idle(d)){ret=-EBUSY;break;}
  /* Fresh txn only; PL remains the final admission authority. */
  if(c.txn<=rd(d,SI_REG_CONFIG_ACCEPTED)){ret=-ESTALE;break;}
  wr(d,SI_REG_SHADOW_AXES,c.axes);wr(d,SI_REG_SHADOW_FEEDBACK_US,c.feedback_us);
  wr(d,SI_REG_SHADOW_WATCHDOG_US,c.watchdog_us);wr(d,SI_REG_CONFIG_TXN,c.txn);wr(d,SI_REG_CONFIG_COMMIT,1);
  if(rd(d,SI_REG_CONFIG_ACCEPTED)!=c.txn){ret=-EACCES;break;}
  ret=readl_poll_timeout(d->base+SI_REG_CONFIG_APPLIED,v,v==c.txn,10,100000);
  if(!ret && (rd(d,SI_REG_ACTIVE_AXES)!=c.axes || rd(d,SI_REG_ACTIVE_FEEDBACK_US)!=c.feedback_us ||
              rd(d,SI_REG_ACTIVE_WATCHDOG_US)!=c.watchdog_us))ret=-EIO;
  break;}
 case SAF2_TIMEOUT_TEST:
  /* No old-owner takeover. The experiment deliberately lets the new owner expire.
   * Releasing this fd or restarting the utility never closes/feeds that owner. */
  if(!idle(d) || rd(d,SI_REG_CAUSES)){ret=-EBUSY;break;}
  wr(d,SI_REG_OWNER_OPEN,1);v=rd(d,SI_REG_STATUS);
  if(!(v&SI_STATUS_OWNER_ACTIVE) || (!rd(d,SI_REG_OWNER_LO)&&!rd(d,SI_REG_OWNER_HI)))ret=-EACCES;
  break;
 default:ret=-ENOTTY;
 }
out:mutex_unlock(&d->lock);return ret;
}
static int open_diag(struct inode *inode,struct file *f)
{
 struct diag *d=container_of(f->private_data,struct diag,misc);int ret=0;
 if(!capable(CAP_SYS_RAWIO))return -EPERM;
 mutex_lock(&d->lock);if(d->opened)ret=-EBUSY;else{d->opened=true;f->private_data=d;}mutex_unlock(&d->lock);return ret;
}
static int close_diag(struct inode *inode,struct file *f)
{struct diag *d=f->private_data;mutex_lock(&d->lock);d->opened=false;mutex_unlock(&d->lock);return 0;}
static const struct file_operations ops={.owner=THIS_MODULE,.open=open_diag,.release=close_diag,.unlocked_ioctl=control,.llseek=no_llseek};
static int probe(struct platform_device *p)
{
 struct diag *d;struct irq_data *irq_data;struct resource *r=platform_get_resource(p,IORESOURCE_MEM,0);int ret,irq;
 if(!r || r->start!=SI_BASE || resource_size(r)!=SI_SIZE)return -EINVAL;
 d=devm_kzalloc(&p->dev,sizeof(*d),GFP_KERNEL);if(!d)return -ENOMEM;
 d->base=devm_platform_ioremap_resource(p,0);if(IS_ERR(d->base))return PTR_ERR(d->base);
 ret=identify(d);if(ret)return ret;mutex_init(&d->lock);
 /* No IRQ mask or W1C mutation on bind. IRQ stays masked until future qualified backend. */
 if(rd(d,SAF_REGISTERS_IRQ_MASK))return -EBUSY;
 irq=platform_get_irq(p,0);if(irq<0)return irq;
 irq_data=irq_get_irq_data(irq);
 if(!irq_data || irq_data->hwirq!=SAF_IRQ_INTID || irq_get_trigger_type(irq)!=IRQ_TYPE_LEVEL_HIGH)return -EINVAL;
 atomic_set(&d->irq_events,0);
 ret=devm_request_irq(&p->dev,irq,diagnostic_irq,0,"bsp-saf2-diag",d);if(ret)return ret;
 d->misc=(struct miscdevice){.minor=MISC_DYNAMIC_MINOR,.name="bsp-saf2-diag",.fops=&ops,.parent=&p->dev,.mode=0600};
 ret=misc_register(&d->misc);if(!ret)platform_set_drvdata(p,d);return ret;
}
static int remove_diag(struct platform_device *p)
{struct diag *d=platform_get_drvdata(p);misc_deregister(&d->misc);return 0;}
static const struct of_device_id ids[]={{.compatible="bsp,saf2-diagnostic-v1"},{}};
MODULE_DEVICE_TABLE(of,ids);
static struct platform_driver saf2_driver={.probe=probe,.remove=remove_diag,.driver={.name="bsp-saf2-diag",.of_match_table=ids,.suppress_bind_attrs=true}};
module_platform_driver(saf2_driver);
MODULE_LICENSE("GPL");MODULE_DESCRIPTION("Explicit no-motor SAF2 diagnostic owner; no motion or heartbeat daemon");
