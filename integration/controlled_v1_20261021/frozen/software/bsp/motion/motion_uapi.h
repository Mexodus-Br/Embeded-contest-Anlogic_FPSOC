#ifndef BSP_MOTION_UAPI_H
#define BSP_MOTION_UAPI_H
#include <linux/types.h>
#include <linux/ioctl.h>
struct motion_command { __u32 opcode, axis_mask, timeout_ms, ack_error; __s64 position[4]; __u64 session; __u32 ack_status, generation; };
struct motion_packet { __u64 data; __u32 count, timeout_ms; __u64 submit_ns, ioc_ns, closed_ns; __u32 generation, packet_count, result, reserved; };
struct motion_snapshot { __u32 words[64]; __u32 id, generation, quarantined, dma_owned; __u64 event_count; };
#define MOTION_COMMAND _IOWR('M',1,struct motion_command)
#define MOTION_PACKET _IOWR('M',2,struct motion_packet)
#define MOTION_SNAPSHOT _IOR('M',3,struct motion_snapshot)
#define MOTION_STOP _IO('M',4)
#define MOTION_RECOVER _IO('M',5)
#define MOTION_REALLOC _IO('M',6)
#define MOTION_RELEASE _IO('M',9) /* quiesce + release buffer before module unload */
#define MOTION_INJECT _IOWR('M',8,struct motion_packet) /* isolated fixture only */
#define MOTION_EVENTS _IO('M',7)
#endif
