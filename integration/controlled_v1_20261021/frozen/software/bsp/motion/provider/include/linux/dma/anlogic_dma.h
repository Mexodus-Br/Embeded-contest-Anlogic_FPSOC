/* SPDX-License-Identifier: GPL-2.0 */
/*
 * Anlogic DMA Engine drivers support header file
 *
 * Copyright (c) 2024 anlogic Technologies Co., Ltd.
 */

#ifndef __DMA_ANLOGIC_DMA_H
#define __DMA_ANLOGIC_DMA_H

#include <linux/dma-mapping.h>
#include <linux/dmaengine.h>
#include <linux/interrupt.h>
#include <linux/io-64-nonatomic-lo-hi.h>

/* Register/Descriptor Offsets */
#define ANLOGIC_DMA_MM2S_CTRL_OFFSET		0x0000
#define ANLOGIC_DMA_S2MM_CTRL_OFFSET		0x0030
#define ANLOGIC_VDMA_MM2S_DESC_OFFSET		0x0050
#define ANLOGIC_VDMA_S2MM_DESC_OFFSET		0x00a0

/* Control Registers */
#define ANLOGIC_DMA_REG_DMACR			0x0000
#define ANLOGIC_DMA_DMACR_DELAY_MAX		0xff
#define ANLOGIC_DMA_DMACR_DELAY_SHIFT		24
#define ANLOGIC_DMA_DMACR_FRAME_COUNT_MAX	0xff
#define ANLOGIC_DMA_DMACR_FRAME_COUNT_SHIFT	16
#define ANLOGIC_DMA_DMACR_ERR_IRQ		BIT(14)
#define ANLOGIC_DMA_DMACR_DLY_CNT_IRQ		BIT(13)
#define ANLOGIC_DMA_DMACR_FRM_CNT_IRQ		BIT(12)
#define ANLOGIC_DMA_DMACR_MASTER_SHIFT		8
#define ANLOGIC_DMA_DMACR_FSYNCSRC_SHIFT	5
#define ANLOGIC_DMA_DMACR_FRAMECNT_EN		BIT(4)
#define ANLOGIC_DMA_DMACR_GENLOCK_EN		BIT(3)
#define ANLOGIC_DMA_DMACR_RESET			BIT(2)
#define ANLOGIC_DMA_DMACR_CIRC_EN		BIT(1)
#define ANLOGIC_DMA_DMACR_RUNSTOP		BIT(0)
#define ANLOGIC_DMA_DMACR_FSYNCSRC_MASK		GENMASK(6, 5)
#define ANLOGIC_DMA_DMACR_DELAY_MASK		GENMASK(31, 24)
#define ANLOGIC_DMA_DMACR_FRAME_COUNT_MASK	GENMASK(23, 16)
#define ANLOGIC_DMA_DMACR_MASTER_MASK		GENMASK(11, 8)

#define ANLOGIC_DMA_REG_DMASR			0x0004
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

#define ANLOGIC_DMA_REG_CURDESC			0x0008
#define ANLOGIC_DMA_REG_TAILDESC		0x0010
#define ANLOGIC_DMA_REG_REG_INDEX		0x0014
#define ANLOGIC_DMA_REG_FRMSTORE		0x0018
#define ANLOGIC_DMA_REG_THRESHOLD		0x001c
#define ANLOGIC_DMA_REG_FRMPTR_STS		0x0024
#define ANLOGIC_DMA_REG_PARK_PTR		0x0028
#define ANLOGIC_DMA_PARK_PTR_WR_REF_SHIFT	8
#define ANLOGIC_DMA_PARK_PTR_WR_REF_MASK		GENMASK(12, 8)
#define ANLOGIC_DMA_PARK_PTR_RD_REF_SHIFT	0
#define ANLOGIC_DMA_PARK_PTR_RD_REF_MASK		GENMASK(4, 0)
#define ANLOGIC_DMA_REG_VDMA_VERSION		0x002c

/* Register Direct Mode Registers */
#define ANLOGIC_DMA_REG_VSIZE			0x0000
#define ANLOGIC_DMA_REG_HSIZE			0x0004

#define ANLOGIC_DMA_REG_FRMDLY_STRIDE		0x0008
#define ANLOGIC_DMA_FRMDLY_STRIDE_FRMDLY_SHIFT	24
#define ANLOGIC_DMA_FRMDLY_STRIDE_STRIDE_SHIFT	0

#define ANLOGIC_VDMA_REG_START_ADDRESS(n)	(0x000c + 4 * (n))
#define ANLOGIC_VDMA_REG_START_ADDRESS_64(n)	(0x000c + 8 * (n))

#define ANLOGIC_VDMA_REG_ENABLE_VERTICAL_FLIP	0x00ec
#define ANLOGIC_VDMA_ENABLE_VERTICAL_FLIP	BIT(0)

/* HW specific definitions */
#define ANLOGIC_MCDMA_MAX_CHANS_PER_DEVICE	0x20
#define ANLOGIC_DMA_MAX_CHANS_PER_DEVICE		0x2
#define ANLOGIC_CDMA_MAX_CHANS_PER_DEVICE	0x1

#define ANLOGIC_DMA_DMAXR_ALL_IRQ_MASK	\
		(ANLOGIC_DMA_DMASR_FRM_CNT_IRQ | \
		 ANLOGIC_DMA_DMASR_DLY_CNT_IRQ | \
		 ANLOGIC_DMA_DMASR_ERR_IRQ)

#define ANLOGIC_DMA_DMASR_ALL_ERR_MASK	\
		(ANLOGIC_DMA_DMASR_EOL_LATE_ERR | \
		 ANLOGIC_DMA_DMASR_SOF_LATE_ERR | \
		 ANLOGIC_DMA_DMASR_SG_DEC_ERR | \
		 ANLOGIC_DMA_DMASR_SG_SLV_ERR | \
		 ANLOGIC_DMA_DMASR_EOF_EARLY_ERR | \
		 ANLOGIC_DMA_DMASR_SOF_EARLY_ERR | \
		 ANLOGIC_DMA_DMASR_DMA_DEC_ERR | \
		 ANLOGIC_DMA_DMASR_DMA_SLAVE_ERR | \
		 ANLOGIC_DMA_DMASR_DMA_INT_ERR)

/*
 * Recoverable errors are DMA Internal error, SOF Early, EOF Early
 * and SOF Late. They are only recoverable when C_FLUSH_ON_FSYNC
 * is enabled in the h/w system.
 */
#define ANLOGIC_DMA_DMASR_ERR_RECOVER_MASK	\
		(ANLOGIC_DMA_DMASR_SOF_LATE_ERR | \
		 ANLOGIC_DMA_DMASR_EOF_EARLY_ERR | \
		 ANLOGIC_DMA_DMASR_SOF_EARLY_ERR | \
		 ANLOGIC_DMA_DMASR_DMA_INT_ERR)

/* Axi VDMA Flush on Fsync bits */
#define ANLOGIC_DMA_FLUSH_S2MM		3
#define ANLOGIC_DMA_FLUSH_MM2S		2
#define ANLOGIC_DMA_FLUSH_BOTH		1

/* Delay loop counter to prevent hardware failure */
#define ANLOGIC_DMA_LOOP_COUNT		1000000

/* AXI DMA Specific Registers/Offsets */
#define ANLOGIC_DMA_REG_SRCDSTADDR	0x18
#define ANLOGIC_DMA_REG_BTT		0x28

/* AXI DMA Specific Masks/Bit fields */
#define ANLOGIC_DMA_MAX_TRANS_LEN_MIN	8
#define ANLOGIC_DMA_MAX_TRANS_LEN_MAX	23
#define ANLOGIC_DMA_V2_MAX_TRANS_LEN_MAX	26
#define ANLOGIC_DMA_CR_COALESCE_MAX	GENMASK(23, 16)
#define ANLOGIC_DMA_CR_CYCLIC_BD_EN_MASK	BIT(4)
#define ANLOGIC_DMA_CR_COALESCE_SHIFT	16
#define ANLOGIC_DMA_BD_SOP		BIT(27)
#define ANLOGIC_DMA_BD_EOP		BIT(26)
#define ANLOGIC_DMA_COALESCE_MAX		255
#define ANLOGIC_DMA_NUM_DESCS		255
#define ANLOGIC_DMA_NUM_APP_WORDS	5

#define anlogic_prep_dma_addr_t(addr)	\
	((dma_addr_t)((u64)addr##_##msb << 32 | (addr)))


struct anlogic_vdma_config {
	int frm_dly;
	int gen_lock;
	int master;
	int frm_cnt_en;
	int park;
	int park_frm;
	int coalesc;
	int delay;
	int reset;
	int ext_fsync;
	bool vflip_en;
};

struct anlogic_vdma_desc_hw {
	u32 next_desc;
	u32 pad1;
	u32 buf_addr;
	u32 buf_addr_msb;
	u32 vsize;
	u32 hsize;
	u32 stride;
} __aligned(64);

struct anlogic_axidma_desc_hw {
	u32 next_desc;
	u32 next_desc_msb;
	u32 buf_addr;
	u32 buf_addr_msb;
	u32 reserved1;
	u32 reserved2;
	u32 control;
	u32 status;
	u32 app[ANLOGIC_DMA_NUM_APP_WORDS];
} __aligned(64);

struct anlogic_vdma_tx_segment {
	struct anlogic_vdma_desc_hw hw;
	struct list_head node;
	dma_addr_t phys;
} __aligned(64);

struct anlogic_axidma_tx_segment {
	struct anlogic_axidma_desc_hw hw;
	struct list_head node;
	dma_addr_t phys;
} __aligned(64);

struct anlogic_dma_tx_descriptor {
	struct dma_async_tx_descriptor async_tx;
	struct list_head segments;
	struct list_head node;
	bool cyclic;
	bool err;
	u32 residue;
};

struct anlogic_dma_chan {
	struct anlogic_dma_device *al_dev;
	u32 ctrl_offset;
	u32 desc_offset;
	spinlock_t lock;
	struct list_head pending_list;
	struct list_head active_list;
	struct list_head done_list;
	struct list_head free_seg_list;
	struct dma_chan common;
	struct dma_pool *desc_pool;
	struct device *dev;
	int irq;
	int id;
	enum dma_transfer_direction direction;
	int num_frms;
	bool has_sg;
	bool cyclic;
	bool genlock;
	bool err;
	bool idle;
	bool terminating;
	void (*motion_fault_stop)(void *data);
	void *motion_fault_data;
	struct tasklet_struct tasklet;
	struct anlogic_vdma_config config;
	bool flush_on_fsync;
	u32 desc_pendingcount;
	bool ext_addr;
	u32 desc_submitcount;
	struct anlogic_axidma_tx_segment *seg_v;
	struct anlogic_aximcdma_tx_segment *seg_mv;
	dma_addr_t seg_p;
	struct anlogic_axidma_tx_segment *cyclic_seg_v;
	dma_addr_t cyclic_seg_p;
	void (*start_transfer)(struct anlogic_dma_chan *chan);
	int (*stop_transfer)(struct anlogic_dma_chan *chan);
	u16 tdest;
	bool has_vflip;
};

enum al_dma_ip_type {
	AL_DMA_TYPE_AXIDMA = 0,
	AL_DMA_TYPE_VDMA,
};

struct anlogic_dma_config {
	enum al_dma_ip_type dmatype;
	irqreturn_t (*irq_handler)(int irq, void *data);
	const int max_channels;
};

struct dma_desc_ops {
	void (*complete_descriptor)(struct anlogic_dma_chan *chan);
	void (*append_desc_queue)(struct anlogic_dma_chan *chan,
			      struct anlogic_dma_tx_descriptor *desc);
	void (*dma_free_tx_descriptor)(struct anlogic_dma_chan *chan,
			       struct anlogic_dma_tx_descriptor *desc);
};

struct anlogic_dma_device {
	void __iomem *regs;
	struct device *dev;
	struct dma_device common;
	struct anlogic_dma_chan *chan[ANLOGIC_MCDMA_MAX_CHANS_PER_DEVICE];
	u32 flush_on_fsync;
	bool ext_addr;
	struct platform_device *pdev;
	const struct anlogic_dma_config *dma_config;
	struct dma_desc_ops desc_ops;
	u32 s2mm_chan_id;
	u32 mm2s_chan_id;
	u32 max_buffer_len;
};

struct anlogic_dma_init {
	struct dma_device dma_ops;
	struct dma_desc_ops desc_ops;
	void (*start_transfer)(struct anlogic_dma_chan *chan);
	int (*stop_transfer)(struct anlogic_dma_chan *chan);
};

/* Macros */
#define to_anlogic_chan(chan) \
	container_of(chan, struct anlogic_dma_chan, common)
#define to_dma_tx_descriptor(tx) \
	container_of(tx, struct anlogic_dma_tx_descriptor, async_tx)
#define anlogic_dma_poll_timeout(chan, reg, val, cond, delay_us, timeout_us) \
	readl_poll_timeout_atomic(chan->al_dev->regs + chan->ctrl_offset + reg, \
				  val, cond, delay_us, timeout_us)

/* IO accessors */
static inline u32 dma_read(struct anlogic_dma_chan *chan, u32 reg)
{
	return ioread32(chan->al_dev->regs + reg);
}

static inline void dma_write(struct anlogic_dma_chan *chan, u32 reg, u32 value)
{
	iowrite32(value, chan->al_dev->regs + reg);
}

static inline u32 dma_ctrl_read(struct anlogic_dma_chan *chan, u32 reg)
{
	return dma_read(chan, chan->ctrl_offset + reg);
}

static inline void dma_ctrl_write(struct anlogic_dma_chan *chan, u32 reg,
				   u32 value)
{
	dma_write(chan, chan->ctrl_offset + reg, value);
}

static inline void dma_ctrl_clr(struct anlogic_dma_chan *chan, u32 reg,
				 u32 clr)
{
	dma_ctrl_write(chan, reg, dma_ctrl_read(chan, reg) & ~clr);
}

static inline void dma_ctrl_set(struct anlogic_dma_chan *chan, u32 reg,
				 u32 set)
{
	dma_ctrl_write(chan, reg, dma_ctrl_read(chan, reg) | set);
}

static inline void dma_writeq(struct anlogic_dma_chan *chan, u32 reg, u64 value)
{
	lo_hi_writeq(value, chan->al_dev->regs + chan->ctrl_offset + reg);
}

static inline void anlogic_write(struct anlogic_dma_chan *chan, u32 reg,
				dma_addr_t addr)
{
	if (chan->ext_addr)
		dma_writeq(chan, reg, addr);
	else
		dma_ctrl_write(chan, reg, addr);
}

static inline void anlogic_axidma_buf(struct anlogic_dma_chan *chan,
				     struct anlogic_axidma_desc_hw *hw,
				     dma_addr_t buf_addr, size_t sg_used,
				     size_t period_len)
{
	if (chan->ext_addr) {
		hw->buf_addr = lower_32_bits(buf_addr + sg_used + period_len);
		hw->buf_addr_msb = upper_32_bits(buf_addr + sg_used +
						 period_len);
	} else {
		hw->buf_addr = buf_addr + sg_used + period_len;
	}
}

static inline void vdma_desc_write_64(struct anlogic_dma_chan *chan, u32 reg,
				      u32 value_lsb, u32 value_msb)
{
	/* Write the lsb 32 bits*/
	writel(value_lsb, chan->al_dev->regs + chan->desc_offset + reg);

	/* Write the msb 32 bits */
	writel(value_msb, chan->al_dev->regs + chan->desc_offset + reg + 4);
}

static inline void vdma_desc_write(struct anlogic_dma_chan *chan, u32 reg,
				   u32 value)
{
	dma_write(chan, chan->desc_offset + reg, value);
}

// Universal interface
int anlogic_dma_chan_reset(struct anlogic_dma_chan *chan);
struct anlogic_dma_tx_descriptor *anlogic_dma_alloc_tx_descriptor(
	struct anlogic_dma_chan *chan);
struct anlogic_axidma_tx_segment *anlogic_axidma_alloc_tx_segment(
	struct anlogic_dma_chan *chan);
void anlogic_dma_free_tx_segment(
	struct anlogic_dma_chan *chan,
	struct anlogic_axidma_tx_segment *segment);
int anlogic_dma_calc_copysize(
	struct anlogic_dma_chan *chan,
	int size,
	int done);
dma_cookie_t anlogic_dma_tx_submit(struct dma_async_tx_descriptor *tx);
void anlogic_dma_start(struct anlogic_dma_chan *chan);

// axi dma interface
extern struct anlogic_dma_init axidma_init;

// axi vdma interface
extern struct anlogic_dma_init axivdma_init;

int anlogic_vdma_channel_set_config(struct dma_chan *dchan,
					struct anlogic_vdma_config *cfg);

void anlogic_vdma_free_tx_segment(struct anlogic_dma_chan *chan,
					struct anlogic_vdma_tx_segment *segment);

#endif
