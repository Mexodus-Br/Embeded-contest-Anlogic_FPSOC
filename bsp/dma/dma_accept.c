// SPDX-License-Identifier: GPL-2.0
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include "dma_uapi.h"
static unsigned tests;
static uint64_t bytes, dma_ns, submit_ns, worst_complete;
static int one(int fd,unsigned len,unsigned pattern,unsigned scenario)
{
    struct bsp_dma_test t={.length=len,.pattern=pattern,.scenario=scenario,.timeout_ms=scenario?100:1000};
    uint64_t complete;
    if(ioctl(fd,BSP_DMA_TEST,&t)<0){perror("BSP_DMA_TEST");return -1;}
    printf("DMA len=%u pattern=%u scenario=%u result=%u mismatch=%u callbacks=%u/%u submit_ns=%" PRIu64 " complete_ns=%" PRIu64 "/%" PRIu64 " total_ns=%" PRIu64 " errors=%u timeouts=%u recoveries=%u generation=%u\n",
      len,pattern,scenario,t.result,t.mismatch_offset,t.tx_callbacks,t.rx_callbacks,
      (uint64_t)t.submit_ns,(uint64_t)t.tx_complete_ns,(uint64_t)t.rx_complete_ns,
      (uint64_t)t.total_ns,t.errors,t.timeouts,t.recoveries,t.generation);
    fflush(stdout);
    printf("PAIR before_status=%u/%u quiescent=%u inflight_observed=%u\n",t.before_tx_status,t.before_rx_status,t.quiescent,t.inflight_observed);
    if(t.result || !t.quiescent || (scenario && !t.inflight_observed) || (!scenario && (t.tx_callbacks!=1 || t.rx_callbacks!=1))){fprintf(stderr,"DMA_ACCEPT_FAIL\n");return -1;}
    tests++;
    if(!scenario){
      complete=t.tx_complete_ns>t.rx_complete_ns?t.tx_complete_ns:t.rx_complete_ns;
      bytes+=len;dma_ns+=complete;submit_ns+=t.submit_ns;
      if(complete>worst_complete)worst_complete=complete;
    }
    return 0;
}
int main(int argc,char **argv)
{
    const unsigned lengths[]={1,7,8,9,15,16,31,127,128,129,255,256,4095,4096,4097,8193,65535};
    unsigned round,p,i;
    int fd;
    if(argc!=2){fprintf(stderr,"Usage: dma-accept /dev/bsp-dma-loop\n");return 2;}
    fd=open(argv[1],O_RDWR|O_CLOEXEC);
    if(fd<0){perror("open");return 1;}
    for(round=0;round<3;round++)for(p=0;p<4;p++)for(i=0;i<sizeof(lengths)/sizeof(lengths[0]);i++)
      if(one(fd,lengths[i],p,0))goto fail;
    for(round=0;round<3;round++){
      for(p=1;p<=3;p++){
        if(one(fd,65535,round%4,p) || one(fd,4097,round%4,0))goto fail;
      }
    }
    printf("DMA_ACCEPT_PASS tests=%u payload_bytes=%" PRIu64 " sum_submit_ns=%" PRIu64 " sum_completion_ns=%" PRIu64 " worst_completion_ns=%" PRIu64 " aggregate_payload_MBps=%.3f (submit-to-IRQ, not bus-only bandwidth); no motion\n",
      tests,bytes,submit_ns,dma_ns,worst_complete,dma_ns?1000.0*(double)bytes/(double)dma_ns:0.0);
    close(fd);return 0;
fail:close(fd);return 1;
}
