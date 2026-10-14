// SPDX-License-Identifier: GPL-2.0
/*
 * anlogic softip dma framework driver.
 *
 * Copyright (c) 2024 anlogic Technologies Co., Ltd.
 */

#include <linux/bitops.h>
#include <linux/dmapool.h>
#include <linux/init.h>
#include <linux/interrupt.h>
#include <linux/io.h>
#include <linux/iopoll.h>
#include <linux/module.h>
#include <linux/of_address.h>
#include <linux/of_dma.h>
#include <linux/of_platform.h>
#include <linux/of_irq.h>
#include <linux/slab.h>
#include <linux/clk.h>
#include <linux/io-64-nonatomic-lo-hi.h>

#include "dmaengine.h"

#include "include/linux/dma/anlogic_dma.h"
#include "../generated/dma_defs.h"
#include "../provider_api.h"

struct anlogic_axidma_tx_segment *anlogic_axidma_alloc_tx_segment(struct anlogic_dma_chan *chan)
{
	struct anlogic_axidma_tx_segment *segment = NULL;
	unsigned long flags;

	spin_lock_irqsave(&chan->lock, flags);
	if (!list_empty(&chan->free_seg_list)) {
		segment = list_first_entry(&chan->free_seg_list,
					   struct anlogic_axidma_tx_segment,
					   node);
		list_del(&segment->node);
	}
	spin_unlock_irqrestore(&chan->lock, flags);

	if (!segment)
		dev_dbg(chan->dev, "Could not find free tx segment\n");

	return segment;
}

static void anlogic_dma_clean_hw_desc(struct anlogic_axidma_desc_hw *hw)
{
	u32 next_desc = hw->next_desc;
	u32 next_desc_msb = hw->next_desc_msb;

	memset(hw, 0, sizeof(struct anlogic_axidma_desc_hw));

	hw->next_desc = next_desc;
	hw->next_desc_msb = next_desc_msb;
}

void anlogic_dma_free_tx_segment(struct anlogic_dma_chan *chan,
				struct anlogic_axidma_tx_segment *segment)
{
	anlogic_dma_clean_hw_desc(&segment->hw);

	list_add_tail(&segment->node, &chan->free_seg_list);
}

void anlogic_vdma_free_tx_segment(struct anlogic_dma_chan *chan,
					struct anlogic_vdma_tx_segment *segment)
{
	dma_pool_free(chan->desc_pool, segment, segment->phys);
}

struct anlogic_dma_tx_descriptor *anlogic_dma_alloc_tx_descriptor(struct anlogic_dma_chan *chan)
{
	struct anlogic_dma_tx_descriptor *desc;

	desc = kzalloc(sizeof(*desc), GFP_NOWAIT);
	if (!desc)
		return NULL;

	INIT_LIST_HEAD(&desc->segments);

	return desc;
}

static void anlogic_dma_chan_handle_cyclic(struct anlogic_dma_chan *chan,
					  struct anlogic_dma_tx_descriptor *desc,
					  unsigned long *flags)
{
	struct dmaengine_desc_callback cb;

	dmaengine_desc_get_callback(&desc->async_tx, &cb);
	if (dmaengine_desc_callback_valid(&cb)) {
		spin_unlock_irqrestore(&chan->lock, *flags);
		dmaengine_desc_callback_invoke(&cb, NULL);
		spin_lock_irqsave(&chan->lock, *flags);
	}
}

static void anlogic_dma_chan_desc_cleanup(struct anlogic_dma_chan *chan)
{
	struct anlogic_dma_tx_descriptor *desc, *next;
	struct anlogic_dma_device *al_dev = chan->al_dev;
	unsigned long flags;

	spin_lock_irqsave(&chan->lock, flags);

	list_for_each_entry_safe(desc, next, &chan->done_list, node) {
		struct dmaengine_result result;

		if (desc->cyclic) {
			anlogic_dma_chan_handle_cyclic(chan, desc, &flags);
			break;
		}

		/* Remove from the list of running transactions */
		list_del(&desc->node);

		if (unlikely(desc->err)) {
			if (chan->direction == DMA_DEV_TO_MEM)
				result.result = DMA_TRANS_READ_FAILED;
			else
				result.result = DMA_TRANS_WRITE_FAILED;
		} else {
			result.result = DMA_TRANS_NOERROR;
		}

		result.residue = desc->residue;

		/* Run the link descriptor callback function */
		spin_unlock_irqrestore(&chan->lock, flags);
		dmaengine_desc_get_callback_invoke(&desc->async_tx, &result);
		spin_lock_irqsave(&chan->lock, flags);

		/* Run any dependencies, then free the descriptor */
		dma_run_dependencies(&desc->async_tx);
		al_dev->desc_ops.dma_free_tx_descriptor(chan, desc);

		/*
		 * While we ran a callback the user called a terminate function,
		 * which takes care of cleaning up any remaining descriptors
		 */
		if (chan->terminating)
			break;
	}

	spin_unlock_irqrestore(&chan->lock, flags);
}

static void anlogic_dma_do_tasklet(struct tasklet_struct *t)
{
	struct anlogic_dma_chan *chan = from_tasklet(chan, t, tasklet);

	anlogic_dma_chan_desc_cleanup(chan);
}

int anlogic_dma_calc_copysize(struct anlogic_dma_chan *chan,
				    int size, int done)
{
	size_t copy;

	copy = min_t(size_t, size - done,
		     chan->al_dev->max_buffer_len);

	if ((copy + done < size) &&
	    chan->al_dev->common.copy_align) {
		/*
		 * If this is not the last descriptor, make sure
		 * the next one will be properly aligned
		 */
		copy = rounddown(copy,
				 (1 << chan->al_dev->common.copy_align));
	}
	return copy;
}

void anlogic_dma_start(struct anlogic_dma_chan *chan)
{
	int err;
	u32 val;

	dma_ctrl_set(chan, ANLOGIC_DMA_REG_DMACR, ANLOGIC_DMA_DMACR_RUNSTOP);

	/* Wait for the hardware to start */
	err = anlogic_dma_poll_timeout(chan, ANLOGIC_DMA_REG_DMASR, val,
				      !(val & ANLOGIC_DMA_DMASR_HALTED), 0,
				      ANLOGIC_DMA_LOOP_COUNT);

	if (err) {
		dev_err(chan->dev, "Cannot start channel %p: %x\n",
			chan, dma_ctrl_read(chan, ANLOGIC_DMA_REG_DMASR));

		chan->err = true;
	}
}

static int anlogic_dma_reset(struct anlogic_dma_chan *chan)
{
	int err;
	u32 tmp;

	dma_ctrl_set(chan, ANLOGIC_DMA_REG_DMACR, ANLOGIC_DMA_DMACR_RESET);

	/* Wait for the hardware to finish reset */
	err = anlogic_dma_poll_timeout(chan, ANLOGIC_DMA_REG_DMACR, tmp,
				      !(tmp & ANLOGIC_DMA_DMACR_RESET), 0,
				      ANLOGIC_DMA_LOOP_COUNT);

	if (err) {
		dev_err(chan->dev, "reset timeout, cr %x, sr %x\n",
			dma_ctrl_read(chan, ANLOGIC_DMA_REG_DMACR),
			dma_ctrl_read(chan, ANLOGIC_DMA_REG_DMASR));
		return -ETIMEDOUT;
	}

	chan->err = false;
	chan->idle = true;
	chan->desc_pendingcount = 0;
	chan->desc_submitcount = 0;

	return err;
}

int anlogic_dma_chan_reset(struct anlogic_dma_chan *chan)
{
	int err;

	/* Reset DMA */
	err = anlogic_dma_reset(chan);
	if (err)
		return err;

	/* Telemetry recovery rearms only after callback/tasklet/descriptor proof. */
	if (chan->telemetry) return 0;
	/* Enable interrupts */
	dma_ctrl_set(chan, ANLOGIC_DMA_REG_DMACR,
		      ANLOGIC_DMA_DMAXR_ALL_IRQ_MASK);

	return 0;
}

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

dma_cookie_t anlogic_dma_tx_submit(struct dma_async_tx_descriptor *tx)
{
	struct anlogic_dma_tx_descriptor *desc = to_dma_tx_descriptor(tx);
	struct anlogic_dma_chan *chan = to_anlogic_chan(tx->chan);
	struct anlogic_dma_device *al_dev = chan->al_dev;
	dma_cookie_t cookie;
	unsigned long flags;
	int err;

	if (chan->telemetry && (chan->telemetry_hold || !list_empty(&chan->pending_list) || !list_empty(&chan->active_list))) {
		al_dev->desc_ops.dma_free_tx_descriptor(chan,desc);return -EBUSY;
	}
	if (chan->cyclic) {
		al_dev->desc_ops.dma_free_tx_descriptor(chan, desc);
		return -EBUSY;
	}

	if (chan->err && (chan->telemetry || of_property_read_bool(chan->dev->of_node, "bsp,motion-exclusive-controller"))) {
		al_dev->desc_ops.dma_free_tx_descriptor(chan, desc);
		return -EIO;
	}

	if (chan->err) {
		/*
		 * If reset fails, need to hard reset the system.
		 * Channel is no longer functional
		 */
		err = anlogic_dma_chan_reset(chan);
		if (err < 0)
			return err;
	}

	spin_lock_irqsave(&chan->lock, flags);

	cookie = dma_cookie_assign(tx);

	/* Put this transaction onto the tail of the pending queue */
	al_dev->desc_ops.append_desc_queue(chan, desc);

	if (desc->cyclic)
		chan->cyclic = true;

	chan->terminating = false;

	spin_unlock_irqrestore(&chan->lock, flags);

	return cookie;
}

static void anlogic_dma_chan_remove(struct anlogic_dma_chan *chan)
{
	/* Disable all interrupts */
	dma_ctrl_clr(chan, ANLOGIC_DMA_REG_DMACR,
		      ANLOGIC_DMA_DMAXR_ALL_IRQ_MASK);

	if (chan->irq > 0)
		free_irq(chan->irq, chan);

	tasklet_kill(&chan->tasklet);

	list_del(&chan->common.device_node);
}

static int anlogic_dma_chan_probe(struct anlogic_dma_device *al_dev,
				  struct device_node *node)
{
	struct anlogic_dma_chan *chan;
	bool has_dre = false;
	u32 value, width;
	int err;

	/* Allocate and initialize the channel structure */
	chan = devm_kzalloc(al_dev->dev, sizeof(*chan), GFP_KERNEL);
	if (!chan)
		return -ENOMEM;

	chan->telemetry = of_property_read_bool(al_dev->dev->of_node,"bsp,telemetry-exclusive-controller");
	chan->dev = al_dev->dev;
	chan->al_dev = al_dev;
	chan->desc_pendingcount = 0x0;
	chan->ext_addr = al_dev->ext_addr;
	/* This variable ensures that descriptors are not
	 * Submitted when dma engine is in progress. This variable is
	 * Added to avoid polling for a bit in the status register to
	 * Know dma state in the driver hot path.
	 */
	chan->idle = true;

	spin_lock_init(&chan->lock);
	INIT_LIST_HEAD(&chan->pending_list);
	INIT_LIST_HEAD(&chan->done_list);
	INIT_LIST_HEAD(&chan->active_list);
	INIT_LIST_HEAD(&chan->free_seg_list);

	/* Retrieve the channel properties from the device tree */
	has_dre = of_property_read_bool(node, "anlogic,include-dre");

	chan->genlock = of_property_read_bool(node, "anlogic,genlock-mode");

	err = of_property_read_u32(node, "anlogic,datawidth", &value);
	if (err) {
		dev_err(al_dev->dev, "missing anlogic,datawidth property\n");
		return err;
	}
	width = value >> 3; /* Convert bits to bytes */

	/* If data width is greater than 8 bytes, DRE is not in hw */
	if (width > 8)
		has_dre = false;

	if (!has_dre)
		al_dev->common.copy_align = (enum dmaengine_alignment)fls(width - 1);

	if (of_device_is_compatible(node, "anlogic,axi-vdma-mm2s-channel") ||
		of_device_is_compatible(node, "anlogic,axi-dma-mm2s-channel")) {
		chan->direction = DMA_MEM_TO_DEV;
		chan->id = al_dev->mm2s_chan_id++;
		chan->tdest = chan->id;

		chan->ctrl_offset = ANLOGIC_DMA_MM2S_CTRL_OFFSET;

		if (al_dev->dma_config->dmatype == AL_DMA_TYPE_VDMA) {
			chan->desc_offset = ANLOGIC_VDMA_MM2S_DESC_OFFSET;
			chan->config.park = 1;

			if (al_dev->flush_on_fsync == ANLOGIC_DMA_FLUSH_BOTH ||
				al_dev->flush_on_fsync == ANLOGIC_DMA_FLUSH_MM2S)
				chan->flush_on_fsync = true;
		}

	} else if (of_device_is_compatible(node,
					   "anlogic,axi-vdma-s2mm-channel") ||
			of_device_is_compatible(node, "anlogic,axi-dma-s2mm-channel")) {
		chan->direction = DMA_DEV_TO_MEM;
		chan->id = al_dev->s2mm_chan_id++;
		chan->tdest = chan->id - al_dev->dma_config->max_channels / 2;
		chan->ctrl_offset = ANLOGIC_DMA_S2MM_CTRL_OFFSET;

		chan->has_vflip = of_property_read_bool(node,
					"anlogic,enable-vert-flip");
		if (chan->has_vflip) {
			chan->config.vflip_en = dma_read(chan,
				ANLOGIC_VDMA_REG_ENABLE_VERTICAL_FLIP) &
				ANLOGIC_VDMA_ENABLE_VERTICAL_FLIP;
		}

		if (al_dev->dma_config->dmatype == AL_DMA_TYPE_VDMA) {
			chan->desc_offset = ANLOGIC_VDMA_S2MM_DESC_OFFSET;
			chan->config.park = 1;

			if (al_dev->flush_on_fsync == ANLOGIC_DMA_FLUSH_BOTH ||
			    al_dev->flush_on_fsync == ANLOGIC_DMA_FLUSH_S2MM)
				chan->flush_on_fsync = true;
		}

	} else {
		dev_err(al_dev->dev, "Invalid channel compatible node\n");
		return -EINVAL;
	}

	if (chan->telemetry && (chan->direction != DMA_DEV_TO_MEM || width != 8 || !has_dre))
		return -EINVAL;
	/* Request the interrupt */
	chan->irq = of_irq_get(node, chan->tdest);

	if (chan->irq < 0)
		return dev_err_probe(al_dev->dev, chan->irq, "failed to get irq\n");
	err = request_irq(chan->irq, al_dev->dma_config->irq_handler,
			  IRQF_SHARED, "anlogic-dma-controller", chan);
	if (err) {
		dev_err(al_dev->dev, "unable to request IRQ %d\n", chan->irq);
		return err;
	}

	if (al_dev->dma_config->dmatype == AL_DMA_TYPE_AXIDMA) {
#ifdef CONFIG_AXI_DMA
		chan->start_transfer = axidma_init.start_transfer;
		chan->stop_transfer = axidma_init.stop_transfer;
#endif
	} else if (al_dev->dma_config->dmatype == AL_DMA_TYPE_VDMA) {
#ifdef CONFIG_AXI_VDMA
		chan->start_transfer = axivdma_init.start_transfer;
		chan->stop_transfer = axivdma_init.stop_transfer;
#endif
	}

	if (dma_ctrl_read(chan, ANLOGIC_DMA_REG_DMASR) & ANLOGIC_DMA_DMASR_SG_MASK) {
		chan->has_sg = true;
		printk(KERN_INFO "%s: ch %d: SG %s\n", dev_name(chan->dev), chan->id,
				chan->has_sg ? "enabled" : "disabled");
	}

	/* Initialize the tasklet */
	tasklet_setup(&chan->tasklet, anlogic_dma_do_tasklet);

	/*
	 * Initialize the DMA channel and add it to the DMA engine channels
	 * list.
	 */
	chan->common.device = &al_dev->common;

	list_add_tail(&chan->common.device_node, &al_dev->common.channels);
	al_dev->chan[chan->id] = chan;

	/* Reset the channel */
	err = anlogic_dma_chan_reset(chan);
	if (err < 0) {
		dev_err(al_dev->dev, "Reset channel failed\n");
		return err;
	}

	return 0;
}

static int anlogic_dma_child_probe(struct anlogic_dma_device *al_dev,
				    struct device_node *node)
{
	int ret, i;
	u32 nr_channels = 1;

	ret = of_property_read_u32(node, "dma-channels", &nr_channels);

	for (i = 0; i < nr_channels; i++) {
		ret = anlogic_dma_chan_probe(al_dev, node);
		if (ret)
			return ret;
	}

	return 0;
}

static struct dma_chan *of_dma_anlogic_xlate(struct of_phandle_args *dma_spec,
						struct of_dma *ofdma)
{
	struct anlogic_dma_device *al_dev = ofdma->of_dma_data;
	int chan_id = dma_spec->args[0];

	if (chan_id >= al_dev->dma_config->max_channels || !al_dev->chan[chan_id])
		return NULL;

	return dma_get_slave_channel(&al_dev->chan[chan_id]->common);
}

static const struct anlogic_dma_config axidma_config = {
	.dmatype = AL_DMA_TYPE_AXIDMA,
	.irq_handler = anlogic_dma_irq_handler,
	.max_channels = ANLOGIC_DMA_MAX_CHANS_PER_DEVICE,
};

#ifdef CONFIG_AXI_VDMA
static const struct anlogic_dma_config axivdma_config = {
	.dmatype = AL_DMA_TYPE_VDMA,
	.irq_handler = anlogic_dma_irq_handler,
	.max_channels = ANLOGIC_DMA_MAX_CHANS_PER_DEVICE,
};
#endif

static const struct of_device_id anlogic_dma_of_ids[] = {
#ifdef CONFIG_AXI_DMA
	{ .compatible = "anlogic,axi-dma", .data = &axidma_config },
#endif
#ifdef CONFIG_AXI_VDMA
	{ .compatible = "anlogic,axi-vdma", .data = &axivdma_config },
#endif
	{}
};
MODULE_DEVICE_TABLE(of, anlogic_dma_of_ids);

static int anlogic_dma_probe(struct platform_device *pdev)
{
	struct device_node *node = pdev->dev.of_node;
	struct anlogic_dma_device *al_dev;
	struct device_node *child, *np = pdev->dev.of_node;
	u32 num_frames = 0, addr_width = 32, len_width;
	int i, err;

	/* Allocate and initialize the DMA engine structure */
	al_dev = devm_kzalloc(&pdev->dev, sizeof(*al_dev), GFP_KERNEL);
	if (!al_dev)
		return -ENOMEM;

	al_dev->dev = &pdev->dev;
	if (np) {
		const struct of_device_id *match;

		match = of_match_node(anlogic_dma_of_ids, np);
		if (match && match->data)
			al_dev->dma_config = match->data;
	}

	/* This additional policy applies only to the independent loop profile. */
	if (of_property_read_bool(node, "bsp,motion-exclusive-controller")) {
		struct resource *r = platform_get_resource(pdev, IORESOURCE_MEM, 0);
		u32 aw, lw;
		if (!r || r->start != PLI_DMA_DMA_LOOPBACK_V1_BASE || resource_size(r) != PLI_DMA_DMA_LOOPBACK_V1_SIZE ||
		    of_property_read_u32(node, "anlogic,addrwidth", &aw) || aw != PLI_DMA_DMA_LOOPBACK_V1_MEMORY_ADDRESS_WIDTH ||
		    of_property_read_u32(node, "anlogic,sg-length-width", &lw) || lw != PLI_DMA_DMA_LOOPBACK_V1_AL_SG_LENGTH_WIDTH ||
		    of_property_read_bool(node, "anlogic,include-sg"))
			return -EINVAL;
	}

	if (of_property_read_bool(node, "bsp,telemetry-exclusive-controller")) {
        struct resource *r=platform_get_resource(pdev,IORESOURCE_MEM,0);
        u32 aw,lw;int children=0;
        if (!r || r->start!=RT_DMA_BASE || resource_size(r)!=RT_DMA_SIZE ||
            of_property_read_u32(node,"anlogic,addrwidth",&aw) || aw!=32 ||
            of_property_read_u32(node,"anlogic,sg-length-width",&lw) || lw!=16 ||
            of_property_read_bool(node,"anlogic,include-sg") ||
            of_property_read_bool(node,"bsp,motion-exclusive-controller")) return -EINVAL;
        for_each_child_of_node(node,child) {
            children++;
            if (!of_device_is_compatible(child,"anlogic,axi-dma-s2mm-channel")) {of_node_put(child);return -EINVAL;}
        }
        if(children!=1) return -EINVAL;
    }
	/* Request and map I/O memory */
	al_dev->regs = devm_platform_ioremap_resource(pdev, 0);
	if (IS_ERR(al_dev->regs)) {
		err = PTR_ERR(al_dev->regs);
		return err;
	}
	/* Retrieve the DMA engine properties from the device tree */
	al_dev->max_buffer_len = GENMASK(ANLOGIC_DMA_MAX_TRANS_LEN_MAX - 1, 0);
	al_dev->s2mm_chan_id = al_dev->dma_config->max_channels / 2;

	if (al_dev->dma_config->dmatype == AL_DMA_TYPE_AXIDMA) {
		if (!of_property_read_u32(node, "anlogic,sg-length-width",
					  &len_width)) {
			if (len_width < ANLOGIC_DMA_MAX_TRANS_LEN_MIN ||
			    len_width > ANLOGIC_DMA_V2_MAX_TRANS_LEN_MAX) {
				dev_warn(al_dev->dev,
					 "invalid anlogic,sg-length-width property value. Using default width\n");
			} else {
				if (len_width > ANLOGIC_DMA_MAX_TRANS_LEN_MAX)
					dev_warn(al_dev->dev,
						 "Please ensure that IP supports buffer length > 23 bits\n");
				al_dev->max_buffer_len =
					GENMASK(len_width - 1, 0);
			}
		}
	}

	if (al_dev->dma_config->dmatype == AL_DMA_TYPE_VDMA) {
		err = of_property_read_u32(node, "anlogic,num-fstores",
					   &num_frames);
		if (err < 0) {
			dev_err(al_dev->dev,
				"missing anlogic,num-fstores property\n");
			return err;
		}

		err = of_property_read_u32(node, "anlogic,flush-fsync",
					   &al_dev->flush_on_fsync);
		if (err < 0)
			dev_warn(al_dev->dev,
				 "missing anlogic,flush-fsync property\n");
	}

	err = of_property_read_u32(node, "anlogic,addrwidth", &addr_width);
	if (err < 0)
		dev_warn(al_dev->dev, "missing anlogic,addrwidth property\n");

	if (addr_width > 32)
		al_dev->ext_addr = true;
	else
		al_dev->ext_addr = false;

	/* Set the dma mask bits */
	err = dma_set_mask_and_coherent(al_dev->dev, DMA_BIT_MASK(addr_width));
	if (err < 0) {
		dev_err(al_dev->dev, "DMA mask error %d\n", err);
		return err;
	}

	if (al_dev->dma_config->dmatype == AL_DMA_TYPE_AXIDMA) {
#ifdef CONFIG_AXI_DMA
		al_dev->common = axidma_init.dma_ops;
		al_dev->desc_ops = axidma_init.desc_ops;
		dma_cap_set(DMA_SLAVE, al_dev->common.cap_mask);
		dma_cap_set(DMA_PRIVATE, al_dev->common.cap_mask);
		dma_cap_set(DMA_CYCLIC, al_dev->common.cap_mask);
		dev_info(&pdev->dev, "Anlogic AXI DMA Engine Driver Probed\n");
#endif
	} else if (al_dev->dma_config->dmatype == AL_DMA_TYPE_VDMA) {
#ifdef CONFIG_AXI_VDMA
		al_dev->common = axivdma_init.dma_ops;
		al_dev->desc_ops = axivdma_init.desc_ops;
		dma_cap_set(DMA_SLAVE, al_dev->common.cap_mask);
		dma_cap_set(DMA_PRIVATE, al_dev->common.cap_mask);
		dev_info(&pdev->dev, "Anlogic AXI VDMA Engine Driver Probed\n");
#endif
	}

	/* Initialize the DMA engine */
	al_dev->common.dev = &pdev->dev;
	INIT_LIST_HEAD(&al_dev->common.channels);

	platform_set_drvdata(pdev, al_dev);

	/* Initialize the channels */
	for_each_child_of_node(node, child) {
		err = anlogic_dma_child_probe(al_dev, child);
		if (err < 0) {
			of_node_put(child);
			goto error;
		}
	}

	if (al_dev->dma_config->dmatype == AL_DMA_TYPE_AXIDMA) {
		for (i = 0; i < al_dev->dma_config->max_channels; i++)
			if (al_dev->chan[i])
				al_dev->chan[i]->num_frms = num_frames;
	}

	/* Register the DMA engine with the core */
	err = dma_async_device_register(&al_dev->common);
	if (err) {
		dev_err(al_dev->dev, "failed to register the dma device\n");
		goto error;
	}

	err = of_dma_controller_register(node, of_dma_anlogic_xlate,
					 al_dev);
	if (err < 0) {
		dev_err(&pdev->dev, "Unable to register DMA to DT\n");
		dma_async_device_unregister(&al_dev->common);
		goto error;
	}

	return 0;

error:
	for (i = 0; i < al_dev->dma_config->max_channels; i++)
		if (al_dev->chan[i])
			anlogic_dma_chan_remove(al_dev->chan[i]);

	return err;
}

static int anlogic_dma_remove(struct platform_device *pdev)
{
	struct anlogic_dma_device *al_dev = platform_get_drvdata(pdev);
	int i;

	of_dma_controller_free(pdev->dev.of_node);

	dma_async_device_unregister(&al_dev->common);

	for (i = 0; i < al_dev->dma_config->max_channels; i++)
		if (al_dev->chan[i])
			anlogic_dma_chan_remove(al_dev->chan[i]);

	return 0;
}

static struct platform_driver anlogic_dma_driver = {
	.driver = {
		.name = "anlogic-dma",
		.of_match_table = anlogic_dma_of_ids,
		.suppress_bind_attrs = true,
	},
	.probe = anlogic_dma_probe,
	.remove = anlogic_dma_remove,
};

module_platform_driver(anlogic_dma_driver);

MODULE_AUTHOR("anlogic, Inc.");
MODULE_DESCRIPTION("anlogic dma driver");
MODULE_LICENSE("GPL");
