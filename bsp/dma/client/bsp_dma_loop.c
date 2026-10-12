// SPDX-License-Identifier: GPL-2.0
/* Independent simple AXI DMA loop test: fixed kernel buffers, no raw addresses. */
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/of.h>
#include <linux/dmaengine.h>
#include <linux/dma-mapping.h>
#include <linux/completion.h>
#include <linux/miscdevice.h>
#include <linux/fs.h>
#include <linux/uaccess.h>
#include <linux/capability.h>
#include <linux/mutex.h>
#include <linux/delay.h>
#include <linux/ktime.h>
#include "../dma_uapi.h"
#include "../bsp_dma_pair.h"
#include "../generated/dma_defs.h"

#define MAX_LEN PLI_DMA_DMA_LOOPBACK_V1_MAXIMUM_TRANSFER_BYTES
#define GUARD 64U
#define ALLOC_SIZE (MAX_LEN + 2 * GUARD)
struct loop;
struct callback {
    struct loop *loop;
    struct completion done;
    u32 generation, count;
    u64 when;
    enum dmaengine_tx_result result;
};
struct loop {
    struct device *dev, *dma_dev;
    struct dma_chan *tx, *rx;
    struct miscdevice misc;
    struct mutex lock;
    void *source, *dest;
    dma_addr_t source_dma, dest_dma;
    struct callback tx_cb, rx_cb;
    u32 generation, errors, timeouts, recoveries;
    bool quarantined;
};
static void done(void *arg, const struct dmaengine_result *result)
{
    struct callback *cb = arg;
    cb->count++;
    if (cb->generation != READ_ONCE(cb->loop->generation))
        return;
    cb->when = ktime_get_ns();
    cb->result = result ? result->result : DMA_TRANS_NOERROR;
    complete(&cb->done);
}
static int recover(struct loop *l)
{
    int a, b, c;
    /* Mutex excludes all new submissions. Buffers remain allocated while both
     * channels halt/reset and IRQ/tasklets drain. No common PL/GP reset. */
    a = dmaengine_terminate_sync(l->rx);
    b = dmaengine_terminate_sync(l->tx);
    c = bsp_anlogic_loop_quiescent(l->tx, l->rx);
    if (a || b || c) {
        if (!l->quarantined) {
            l->quarantined = true;
            __module_get(THIS_MODULE); /* Retain buffers/module until cold reset. */
        }
        l->errors++;
        dev_err(l->dev, "pair stop failed rx=%d tx=%d post=%d; buffers retained, no reuse/unload\n", a,b,c);
        return -EIO;
    }
    l->generation++;
    l->recoveries++;
    return 0;
}
static u8 pattern_byte(u32 i, u32 pattern)
{
    switch (pattern) {
    case 0: return i;
    case 1: return 0xa5;
    case 2: return i * 37U + 19U;
    default: return ~(i * 13U + 7U);
    }
}
static dma_cookie_t submit(struct loop *l, bool tx, u32 length)
{
    struct callback *cb = tx ? &l->tx_cb : &l->rx_cb;
    struct dma_async_tx_descriptor *desc;
    struct dma_chan *chan = tx ? l->tx : l->rx;
    dma_addr_t addr = (tx ? l->source_dma : l->dest_dma) + GUARD;
    reinit_completion(&cb->done);
    cb->generation = l->generation;
    cb->when = 0;
    cb->result = DMA_TRANS_ABORTED;
    desc = dmaengine_prep_slave_single(chan, addr, length,
            tx ? DMA_MEM_TO_DEV : DMA_DEV_TO_MEM, DMA_PREP_INTERRUPT | DMA_CTRL_ACK);
    if (!desc)
        return -EINVAL;
    desc->callback_result = done;
    desc->callback_param = cb;
    return dmaengine_submit(desc);
}
static int run(struct loop *l, struct bsp_dma_test *t)
{
    dma_cookie_t tx_cookie = 0, rx_cookie = 0;
    u64 start = ktime_get_ns(), submitted;
    u32 i, tx_before = l->tx_cb.count, rx_before = l->rx_cb.count;
    bool expected_timeout = t->scenario != 0;
    int ret = 0;
    if (l->quarantined)
        return -EIO;
    memset(l->source, 0x6b, ALLOC_SIZE);
    memset(l->dest, 0x5a, ALLOC_SIZE);
    for (i = 0; i < t->length; i++)
        ((u8 *)l->source)[GUARD+i] = pattern_byte(i, t->pattern);
    dma_wmb();
    submitted = ktime_get_ns();
    /* 0: equal-length loop; 1: armed receive timeout; 2/3: TX without RX,
     * exercising FIFO backpressure and cancellation of a pending packet. */
    if (t->scenario < 2) {
        rx_cookie = submit(l, false, t->length);
        if (dma_submit_error(rx_cookie)) { ret = rx_cookie; goto stop; }
        dma_async_issue_pending(l->rx);
    }
    if (t->scenario != 1) {
        tx_cookie = submit(l, true, t->length);
        if (dma_submit_error(tx_cookie)) { ret = tx_cookie; goto stop; }
        dma_async_issue_pending(l->tx);
    }
    t->submit_ns = ktime_get_ns() - submitted;
    if (expected_timeout) {
        msleep(t->scenario == 3 ? 1 : t->timeout_ms);
        /* Cancellation may occur after MM2S read completion. Packet still
         * has no S2MM consumer; pair reset must drop all stream remnants. */
        if (t->scenario != 3)
            l->timeouts++;
    } else {
        if (!wait_for_completion_timeout(&l->rx_cb.done, msecs_to_jiffies(t->timeout_ms)) ||
            !wait_for_completion_timeout(&l->tx_cb.done, msecs_to_jiffies(t->timeout_ms))) {
            l->timeouts++; ret = -ETIMEDOUT; goto stop;
        }
        if (l->tx_cb.result != DMA_TRANS_NOERROR || l->rx_cb.result != DMA_TRANS_NOERROR ||
            dma_async_is_tx_complete(l->tx,tx_cookie,NULL,NULL) != DMA_COMPLETE ||
            dma_async_is_tx_complete(l->rx,rx_cookie,NULL,NULL) != DMA_COMPLETE) {
            ret = -EIO; goto stop;
        }
        dma_rmb();
        for (i=0; i<t->length; i++) {
            if (((u8 *)l->dest)[GUARD+i] != ((u8 *)l->source)[GUARD+i]) {
                t->mismatch_offset=i; ret=-EILSEQ; break;
            }
        }
    }
stop:
    t->before_tx_status=tx_cookie>0 ? dma_async_is_tx_complete(l->tx,tx_cookie,NULL,NULL) : ~0U;
    t->before_rx_status=rx_cookie>0 ? dma_async_is_tx_complete(l->rx,rx_cookie,NULL,NULL) : ~0U;
    t->inflight_observed=expected_timeout &&
        ((tx_cookie>0 && !completion_done(&l->tx_cb.done)) || (rx_cookie>0 && !completion_done(&l->rx_cb.done)));
    if (recover(l))
        ret = -EIO;
    t->quiescent=!l->quarantined;
    if (!l->quarantined) {
        /* HALTED + synchronized callbacks owns both buffers again. Check
         * guards and stability after a delay before any future reuse/free. */
        dma_rmb();
        for (i=0; i<ALLOC_SIZE; i++) {
            if ((i < GUARD || i >= GUARD+t->length) && ((u8 *)l->dest)[i] != 0x5a)
                ret = -EOVERFLOW;
            if (expected_timeout && ((u8 *)l->dest)[i] != 0x5a)
                ret = -EOVERFLOW;
        }
        msleep(10);
        dma_rmb();
        for (i=0; i<ALLOC_SIZE; i++) {
            u8 expected = (i >= GUARD && i < GUARD+t->length && !expected_timeout) ?
                          pattern_byte(i-GUARD,t->pattern) : 0x5a;
            if (((u8 *)l->dest)[i] != expected)
                ret = -EILSEQ;
        }
    }
    if (ret)
        l->errors++;
    t->result = ret ? -ret : 0;
    t->tx_callbacks = l->tx_cb.count-tx_before;
    t->rx_callbacks = l->rx_cb.count-rx_before;
    t->tx_complete_ns = l->tx_cb.when > submitted ? l->tx_cb.when-submitted : 0;
    t->rx_complete_ns = l->rx_cb.when > submitted ? l->rx_cb.when-submitted : 0;
    t->total_ns = ktime_get_ns()-start;
    t->errors=l->errors; t->timeouts=l->timeouts; t->recoveries=l->recoveries;
    t->generation=l->generation;
    return 0; /* Return detailed transfer result through ordinary copied data. */
}
static long control(struct file *f, unsigned int cmd, unsigned long arg)
{
    struct loop *l = container_of(f->private_data,struct loop,misc);
    struct bsp_dma_test t;
    int ret;
    if (!capable(CAP_SYS_RAWIO)) return -EPERM;
    if (cmd != BSP_DMA_TEST) return -ENOTTY;
    if (copy_from_user(&t,(void __user *)arg,sizeof(t))) return -EFAULT;
    if (!t.length || t.length>MAX_LEN || t.pattern>3 || t.scenario>3 ||
        t.timeout_ms<10 || t.timeout_ms>2000 || (t.scenario>=2 && t.length<4096))
        return -EINVAL;
    t.result=0; t.mismatch_offset=~0U;
    mutex_lock(&l->lock);
    ret=run(l,&t);
    mutex_unlock(&l->lock);
    if (ret) return ret;
    return copy_to_user((void __user *)arg,&t,sizeof(t)) ? -EFAULT : 0;
}
static const struct file_operations ops={.owner=THIS_MODULE,.unlocked_ioctl=control,.llseek=no_llseek};
static int probe(struct platform_device *p)
{
    struct loop *l;
    int ret;
    l=kzalloc(sizeof(*l),GFP_KERNEL);
    if (!l) return -ENOMEM;
    l->dev=&p->dev; mutex_init(&l->lock);
    l->tx=dma_request_chan(&p->dev,"tx");
    if (IS_ERR(l->tx)) { ret=PTR_ERR(l->tx); goto free; }
    l->rx=dma_request_chan(&p->dev,"rx");
    if (IS_ERR(l->rx)) { ret=PTR_ERR(l->rx); goto release_tx; }
    l->dma_dev=dmaengine_get_dma_device(l->tx);
    if (l->dma_dev != dmaengine_get_dma_device(l->rx)) { ret=-EINVAL; goto release; }
    if (dma_get_mask(l->dma_dev) != DMA_BIT_MASK(32)) { ret=-EINVAL; goto release; }
    l->source=dma_alloc_coherent(l->dma_dev,ALLOC_SIZE,&l->source_dma,GFP_KERNEL);
    l->dest=dma_alloc_coherent(l->dma_dev,ALLOC_SIZE,&l->dest_dma,GFP_KERNEL);
    if (!l->source || !l->dest) { ret=-ENOMEM; goto buffers; }
    if ((l->source_dma & 7) || (l->dest_dma & 7) ||
        upper_32_bits(l->source_dma+ALLOC_SIZE-1) || upper_32_bits(l->dest_dma+ALLOC_SIZE-1)) {
        ret=-ERANGE; goto buffers;
    }
    l->tx_cb.loop=l; l->rx_cb.loop=l;
    init_completion(&l->tx_cb.done); init_completion(&l->rx_cb.done);
    ret=bsp_anlogic_loop_quiescent(l->tx,l->rx);
    if (ret) goto buffers; /* No transfer has been submitted in probe. */
    l->misc=(struct miscdevice){.minor=MISC_DYNAMIC_MINOR,.name="bsp-dma-loop",.fops=&ops,.mode=0600,.parent=&p->dev};
    ret=misc_register(&l->misc);
    if (ret) goto buffers;
    platform_set_drvdata(p,l);
    dev_info(&p->dev,"coherent loop buffers allocated via provider DMA API; mask32, simple; no user addresses\n");
    return 0;
buffers:
    if (l->source) dma_free_coherent(l->dma_dev,ALLOC_SIZE,l->source,l->source_dma);
    if (l->dest) dma_free_coherent(l->dma_dev,ALLOC_SIZE,l->dest,l->dest_dma);
release: dma_release_channel(l->rx);
release_tx: dma_release_channel(l->tx);
free: kfree(l); return ret;
}
static int remove_loop(struct platform_device *p)
{
    struct loop *l=platform_get_drvdata(p);
    misc_deregister(&l->misc);
    mutex_lock(&l->lock);
    if (recover(l)) { mutex_unlock(&l->lock); return -EBUSY; }
    dma_free_coherent(l->dma_dev,ALLOC_SIZE,l->source,l->source_dma);
    dma_free_coherent(l->dma_dev,ALLOC_SIZE,l->dest,l->dest_dma);
    dma_release_channel(l->rx); dma_release_channel(l->tx);
    mutex_unlock(&l->lock); kfree(l); return 0;
}
static const struct of_device_id ids[]={{.compatible="bsp,dma-loopback-test-v1"},{}};
MODULE_DEVICE_TABLE(of,ids);
static struct platform_driver bsp_loop_driver={.probe=probe,.remove=remove_loop,.driver={.name="bsp-dma-loop",.of_match_table=ids,.suppress_bind_attrs=true}};
module_platform_driver(bsp_loop_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Restricted coherent Anlogic simple DMA loop acceptance");
