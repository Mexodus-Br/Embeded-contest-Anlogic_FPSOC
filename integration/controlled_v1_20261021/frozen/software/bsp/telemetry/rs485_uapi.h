#ifndef BSP_RS485_UAPI_H
#define BSP_RS485_UAPI_H
#include <linux/types.h>
#include <linux/ioctl.h>
/* Typed operations only; no arbitrary address, offset, DMA pointer or mmap. */
struct rs485_packet { __u32 id,generation,bytes,actual,status,records; __u64 data; };
struct rs485_config { __u32 id,periods[5],mask,run,generation,revision,apply_sequence,error; __u64 notified_us; };
struct rs485_snapshot { __u32 id,generation,word[512]; };
struct rs485_diag { __u32 id,generation,revision,word[8]; };
struct rs485_state { __u32 blocked,owned,quarantine,generation,packet_id,packet_bytes,actual,dma_status; };
#define RS485_CONFIG _IOWR('R',1,struct rs485_config)
#define RS485_SNAPSHOT _IOWR('R',2,struct rs485_snapshot)
#define RS485_DIAG _IOR('R',3,struct rs485_diag)
#define RS485_RX _IOWR('R',4,struct rs485_packet)
#define RS485_COMPLETE _IOW('R',5,struct rs485_packet)
#define RS485_RECOVER _IO('R',6)
#define RS485_CANCEL _IO('R',7)
#define RS485_STATE _IOR('R',8,struct rs485_state)
#define RS485_RELEASE _IO('R',9)
#endif
