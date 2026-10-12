#ifndef BSP_DMA_UAPI_H
#define BSP_DMA_UAPI_H
#include <linux/types.h>
#include <linux/ioctl.h>
struct bsp_dma_test {
    __u32 length, pattern, scenario, timeout_ms;
    __u32 result, mismatch_offset, tx_callbacks, rx_callbacks;
    __u32 errors, timeouts, recoveries, generation;
    __u32 before_tx_status, before_rx_status, quiescent, inflight_observed;
    __u64 submit_ns, tx_complete_ns, rx_complete_ns, total_ns;
};
#define BSP_DMA_TEST _IOWR('L', 1, struct bsp_dma_test)
#endif
