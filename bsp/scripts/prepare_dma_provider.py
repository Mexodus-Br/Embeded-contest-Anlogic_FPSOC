"""Patch a frozen matching GPL provider working copy; original kernel untouched."""
from pathlib import Path
import hashlib,json,difflib
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'dma/provider';V=P/'vendor'
records={};patch=[]
def write(name,text):
    old=(V/name).read_text(encoding='utf-8')
    patch.extend(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
    (P/name).write_text(text,encoding='utf-8')
for f in sorted(V.iterdir()):
    records[f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
lock=ROOT/'dma/provider-inputs.json'
if lock.exists():assert json.loads(lock.read_text())==records,'Matched provider inputs changed'
else:lock.write_text(json.dumps(records,indent=2)+'\n')
# Internal DMAengine helpers and public vendor header from this exact source.
(P/'dmaengine.h').write_bytes((V/'dmaengine.h').read_bytes())
(P/'include/linux/dma').mkdir(parents=True,exist_ok=True)
(P/'include/linux/dma/anlogic_dma.h').write_bytes((V/'anlogic_dma.h').read_bytes())
t=(V/'anlogic_dma.c').read_text()
t=t.replace('#include "../dmaengine.h"','#include "dmaengine.h"')
t=t.replace('#include <linux/dma/anlogic_dma.h>','#include <linux/dma/anlogic_dma.h>\n#include "../generated/dma_defs.h"')
t=t.replace('u32 num_frames, addr_width, len_width;','u32 num_frames = 0, addr_width = 32, len_width;')
needle='\t/* Request and map I/O memory */'
guard='''\t/* This additional policy applies only to the independent loop profile. */
\tif (of_property_read_bool(node, "bsp,loopback-pair")) {
\t\tstruct resource *r = platform_get_resource(pdev, IORESOURCE_MEM, 0);
\t\tu32 aw, lw;
\t\tif (!r || r->start != PLI_DMA_DMA_LOOPBACK_V1_BASE || resource_size(r) != PLI_DMA_DMA_LOOPBACK_V1_SIZE ||
\t\t    of_property_read_u32(node, "anlogic,addrwidth", &aw) || aw != PLI_DMA_DMA_LOOPBACK_V1_MEMORY_ADDRESS_WIDTH ||
\t\t    of_property_read_u32(node, "anlogic,sg-length-width", &lw) || lw != PLI_DMA_DMA_LOOPBACK_V1_AL_SG_LENGTH_WIDTH ||
\t\t    of_property_read_bool(node, "anlogic,include-sg"))
\t\t\treturn -EINVAL;
\t}

'''
assert t.count(needle)==1;t=t.replace(needle,guard+needle)
start=t.index('static const struct anlogic_dma_config axivdma_config = {')
end=t.index('\n};',start)+3
t=t[:start]+'#ifdef CONFIG_AXI_VDMA\n'+t[start:end]+'\n#endif'+t[end:]
# No implicit per-channel error reset: it can destroy the other direction's
# packet. A loopback consumer must stop both via DMAengine and recover as a pair.
needle='\tif (chan->err) {\n\t\t/*\n\t\t * If reset fails'
replacement='\tif (chan->err && of_property_read_bool(chan->dev->of_node, "bsp,loopback-pair")) {\n\t\tal_dev->desc_ops.dma_free_tx_descriptor(chan, desc);\n\t\treturn -EIO;\n\t}\n\n'+needle
assert t.count(needle)==1;t=t.replace(needle,replacement)
write('anlogic_dma.c',t)
t=(V/'axi-dma.c').read_text().replace('#include "../dmaengine.h"','#include "dmaengine.h"')
t=t.replace('#include <linux/dma/anlogic_dma.h>','#include <linux/dma/anlogic_dma.h>\n#include "../bsp_dma_pair.h"')
t=t.replace(' * anlogic_dma_start_transfer - Starts DMA transfer',' * anlogic_axidma_start_transfer - Starts DMA transfer')
t=t.replace('\t\t\tchan->err = true;\n\t\t}\n\t}\n\n\tanlogic_dma_chan_reset(chan);',
            '\t\t\tchan->err = true;\n\t\t\treturn err; /* Do not free descriptors on an unconfirmed halt. */\n\t\t}\n\t}\n\n\terr = anlogic_dma_chan_reset(chan);\n\tif (err)\n\t\treturn err;')
assert 'return err; /* Do not free' in t
# RUNSTOP alone can wait indefinitely for the missing S2MM packet/TLAST.
# The private duplex client holds both buffers and blocks all submissions while
# terminating both channels. For this sealed simple pair only, reset the DMA
# controller before freeing any channel descriptors, then prove BOTH hardware
# directions halted. The consumer still synchronizes both IRQ/tasklets and
# checks both software queues before any buffer reuse or release.
needle='\tif (!chan->cyclic) {\n\t\terr = chan->stop_transfer(chan);'
assert t.count(needle)==1
t=t.replace(needle, '\tif (!of_property_read_bool(chan->dev->of_node, "bsp,loopback-pair") &&\n\t    !chan->cyclic) {\n\t\terr = chan->stop_transfer(chan);', 1)
needle='\tif (err)\n\t\treturn err;\n\t/* Remove and free all of the descriptors in the lists */'
paired='''\tif (err)
\t\treturn err;
\tif (of_property_read_bool(chan->dev->of_node, "bsp,loopback-pair")) {
\t\tint i;
\t\tu32 sr, cr;
\t\tfor (i = 0; i < 2; i++) {
\t\t\tstruct anlogic_dma_chan *peer = chan->al_dev->chan[i];
\t\t\tif (!peer || peer->has_sg)
\t\t\t\treturn -EINVAL;
\t\t\terr = anlogic_dma_poll_timeout(peer, ANLOGIC_DMA_REG_DMASR, sr,
\t\t\t\t\t\t      sr & ANLOGIC_DMA_DMASR_HALTED, 0,
\t\t\t\t\t\t      ANLOGIC_DMA_LOOP_COUNT);
\t\t\tcr = dma_ctrl_read(peer, ANLOGIC_DMA_REG_DMACR);
\t\t\tif (err || (cr & (ANLOGIC_DMA_DMACR_RUNSTOP | ANLOGIC_DMA_DMACR_RESET)))
\t\t\t\treturn err ? err : -EBUSY;
\t\t}
\t}
\t/* Remove and free all of the descriptors in the lists */'''
assert t.count(needle)==1;t=t.replace(needle,paired,1)
t=t.replace('\ttasklet_kill(&chan->tasklet);','\tsynchronize_irq(chan->irq);\n\ttasklet_kill(&chan->tasklet);')
# Simple hardware only executes the first descriptor. Reject unsupported
# multi-SG/oversized/direction-mismatched submissions before programming BTT.
needle='\tif (!is_slave_direction(direction))\n\t\treturn NULL;'
guard=needle+'\n\tif (!chan->has_sg && (direction != chan->direction || sg_len != 1 ||\n\t    !sg_dma_len(sgl) || sg_dma_len(sgl) > chan->al_dev->max_buffer_len ||\n\t    (sg_dma_address(sgl) & 7)))\n\t\treturn NULL;'
assert t.count(needle)==2
t=t.replace(needle,guard,1)
# Simple pending list must move only its programmed descriptor to active.
t=t.replace('\tlist_splice_tail_init(&chan->pending_list, &chan->active_list);\n\tchan->desc_pendingcount = 0;',
'''\tif (chan->has_sg) {
\t\tlist_splice_tail_init(&chan->pending_list, &chan->active_list);
\t\tchan->desc_pendingcount = 0;
\t} else {
\t\tlist_move_tail(&head_desc->node, &chan->active_list);
\t\tchan->desc_pendingcount--;
\t}''')
# A failed channel must return DMA_ERROR even when cookie status has not moved.
t=t.replace('\tret = dma_cookie_status(dchan, cookie, txstate);','\tif (READ_ONCE(chan->err))\n\t\treturn DMA_ERROR;\n\tret = dma_cookie_status(dchan, cookie, txstate);')
t+='''
/* Narrow loopback-only postcondition, not a general raw-register API. */
int bsp_anlogic_loop_quiescent(struct dma_chan *tx, struct dma_chan *rx)
{
    struct anlogic_dma_chan *a = to_anlogic_chan(tx), *b = to_anlogic_chan(rx);
    struct anlogic_dma_chan *channels[2] = {a, b};
    unsigned long flags;
    int i;
    if (a->al_dev != b->al_dev || a->direction != DMA_MEM_TO_DEV ||
        b->direction != DMA_DEV_TO_MEM || a->has_sg || b->has_sg ||
        !of_property_read_bool(a->dev->of_node, "bsp,loopback-pair"))
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
    /* The last channel reset can clear BOTH interrupt enables. Restore only
     * after both directions are halted and all old callbacks synchronized. */
    for (i = 0; i < 2; i++) {
        dma_ctrl_write(channels[i], ANLOGIC_DMA_REG_DMASR,
                       ANLOGIC_DMA_DMAXR_ALL_IRQ_MASK);
        dma_ctrl_set(channels[i], ANLOGIC_DMA_REG_DMACR,
                     ANLOGIC_DMA_DMAXR_ALL_IRQ_MASK);
    }
    dev_info(a->dev, "BSP loop pair quiescent: both HALTED, reset clear, IRQ/tasklets synchronized; no descriptor owns buffers\\n");
    return 0;
}
EXPORT_SYMBOL_GPL(bsp_anlogic_loop_quiescent);
'''
write('axi-dma.c',t)
(ROOT/'dma/patches/0001-simple-loopback-provider.patch').write_text(''.join(patch),encoding='utf-8')
print('Matched provider patched; old source/build tree unchanged. Inputs:',records)
