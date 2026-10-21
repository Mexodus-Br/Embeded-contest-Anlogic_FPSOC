#ifndef BSP_SAF2_DIAG_UAPI_H
#define BSP_SAF2_DIAG_UAPI_H
#include <linux/types.h>
#include <linux/ioctl.h>
/* Diagnostic ABI, no arbitrary MMIO, HOME, clear-fault or motion commands. */
struct saf2_snapshot {
 __u32 version,profile,caps,features,config_valid,config_id[8];
 __u32 irq_pending,irq_mask,global_id,interlock_id,irq_events,config_accepted,config_applied;
 __u32 global[64],interlock[32];
};
struct saf2_config { __u32 txn,axes,feedback_us,watchdog_us; };
#define SAF2_SNAPSHOT _IOR('I',1,struct saf2_snapshot)
#define SAF2_CONFIG _IOW('I',2,struct saf2_config)
/* Opens a NEW PL owner without feeding. Explicit timeout experiment only. */
#define SAF2_TIMEOUT_TEST _IO('I',3)
#endif
