#ifndef BSP_MOTION_PROVIDER_API_H
#define BSP_MOTION_PROVIDER_API_H
struct dma_chan;
int bsp_motion_dma_quiescent(struct dma_chan *tx, struct dma_chan *rx);
int bsp_motion_dma_fault_hook(struct dma_chan *tx, void (*stop)(void *), void *data);
#endif
