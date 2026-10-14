// SPDX-License-Identifier: GPL-2.0
/*
 * anlogic axi dma Controller Driver
 *
 * Copyright (c) 2024 anlogic Technologies Co., Ltd.
 */

#include <linux/bitops.h>
#include <linux/dmapool.h>
#include <linux/init.h>
#include <linux/interrupt.h>
#include <linux/io.h>
#include <linux/iopoll.h>
#include <linux/delay.h>
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
#include "../provider_api.h"

static void anlogic_axidma_free_tx_descriptor(struct anlogic_dma_chan *chan,
			       struct anlogic_dma_tx_descriptor *desc)
{
	struct anlogic_axidma_tx_segment *axidma_segment, *axidma_next;

	if (!desc)
		return;

	list_for_each_entry_safe(axidma_segment, axidma_next,
				 &desc->segments, node) {
		list_del(&axidma_segment->node);
		anlogic_dma_free_tx_segment(chan, axidma_segment);
	}

	kfree(desc);
}

static void anlogic_axidma_free_desc_list(struct anlogic_dma_chan *chan,
					struct list_head *list)
{
	struct anlogic_dma_tx_descriptor *desc, *next;

	list_for_each_entry_safe(desc, next, list, node) {
		list_del(&desc->node);
		anlogic_axidma_free_tx_descriptor(chan, desc);
	}
}

static void anlogic_axidma_free_descriptors(struct anlogic_dma_chan *chan)
{
	unsigned long flags;

	spin_lock_irqsave(&chan->lock, flags);

	anlogic_axidma_free_desc_list(chan, &chan->pending_list);
	anlogic_axidma_free_desc_list(chan, &chan->done_list);
	anlogic_axidma_free_desc_list(chan, &chan->active_list);

	spin_unlock_irqrestore(&chan->lock, flags);
}

static void anlogic_axidma_free_chan_resources(struct dma_chan *dchan)
{
	struct anlogic_dma_chan *chan = to_anlogic_chan(dchan);
	unsigned long flags;

	dev_dbg(chan->dev, "Free all channel resources.\n");

	anlogic_axidma_free_descriptors(chan);

	if (chan->al_dev->dma_config->dmatype == AL_DMA_TYPE_AXIDMA) {
		spin_lock_irqsave(&chan->lock, flags);
		INIT_LIST_HEAD(&chan->free_seg_list);
		spin_unlock_irqrestore(&chan->lock, flags);

		/* Free memory that is allocated for BD */
		dma_free_coherent(chan->dev, sizeof(*chan->seg_v) *
				  ANLOGIC_DMA_NUM_DESCS, chan->seg_v,
				  chan->seg_p);

		/* Free Memory that is allocated for cyclic DMA Mode */
		dma_free_coherent(chan->dev, sizeof(*chan->cyclic_seg_v),
				  chan->cyclic_seg_v, chan->cyclic_seg_p);
	}

}

static int anlogic_axidma_alloc_chan_resources(struct dma_chan *dchan)
{
	struct anlogic_dma_chan *chan = to_anlogic_chan(dchan);
	int i;

	/* Has this channel already been allocated? */
	if (chan->desc_pool)
		return 0;

	/* Allocate the buffer descriptors. */
	chan->seg_v = dma_alloc_coherent(chan->dev,
					 sizeof(*chan->seg_v) * ANLOGIC_DMA_NUM_DESCS,
					 &chan->seg_p, GFP_KERNEL);
	if (!chan->seg_v) {
		dev_err(chan->dev,
			"unable to allocate channel %d descriptors\n",
			chan->id);
		return -ENOMEM;
	}
	/*
	 * For cyclic DMA mode we need to program the tail Descriptor
	 * register with a value which is not a part of the BD chain
	 * so allocating a desc segment during channel allocation for
	 * programming tail descriptor.
	 */
	chan->cyclic_seg_v = dma_alloc_coherent(chan->dev,
						sizeof(*chan->cyclic_seg_v),
						&chan->cyclic_seg_p,
						GFP_KERNEL);
	if (!chan->cyclic_seg_v) {
		dev_err(chan->dev,
			"unable to allocate desc segment for cyclic DMA\n");
		dma_free_coherent(chan->dev, sizeof(*chan->seg_v) *
			ANLOGIC_DMA_NUM_DESCS, chan->seg_v,
			chan->seg_p);
		return -ENOMEM;
	}
	chan->cyclic_seg_v->phys = chan->cyclic_seg_p;

	for (i = 0; i < ANLOGIC_DMA_NUM_DESCS; i++) {
		chan->seg_v[i].hw.next_desc =
		lower_32_bits(chan->seg_p + sizeof(*chan->seg_v) *
			((i + 1) % ANLOGIC_DMA_NUM_DESCS));
		chan->seg_v[i].hw.next_desc_msb =
		upper_32_bits(chan->seg_p + sizeof(*chan->seg_v) *
			((i + 1) % ANLOGIC_DMA_NUM_DESCS));
		chan->seg_v[i].phys = chan->seg_p +
			sizeof(*chan->seg_v) * i;
		list_add_tail(&chan->seg_v[i].node,
			      &chan->free_seg_list);
	}

	dma_cookie_init(dchan);

	/* For AXI DMA resetting once channel will reset the
	 * other channel as well so enable the interrupts here.
	 */
	dma_ctrl_set(chan, ANLOGIC_DMA_REG_DMACR,
		      ANLOGIC_DMA_DMAXR_ALL_IRQ_MASK);

	return 0;
}

static int anlogic_axidma_terminate_all(struct dma_chan *dchan)
{
	struct anlogic_dma_chan *chan = to_anlogic_chan(dchan);
	u32 reg;
	int err;

	if (!chan->telemetry && !of_property_read_bool(chan->dev->of_node, "bsp,motion-exclusive-controller") &&
	    !chan->cyclic) {
		err = chan->stop_transfer(chan);
		if (err) {
			dev_err(chan->dev, "Cannot stop channel %p: %x\n",
				chan, dma_ctrl_read(chan,
				ANLOGIC_DMA_REG_DMASR));
			chan->err = true;
			return err; /* Do not free descriptors on an unconfirmed halt. */
		}
	}

	err = anlogic_dma_chan_reset(chan);
	if (err)
		return err;
	if (of_property_read_bool(chan->dev->of_node, "bsp,motion-exclusive-controller")) {
		int i;
		u32 sr, cr;
		for (i = 0; i < 2; i++) {
			struct anlogic_dma_chan *peer = chan->al_dev->chan[i];
			if (!peer || peer->has_sg)
				return -EINVAL;
			err = anlogic_dma_poll_timeout(peer, ANLOGIC_DMA_REG_DMASR, sr,
						      sr & ANLOGIC_DMA_DMASR_HALTED, 0,
						      ANLOGIC_DMA_LOOP_COUNT);
			cr = dma_ctrl_read(peer, ANLOGIC_DMA_REG_DMACR);
			if (err || (cr & (ANLOGIC_DMA_DMACR_RUNSTOP | ANLOGIC_DMA_DMACR_RESET)))
				return err ? err : -EBUSY;
		}
	}
    if (chan->telemetry) {
        u32 sr,cr;
        err=anlogic_dma_poll_timeout(chan,ANLOGIC_DMA_REG_DMASR,sr,sr & ANLOGIC_DMA_DMASR_HALTED,0,ANLOGIC_DMA_LOOP_COUNT);
        cr=dma_ctrl_read(chan,ANLOGIC_DMA_REG_DMACR);
        if(err || (cr & (ANLOGIC_DMA_DMACR_RUNSTOP|ANLOGIC_DMA_DMACR_RESET))) return err?err:-EBUSY;
        dma_ctrl_clr(chan,ANLOGIC_DMA_REG_DMACR,ANLOGIC_DMA_DMAXR_ALL_IRQ_MASK);
        synchronize_irq(chan->irq);tasklet_kill(&chan->tasklet);
    }
	/* Remove and free all of the descriptors in the lists */
	chan->terminating = true;
	anlogic_axidma_free_descriptors(chan);
	chan->idle = true;

	if (chan->cyclic) {
		reg = dma_ctrl_read(chan, ANLOGIC_DMA_REG_DMACR);
		reg &= ~ANLOGIC_DMA_CR_CYCLIC_BD_EN_MASK;
		dma_ctrl_write(chan, ANLOGIC_DMA_REG_DMACR, reg);
		chan->cyclic = false;
	}

	return 0;
}

static void anlogic_axidma_synchronize(struct dma_chan *dchan)
{
	struct anlogic_dma_chan *chan = to_anlogic_chan(dchan);

	synchronize_irq(chan->irq);
	tasklet_kill(&chan->tasklet);
}

static u32 anlogic_axidma_get_residue(struct anlogic_dma_chan *chan,
				  struct anlogic_dma_tx_descriptor *desc)
{
	struct anlogic_axidma_tx_segment *axidma_seg;
	struct anlogic_axidma_desc_hw *axidma_hw;
	struct list_head *entry;
	u32 residue = 0;

	list_for_each(entry, &desc->segments) {
		axidma_seg = list_entry(entry,
					struct anlogic_axidma_tx_segment,
					node);
		axidma_hw = &axidma_seg->hw;
		residue += (axidma_hw->control - axidma_hw->status) &
			   chan->al_dev->max_buffer_len;

	}

	return residue;
}

static enum dma_status anlogic_axidma_tx_status(struct dma_chan *dchan,
					dma_cookie_t cookie,
					struct dma_tx_state *txstate)
{
	struct anlogic_dma_chan *chan = to_anlogic_chan(dchan);
	struct anlogic_dma_tx_descriptor *desc;
	enum dma_status ret;
	unsigned long flags;
	u32 residue = 0;

	if (READ_ONCE(chan->err))
		return DMA_ERROR;
	ret = dma_cookie_status(dchan, cookie, txstate);
	if (ret == DMA_COMPLETE || !txstate)
		return ret;

	spin_lock_irqsave(&chan->lock, flags);
	if (!list_empty(&chan->active_list)) {
		desc = list_last_entry(&chan->active_list,
				       struct anlogic_dma_tx_descriptor, node);
		if (chan->has_sg)
			residue = anlogic_axidma_get_residue(chan, desc);
	}
	spin_unlock_irqrestore(&chan->lock, flags);

	dma_set_residue(txstate, residue);

	return ret;
}

static void anlogic_axidma_issue_pending(struct dma_chan *dchan)
{
	struct anlogic_dma_chan *chan = to_anlogic_chan(dchan);
	unsigned long flags;

	spin_lock_irqsave(&chan->lock, flags);
	chan->start_transfer(chan);
	spin_unlock_irqrestore(&chan->lock, flags);
}

static int anlogic_axidma_device_config(struct dma_chan *dchan,
				    struct dma_slave_config *config)
{
	return 0;
}

static struct dma_async_tx_descriptor *anlogic_axidma_prep_slave_sg(
	struct dma_chan *dchan, struct scatterlist *sgl, unsigned int sg_len,
	enum dma_transfer_direction direction, unsigned long flags,
	void *context)
{
	struct anlogic_dma_chan *chan = to_anlogic_chan(dchan);
	struct anlogic_dma_tx_descriptor *desc;
	struct anlogic_axidma_tx_segment *segment = NULL;
	u32 *app_w = (u32 *)context;
	struct scatterlist *sg;
	size_t copy;
	size_t sg_used;
	unsigned int i;

	if (!is_slave_direction(direction))
		return NULL;
	if (!chan->has_sg && (direction != chan->direction || sg_len != 1 ||
	    !sg_dma_len(sgl) || sg_dma_len(sgl) > chan->al_dev->max_buffer_len ||
	    (sg_dma_address(sgl) & 7)))
		return NULL;

	/* Allocate a transaction descriptor. */
	desc = anlogic_dma_alloc_tx_descriptor(chan);
	if (!desc)
		return NULL;

	dma_async_tx_descriptor_init(&desc->async_tx, &chan->common);
	desc->async_tx.tx_submit = anlogic_dma_tx_submit;

	/* Build transactions using information in the scatter gather list */
	for_each_sg(sgl, sg, sg_len, i) {
		sg_used = 0;

		/* Loop until the entire scatterlist entry is used */
		while (sg_used < sg_dma_len(sg)) {
			struct anlogic_axidma_desc_hw *hw;

			/* Get a free segment */
			segment = anlogic_axidma_alloc_tx_segment(chan);
			if (!segment)
				goto error;

			/*
			 * Calculate the maximum number of bytes to transfer,
			 * making sure it is less than the hw limit
			 */
			copy = anlogic_dma_calc_copysize(chan, sg_dma_len(sg),
							sg_used);
			hw = &segment->hw;

			/* Fill in the descriptor */
			anlogic_axidma_buf(chan, hw, sg_dma_address(sg),
					  sg_used, 0);

			hw->control = copy;

			if (chan->direction == DMA_MEM_TO_DEV) {
				if (app_w)
					memcpy(hw->app, app_w, sizeof(u32) *
					       ANLOGIC_DMA_NUM_APP_WORDS);
			}

			sg_used += copy;

			/*
			 * Insert the segment into the descriptor segments
			 * list.
			 */
			list_add_tail(&segment->node, &desc->segments);
		}
	}

	segment = list_first_entry(&desc->segments,
				   struct anlogic_axidma_tx_segment, node);
	desc->async_tx.phys = segment->phys;

	/* For the last DMA_MEM_TO_DEV transfer, set EOP */
	if (chan->direction == DMA_MEM_TO_DEV) {
		segment->hw.control |= ANLOGIC_DMA_BD_SOP;
		segment = list_last_entry(&desc->segments,
					  struct anlogic_axidma_tx_segment,
					  node);
		segment->hw.control |= ANLOGIC_DMA_BD_EOP;
	}

	return &desc->async_tx;

error:
	anlogic_axidma_free_tx_descriptor(chan, desc);
	return NULL;
}

static struct dma_async_tx_descriptor *anlogic_axidma_prep_dma_cyclic(
	struct dma_chan *dchan, dma_addr_t buf_addr, size_t buf_len,
	size_t period_len, enum dma_transfer_direction direction,
	unsigned long flags)
{
	struct anlogic_dma_chan *chan = to_anlogic_chan(dchan);
	struct anlogic_dma_tx_descriptor *desc;
	struct anlogic_axidma_tx_segment *segment, *head_segment, *prev = NULL;
	size_t copy, sg_used;
	unsigned int num_periods;
	int i;
	u32 reg;

	if (!period_len)
		return NULL;

	num_periods = buf_len / period_len;

	if (!num_periods)
		return NULL;

	if (!is_slave_direction(direction))
		return NULL;

	/* Allocate a transaction descriptor. */
	desc = anlogic_dma_alloc_tx_descriptor(chan);
	if (!desc)
		return NULL;

	chan->direction = direction;
	dma_async_tx_descriptor_init(&desc->async_tx, &chan->common);
	desc->async_tx.tx_submit = anlogic_dma_tx_submit;

	for (i = 0; i < num_periods; ++i) {
		sg_used = 0;

		while (sg_used < period_len) {
			struct anlogic_axidma_desc_hw *hw;

			/* Get a free segment */
			segment = anlogic_axidma_alloc_tx_segment(chan);
			if (!segment)
				goto error;

			/*
			 * Calculate the maximum number of bytes to transfer,
			 * making sure it is less than the hw limit
			 */
			copy = anlogic_dma_calc_copysize(chan, period_len,
							sg_used);
			hw = &segment->hw;
			anlogic_axidma_buf(chan, hw, buf_addr, sg_used,
					  period_len * i);
			hw->control = copy;

			if (prev)
				prev->hw.next_desc = segment->phys;

			prev = segment;
			sg_used += copy;

			/*
			 * Insert the segment into the descriptor segments
			 * list.
			 */
			list_add_tail(&segment->node, &desc->segments);
		}
	}

	head_segment = list_first_entry(&desc->segments,
				   struct anlogic_axidma_tx_segment, node);
	desc->async_tx.phys = head_segment->phys;

	desc->cyclic = true;
	reg = dma_ctrl_read(chan, ANLOGIC_DMA_REG_DMACR);
	reg |= ANLOGIC_DMA_CR_CYCLIC_BD_EN_MASK;
	dma_ctrl_write(chan, ANLOGIC_DMA_REG_DMACR, reg);

	segment = list_last_entry(&desc->segments,
				  struct anlogic_axidma_tx_segment,
				  node);
	segment->hw.next_desc = (u32) head_segment->phys;

	/* For the last DMA_MEM_TO_DEV transfer, set EOP */
	if (direction == DMA_MEM_TO_DEV) {
		head_segment->hw.control |= ANLOGIC_DMA_BD_SOP;
		segment->hw.control |= ANLOGIC_DMA_BD_EOP;
	}

	return &desc->async_tx;

error:
	anlogic_axidma_free_tx_descriptor(chan, desc);
	return NULL;
}

/**
 * anlogic_axidma_start_transfer - Starts DMA transfer
 * @chan: Driver specific channel struct pointer
 */
static void anlogic_axidma_start_transfer(struct anlogic_dma_chan *chan)
{
	struct anlogic_dma_tx_descriptor *head_desc, *tail_desc;
	struct anlogic_axidma_tx_segment *tail_segment;
	u32 reg;

	if (chan->err || (chan->telemetry && chan->telemetry_hold))
		return;

	if (list_empty(&chan->pending_list))
		return;

	if (!chan->idle)
		return;

	head_desc = list_first_entry(&chan->pending_list,
				     struct anlogic_dma_tx_descriptor, node);
	tail_desc = list_last_entry(&chan->pending_list,
				    struct anlogic_dma_tx_descriptor, node);
	tail_segment = list_last_entry(&tail_desc->segments,
				       struct anlogic_axidma_tx_segment, node);

	reg = dma_ctrl_read(chan, ANLOGIC_DMA_REG_DMACR);

	if (chan->desc_pendingcount <= ANLOGIC_DMA_COALESCE_MAX) {
		reg &= ~ANLOGIC_DMA_CR_COALESCE_MAX;
		reg |= chan->desc_pendingcount <<
				  ANLOGIC_DMA_CR_COALESCE_SHIFT;
		dma_ctrl_write(chan, ANLOGIC_DMA_REG_DMACR, reg);
	}

	if (chan->has_sg)
		anlogic_write(chan, ANLOGIC_DMA_REG_CURDESC,
			     head_desc->async_tx.phys);

	anlogic_dma_start(chan);

	if (chan->err)
		return;

	/* Start the transfer */
	if (chan->has_sg) {
		if (chan->cyclic)
			anlogic_write(chan, ANLOGIC_DMA_REG_TAILDESC,
				     chan->cyclic_seg_v->phys);
		else
			anlogic_write(chan, ANLOGIC_DMA_REG_TAILDESC,
				     tail_segment->phys);
	} else {
		struct anlogic_axidma_tx_segment *segment;
		struct anlogic_axidma_desc_hw *hw;

		segment = list_first_entry(&head_desc->segments,
					   struct anlogic_axidma_tx_segment,
					   node);
		hw = &segment->hw;

		anlogic_write(chan, ANLOGIC_DMA_REG_SRCDSTADDR,
			     anlogic_prep_dma_addr_t(hw->buf_addr));

		/* Start the transfer */
		dma_ctrl_write(chan, ANLOGIC_DMA_REG_BTT,
			       hw->control & chan->al_dev->max_buffer_len);
	}

	if (chan->has_sg) {
		list_splice_tail_init(&chan->pending_list, &chan->active_list);
		chan->desc_pendingcount = 0;
	} else {
		list_move_tail(&head_desc->node, &chan->active_list);
		chan->desc_pendingcount--;
	}
	chan->idle = false;
}

static int anlogic_axidma_stop_transfer(struct anlogic_dma_chan *chan)
{
	u32 val;

	dma_ctrl_clr(chan, ANLOGIC_DMA_REG_DMACR, ANLOGIC_DMA_DMACR_RUNSTOP);

	/* Wait for the hardware to halt */
	return anlogic_dma_poll_timeout(chan, ANLOGIC_DMA_REG_DMASR, val,
				       val & ANLOGIC_DMA_DMASR_HALTED, 0,
				       ANLOGIC_DMA_LOOP_COUNT);
}

static void anlogic_axidma_complete_descriptor(struct anlogic_dma_chan *chan)
{
	struct anlogic_dma_tx_descriptor *desc, *next;

	/* This function was invoked with lock held */
	if (list_empty(&chan->active_list))
		return;

	list_for_each_entry_safe(desc, next, &chan->active_list, node) {
		if (chan->has_sg)
			desc->residue = anlogic_axidma_get_residue(chan, desc);
		else
			desc->residue = 0;
		desc->err = chan->err;

		list_del(&desc->node);
		if (!desc->cyclic)
			dma_cookie_complete(&desc->async_tx);
		list_add_tail(&desc->node, &chan->done_list);
	}
}

static void anlogic_axidma_append_desc_queue(struct anlogic_dma_chan *chan,
			      struct anlogic_dma_tx_descriptor *desc)
{
	struct anlogic_dma_tx_descriptor *tail_desc;
	struct anlogic_axidma_tx_segment *axidma_tail_segment;

	if (list_empty(&chan->pending_list))
		goto append;

	/*
	 * Add the hardware descriptor to the chain of hardware descriptors
	 * that already exists in memory.
	 */
	tail_desc = list_last_entry(&chan->pending_list,
				    struct anlogic_dma_tx_descriptor, node);

	axidma_tail_segment = list_last_entry(&tail_desc->segments,
				       struct anlogic_axidma_tx_segment,
				       node);
	axidma_tail_segment->hw.next_desc = (u32)desc->async_tx.phys;

	/*
	 * Add the software descriptor and all children to the list
	 * of pending transactions
	 */
append:
	list_add_tail(&desc->node, &chan->pending_list);
	chan->desc_pendingcount++;
}

struct anlogic_dma_init axidma_init = {
	.dma_ops = {
		.device_alloc_chan_resources = anlogic_axidma_alloc_chan_resources,
		.device_free_chan_resources = anlogic_axidma_free_chan_resources,
		.device_terminate_all = anlogic_axidma_terminate_all,
		.device_synchronize = anlogic_axidma_synchronize,
		.device_tx_status = anlogic_axidma_tx_status,
		.device_issue_pending = anlogic_axidma_issue_pending,
		.device_config = anlogic_axidma_device_config,
		.device_prep_slave_sg = anlogic_axidma_prep_slave_sg,
		.device_prep_dma_cyclic = anlogic_axidma_prep_dma_cyclic,
		.residue_granularity = DMA_RESIDUE_GRANULARITY_SEGMENT,
	},

	.desc_ops = {
		.complete_descriptor = anlogic_axidma_complete_descriptor,
		.append_desc_queue = anlogic_axidma_append_desc_queue,
		.dma_free_tx_descriptor = anlogic_axidma_free_tx_descriptor,
	},

	.start_transfer = anlogic_axidma_start_transfer,
	.stop_transfer  = anlogic_axidma_stop_transfer,
};

MODULE_AUTHOR("anlogic, Inc.");
MODULE_DESCRIPTION("anlogic axi dma Controller Driver");
MODULE_LICENSE("GPL");

/* Exclusive MM2S controller lifecycle, with an unsubmitted reset peer. */
int bsp_motion_dma_quiescent(struct dma_chan *tx, struct dma_chan *rx)
{
    struct anlogic_dma_chan *a = to_anlogic_chan(tx), *b = to_anlogic_chan(rx);
    struct anlogic_dma_chan *channels[2] = {a, b};
    unsigned long flags;
    int i;
    if (a->al_dev != b->al_dev || a->direction != DMA_MEM_TO_DEV ||
        b->direction != DMA_DEV_TO_MEM || a->has_sg || b->has_sg ||
        !of_property_read_bool(a->dev->of_node, "bsp,motion-exclusive-controller"))
        return -EINVAL;
    for (i = 0; i < 2; i++) {
        struct anlogic_dma_chan *c = channels[i];
        u32 cr, sr;
        synchronize_irq(c->irq);
        tasklet_kill(&c->tasklet);
        cr = dma_ctrl_read(c, ANLOGIC_DMA_REG_DMACR);
        sr = dma_ctrl_read(c, ANLOGIC_DMA_REG_DMASR);
        if ((cr & (ANLOGIC_DMA_DMACR_RUNSTOP | ANLOGIC_DMA_DMACR_RESET)) ||
            !(sr & ANLOGIC_DMA_DMASR_HALTED))
            return -EBUSY;
        spin_lock_irqsave(&c->lock, flags);
        if (!list_empty(&c->active_list) || !list_empty(&c->pending_list) ||
            !list_empty(&c->done_list)) {
            spin_unlock_irqrestore(&c->lock, flags);
            return -EBUSY;
        }
        spin_unlock_irqrestore(&c->lock, flags);
    }
    /* Verify a stable post-reset interval with submissions still blocked.
     * This supplements the provider's terminate/reset protocol; it is not an
     * independent physical HP outstanding-transaction monitor. */
    msleep(10);
    for (i = 0; i < 2; i++) {
        struct anlogic_dma_chan *c = channels[i];
        u32 cr, sr;
        synchronize_irq(c->irq);
        tasklet_kill(&c->tasklet);
        cr = dma_ctrl_read(c, ANLOGIC_DMA_REG_DMACR);
        sr = dma_ctrl_read(c, ANLOGIC_DMA_REG_DMASR);
        if ((cr & (ANLOGIC_DMA_DMACR_RUNSTOP | ANLOGIC_DMA_DMACR_RESET)) ||
            !(sr & ANLOGIC_DMA_DMASR_HALTED) || (sr & ANLOGIC_DMA_DMASR_ALL_ERR_MASK))
            return -EBUSY;
        spin_lock_irqsave(&c->lock, flags);
        if (!list_empty(&c->active_list) || !list_empty(&c->pending_list) ||
            !list_empty(&c->done_list)) {
            spin_unlock_irqrestore(&c->lock, flags);
            return -EBUSY;
        }
        spin_unlock_irqrestore(&c->lock, flags);
    }
    /* The last channel reset can clear BOTH interrupt enables. Restore only
     * after both directions are halted and all old callbacks synchronized. */
    for (i = 0; i < 2; i++) {
        dma_ctrl_write(channels[i], ANLOGIC_DMA_REG_DMASR,
                       ANLOGIC_DMA_DMAXR_ALL_IRQ_MASK);
        dma_ctrl_set(channels[i], ANLOGIC_DMA_REG_DMACR,
                     ANLOGIC_DMA_DMAXR_ALL_IRQ_MASK);
    }
    dev_info(a->dev, "BSP motion controller quiescent: both HALTED, reset clear, IRQ/tasklets synchronized; no descriptor owns buffers\n");
    return 0;
}
EXPORT_SYMBOL_GPL(bsp_motion_dma_quiescent);

/* Bind before any submission, detach only after both channels synchronized. */
int bsp_motion_dma_fault_hook(struct dma_chan *tx, void (*stop)(void *), void *data)
{
    struct anlogic_dma_chan *c = to_anlogic_chan(tx);
    if (c->has_sg || c->direction != DMA_MEM_TO_DEV ||
        !of_property_read_bool(c->dev->of_node, "bsp,motion-exclusive-controller"))
        return -EINVAL;
    synchronize_irq(c->irq);
    c->motion_fault_data = data;
    c->motion_fault_stop = stop;
    return 0;
}
EXPORT_SYMBOL_GPL(bsp_motion_dma_fault_hook);

/* Independent instance only: never access the motion controller or MM2S. */
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
