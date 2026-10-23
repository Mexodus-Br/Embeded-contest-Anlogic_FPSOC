#ifndef BSP_SAF2_EXEC_UAPI_H
#define BSP_SAF2_EXEC_UAPI_H
#include "../../integration/controlled_v1_20261021/safety/safety_uapi.h"
/* Additive ABI. All values fixed width; no offsets, pointers or arbitrary MMIO. */
struct saf2_owner { __u64 id, sequence; };
struct saf2_action { __u32 txn, ack_id, ack_status, ack_error; };
#define SAF2_OWNER_OPEN _IOR('J',1,struct saf2_owner)
#define SAF2_OWNER_FEED _IOW('J',2,struct saf2_owner)
#define SAF2_OWNER_CLOSE _IOW('J',3,struct saf2_owner)
#define SAF2_STOP _IO('J',4)
#define SAF2_CLEAR _IOWR('J',5,struct saf2_action)
#define SAF2_HOME _IOWR('J',6,struct saf2_action)
#define SAF2_ACK _IOR('J',7,struct saf2_action)
#endif
