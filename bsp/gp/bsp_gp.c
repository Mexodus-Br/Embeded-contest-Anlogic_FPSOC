// SPDX-License-Identifier: GPL-2.0
/* Minimum probe profile only. No mmap, DMA, reset or motion entry points. */
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/of.h>
#include <linux/miscdevice.h>
#include <linux/io.h>
#include <linux/interrupt.h>
#include <linux/irq.h>
#include <linux/poll.h>
#include <linux/uaccess.h>
#include <linux/compat.h>
#include <linux/kref.h>
#include <linux/slab.h>
#include <linux/delay.h>
#include <linux/iopoll.h>
#include <linux/capability.h>
#include "gp_uapi.h"
#include "generated/gp_defs.h"

#define PROFILE(x) PLI_GP_GP_CONTROL_PROBE_V1_##x
struct gp_device {
 void __iomem *base;
 struct miscdevice misc;
 struct mutex lock;
 spinlock_t irq_lock;
 wait_queue_head_t wait;
 struct kref ref;
 bool dying, opened, cached;
 int irq;
 u32 last_opcode, last_id, events;
 u64 count;
};
struct gp_file { struct gp_device *g; u64 seen; };
static u32 rd(struct gp_device *g, u32 offset) { return readl(g->base + offset); }
static void wr(struct gp_device *g, u32 offset, u32 value) { writel(value, g->base + offset); }
static u64 pair(struct gp_device *g, u32 lo, u32 hi)
{ return (u64)rd(g, hi) << 32 | rd(g, lo); }
static void drop(struct kref *ref) { kfree(container_of(ref, struct gp_device, ref)); }

static irqreturn_t gp_irq(int irq, void *data)
{
 struct gp_device *g = data;
 unsigned long flags;
 u32 active;
 spin_lock_irqsave(&g->irq_lock, flags);
 active = rd(g, PLI_REG_IRQ_PENDING) & rd(g, PLI_REG_IRQ_MASK);
 if (!active) { spin_unlock_irqrestore(&g->irq_lock, flags); return IRQ_NONE; }
 /* Leave source/pending observable. Mask before returning to prevent storm.
  * Rearm is explicit: remove source -> W1C -> readback -> mask. */
 wr(g, PLI_REG_IRQ_MASK, 0);
 rd(g, PLI_REG_IRQ_MASK);
 g->events |= active;
 g->count++;
 spin_unlock_irqrestore(&g->irq_lock, flags);
 wake_up_interruptible(&g->wait);
 return IRQ_HANDLED;
}
static int gp_open(struct inode *inode, struct file *file)
{
 struct gp_device *g = container_of(file->private_data, struct gp_device, misc);
 struct gp_file *f;
 unsigned long flags;
 int ret = 0;
 if (!capable(CAP_SYS_RAWIO)) return -EPERM;
 f = kzalloc(sizeof(*f), GFP_KERNEL);
 if (!f) return -ENOMEM;
 mutex_lock(&g->lock);
 if (g->dying) ret = -ENODEV;
 else if (g->opened) ret = -EBUSY;
 else {
  g->opened = true;
  g->cached = false;
  kref_get(&g->ref);
  f->g = g;
  spin_lock_irqsave(&g->irq_lock, flags);
  f->seen = g->count;
  g->events = 0;
  spin_unlock_irqrestore(&g->irq_lock, flags);
  file->private_data = f;
 }
 mutex_unlock(&g->lock);
 if (ret) kfree(f);
 return ret;
}
static int gp_release(struct inode *inode, struct file *file)
{
 struct gp_file *f = file->private_data;
 struct gp_device *g = f->g;
 unsigned long flags;
 mutex_lock(&g->lock);
 if (!g->dying) {
  spin_lock_irqsave(&g->irq_lock, flags);
  wr(g, PLI_REG_IRQ_MASK, 0);
  wr(g, PLI_REG_TEST_IRQ_LEVEL, 0);
  wr(g, PLI_REG_IRQ_PENDING, PROFILE(IRQ_PENDING_MASK));
  rd(g, PLI_REG_IRQ_PENDING);
  spin_unlock_irqrestore(&g->irq_lock, flags);
 }
 g->opened = false;
 mutex_unlock(&g->lock);
 kref_put(&g->ref, drop);
 kfree(f);
 return 0;
}
static __poll_t gp_poll(struct file *file, poll_table *wait)
{
 struct gp_file *f = file->private_data;
 struct gp_device *g = f->g;
 unsigned long flags;
 __poll_t result = 0;
 poll_wait(file, &g->wait, wait);
 spin_lock_irqsave(&g->irq_lock, flags);
 if (READ_ONCE(g->dying)) result = EPOLLHUP | EPOLLERR;
 else if (g->count != f->seen) result = EPOLLIN | EPOLLRDNORM;
 spin_unlock_irqrestore(&g->irq_lock, flags);
 return result;
}
static int command(struct gp_device *g, struct gp_command *c)
{
 u32 id, status, before, after;
 int ret;
 if (c->reserved || c->repeat > 1 ||
     (c->opcode != PLI_CMD_NOP && c->opcode != PLI_CMD_SNAPSHOT)) return -EINVAL;
 if (rd(g, PLI_REG_CMD_STATUS) & PLI_REG_CMD_STATUS_BUSY_MASK) return -EBUSY;
 id = rd(g, PLI_REG_LAST_TXN_ID);
 if (c->repeat) {
  if (!g->cached || id != g->last_id || c->opcode != g->last_opcode) return -EINVAL;
 } else {
  if (id == U32_MAX) return -EOVERFLOW;
  id++;
 }
 wr(g, PLI_REG_CMD_OPCODE, c->opcode);
 wr(g, PLI_REG_CMD_ARG, 0);
 wr(g, PLI_REG_TXN_ID, id);
 /* Ordered Device MMIO, followed by completion reads. No userspace address. */
 wr(g, PLI_REG_CMD_SUBMIT, 1);
 ret = read_poll_timeout(rd, status,
   (status & PLI_REG_CMD_STATUS_ACK_VALID_MASK) &&
   (status & PLI_REG_CMD_STATUS_COMPLETED_MASK) && rd(g, PLI_REG_ACK_ID) == id,
   10, 100000, false, g, PLI_REG_CMD_STATUS);
 if (ret) { g->cached = false; return ret; }
 g->last_id = id; g->last_opcode = c->opcode; g->cached = true;
 memset(c, 0, sizeof(*c));
 c->opcode = g->last_opcode; c->txn = id; c->status = status;
 c->error = rd(g, PLI_REG_ACK_ERROR);
 if (c->error || !(status & PLI_REG_CMD_STATUS_ACCEPTED_MASK)) return -EIO;
 if (c->opcode != PLI_CMD_SNAPSHOT) return 0;
 before = rd(g, PLI_REG_SNAP_ID);
 if (!rd(g, PLI_REG_SNAP_VALID) || before != id) return -EAGAIN;
 c->timestamp = pair(g, PLI_REG_SNAP_TIME_LO, PLI_REG_SNAP_TIME_HI);
#define AXIS(n) \
 c->position[n] = pair(g, PLI_REG_SNAP_A##n##_POSITION_LO, PLI_REG_SNAP_A##n##_POSITION_HI); \
 c->pulses[n] = pair(g, PLI_REG_SNAP_A##n##_PULSE_LO, PLI_REG_SNAP_A##n##_PULSE_HI)
 AXIS(0); AXIS(1); AXIS(2); AXIS(3);
#undef AXIS
 c->session = pair(g, PLI_REG_SNAP_SESSION_LO, PLI_REG_SNAP_SESSION_HI);
 c->state = rd(g, PLI_REG_SNAP_STATE);
 c->position_valid = rd(g, PLI_REG_SNAP_POSITION_VALID);
 c->accepted_seq = rd(g, PLI_REG_SNAP_ACCEPTED_SEQ);
 c->done_seq = rd(g, PLI_REG_SNAP_DONE_SEQ);
 after = rd(g, PLI_REG_SNAP_ID);
 if (after != before || !rd(g, PLI_REG_SNAP_VALID)) return -EAGAIN;
 c->snapshot_id = after; c->snapshot_valid = 1;
 return 0;
}
static long gp_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
{
 struct gp_file *f = file->private_data;
 struct gp_device *g = f->g;
 void __user *user = (void __user *)arg;
 unsigned long flags;
 long ret = 0;
 union { struct gp_identity id; struct gp_scratch scratch; struct gp_command command;
         struct gp_irq_config irq; struct gp_event event; } u;
 size_t size;
 switch (cmd) {
 case GP_IDENTITY: size = sizeof(u.id); break;
 case GP_SCRATCH: size = sizeof(u.scratch); break;
 case GP_COMMAND: size = sizeof(u.command); break;
 case GP_IRQ_CONFIG: size = sizeof(u.irq); break;
 case GP_EVENT: size = sizeof(u.event); break;
 default: return -ENOTTY;
 }
 memset(&u, 0, sizeof(u));
 if ((cmd == GP_SCRATCH || cmd == GP_COMMAND || cmd == GP_IRQ_CONFIG) &&
     copy_from_user(&u, user, size)) return -EFAULT;
 if (mutex_lock_interruptible(&g->lock)) return -ERESTARTSYS;
 if (g->dying) { ret = -ENODEV; goto out; }
 switch (cmd) {
 case GP_IDENTITY:
  u.id = (struct gp_identity){ rd(g, PLI_REG_VERSION), rd(g, PLI_REG_CAPS),
   rd(g, PLI_REG_FEATURES), rd(g, PLI_REG_TICK_HZ), rd(g, PLI_REG_LAST_TXN_ID), rd(g, PLI_REG_STATE) };
  break;
 case GP_SCRATCH:
  wr(g, PLI_REG_TEST_RW, u.scratch.value);
  if (rd(g, PLI_REG_TEST_RW) != u.scratch.value) ret = -EIO;
  break;
 case GP_COMMAND: ret = command(g, &u.command); break;
 case GP_IRQ_CONFIG:
  if ((u.irq.mask | u.irq.clear) & ~PROFILE(IRQ_PENDING_MASK) || u.irq.source > 1) { ret = -EINVAL; break; }
  spin_lock_irqsave(&g->irq_lock, flags);
  wr(g, PLI_REG_IRQ_MASK, 0);
  wr(g, PLI_REG_TEST_IRQ_LEVEL, u.irq.source);
  wr(g, PLI_REG_IRQ_PENDING, u.irq.clear);
  /* Drain posted writes before restoring the requested interrupt mask. */
  u.irq.pending = rd(g, PLI_REG_IRQ_PENDING);
  wr(g, PLI_REG_IRQ_MASK, u.irq.mask);
  u.irq.actual_mask = rd(g, PLI_REG_IRQ_MASK);
  u.irq.actual_source = rd(g, PLI_REG_TEST_IRQ_LEVEL);
  spin_unlock_irqrestore(&g->irq_lock, flags);
  break;
 case GP_EVENT:
  spin_lock_irqsave(&g->irq_lock, flags);
  u.event.count = g->count; u.event.pending = g->events;
  spin_unlock_irqrestore(&g->irq_lock, flags);
  break;
 }
 if (!ret && copy_to_user(user, &u, size)) ret = -EFAULT;
 if (!ret && cmd == GP_EVENT) {
  /* Preserve events arriving during copy_to_user for the next poll. */
  spin_lock_irqsave(&g->irq_lock, flags);
  f->seen = u.event.count;
  if (g->count == u.event.count) g->events = 0;
  spin_unlock_irqrestore(&g->irq_lock, flags);
 }
out:
 mutex_unlock(&g->lock);
 return ret;
}
static const struct file_operations gp_fops = {
 .owner = THIS_MODULE, .open = gp_open, .release = gp_release,
 .unlocked_ioctl = gp_ioctl,
#ifdef CONFIG_COMPAT
 .compat_ioctl = compat_ptr_ioctl,
#endif
 .poll = gp_poll, .llseek = no_llseek,
};
static int gp_probe(struct platform_device *pdev)
{
 struct gp_device *g;
 struct resource *res = platform_get_resource(pdev, IORESOURCE_MEM, 0);
 int ret;
 if (!res || res->start != PROFILE(BASE) || resource_size(res) != PROFILE(SIZE)) return -EINVAL;
 g = kzalloc(sizeof(*g), GFP_KERNEL);
 if (!g) return -ENOMEM;
 kref_init(&g->ref); mutex_init(&g->lock); spin_lock_init(&g->irq_lock); init_waitqueue_head(&g->wait);
 g->base = devm_ioremap_resource(&pdev->dev, res);
 if (IS_ERR(g->base)) { ret = PTR_ERR(g->base); goto fail; }
 g->irq = platform_get_irq(pdev, 0);
 if (g->irq < 0) { ret = g->irq; goto fail; }
 if (irq_get_trigger_type(g->irq) != IRQ_TYPE_LEVEL_HIGH) { ret = -EINVAL; goto fail; }
 if (rd(g, PLI_REG_VERSION) != PROFILE(EXPECTED_VERSION) ||
     rd(g, PLI_REG_CAPS) != PROFILE(EXPECTED_CAPS) ||
     rd(g, PLI_REG_FEATURES) != PROFILE(EXPECTED_FEATURES) ||
     rd(g, PLI_REG_TICK_HZ) != PROFILE(EXPECTED_TICK_HZ)) { ret = -ENODEV; goto fail; }
 wr(g, PLI_REG_IRQ_MASK, 0); wr(g, PLI_REG_TEST_IRQ_LEVEL, 0);
 wr(g, PLI_REG_IRQ_PENDING, PROFILE(IRQ_PENDING_MASK)); rd(g, PLI_REG_IRQ_PENDING);
 ret = request_threaded_irq(g->irq, NULL, gp_irq, IRQF_ONESHOT, "bsp-gp", g);
 if (ret) goto fail;
 g->misc = (struct miscdevice){ .minor = MISC_DYNAMIC_MINOR, .name = "bsp-gp", .fops = &gp_fops, .parent = &pdev->dev, .mode = 0600 };
 ret = misc_register(&g->misc);
 if (ret) { free_irq(g->irq, g); goto fail; }
 platform_set_drvdata(pdev, g);
 dev_info(&pdev->dev, "GP probe ABI verified; Linux IRQ %d; no motion/DMA\n", g->irq);
 return 0;
fail:
 kref_put(&g->ref, drop);
 return ret;
}
static int gp_remove(struct platform_device *pdev)
{
 struct gp_device *g = platform_get_drvdata(pdev);
 unsigned long flags;
 misc_deregister(&g->misc);
 mutex_lock(&g->lock);
 spin_lock_irqsave(&g->irq_lock, flags);
 WRITE_ONCE(g->dying, true); wr(g, PLI_REG_IRQ_MASK, 0); rd(g, PLI_REG_IRQ_MASK);
 spin_unlock_irqrestore(&g->irq_lock, flags);
 mutex_unlock(&g->lock);
 free_irq(g->irq, g);
 wake_up_interruptible(&g->wait);
 kref_put(&g->ref, drop);
 return 0;
}
static const struct of_device_id gp_match[] = { { .compatible = "embedded-contest,gp-control-probe-v1" }, {} };
MODULE_DEVICE_TABLE(of, gp_match);
static struct platform_driver gp_driver = { .probe = gp_probe, .remove = gp_remove,
 .driver = { .name = "bsp-gp", .of_match_table = gp_match } };
module_platform_driver(gp_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Minimal GP control probe; NOP/snapshot and level IRQ only");
