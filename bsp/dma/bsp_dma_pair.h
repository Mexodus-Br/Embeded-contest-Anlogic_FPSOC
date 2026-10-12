#ifndef BSP_DMA_PAIR_H
#define BSP_DMA_PAIR_H
struct dma_chan;
/* Process context; after terminate_sync on both channels, before reuse/free. */
int bsp_anlogic_loop_quiescent(struct dma_chan *tx, struct dma_chan *rx);
#endif
