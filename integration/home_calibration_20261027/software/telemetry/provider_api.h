#ifndef BSP_MOTION_PROVIDER_API_H
#define BSP_MOTION_PROVIDER_API_H
#include "generated/telem_defs.h"
struct dma_chan;
int bsp_motion_dma_quiescent(struct dma_chan *tx, struct dma_chan *rx);
int bsp_motion_dma_fault_hook(struct dma_chan *tx, void (*stop)(void *), void *data);
struct bsp_telem_result { int cookie; unsigned int actual,status; };
int bsp_telem_dma_result(struct dma_chan *rx,int cookie,struct bsp_telem_result *out);
int bsp_telem_dma_exact(struct dma_chan *rx,int cookie,unsigned int requested,struct bsp_telem_result *out);
int bsp_telem_dma_retire(struct dma_chan *rx,int cookie);
int bsp_telem_dma_quiescent(struct dma_chan *rx);
#endif
