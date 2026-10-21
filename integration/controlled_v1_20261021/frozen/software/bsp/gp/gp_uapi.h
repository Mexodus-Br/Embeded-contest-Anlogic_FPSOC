#ifndef BSP_GP_UAPI_H
#define BSP_GP_UAPI_H
#include <linux/types.h>
#include <linux/ioctl.h>
struct gp_identity { __u32 version, caps, features, tick_hz, last_txn, state; };
struct gp_scratch { __u32 value; };
struct gp_command {
 __u32 opcode, repeat, txn, status, error, snapshot_valid, snapshot_id, reserved;
 __aligned_u64 timestamp, position[4], pulses[4], session;
 __u32 state, position_valid, accepted_seq, done_seq;
};
struct gp_irq_config { __u32 mask, source, clear, pending, actual_mask, actual_source; };
struct gp_event { __aligned_u64 count; __u32 pending, reserved; };
#define GP_IDENTITY _IOR('G', 0, struct gp_identity)
#define GP_SCRATCH _IOWR('G', 1, struct gp_scratch)
#define GP_COMMAND _IOWR('G', 2, struct gp_command)
#define GP_IRQ_CONFIG _IOWR('G', 3, struct gp_irq_config)
#define GP_EVENT _IOR('G', 4, struct gp_event)
#endif
