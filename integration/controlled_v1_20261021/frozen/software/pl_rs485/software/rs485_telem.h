#ifndef RS485_TELEM_H
#define RS485_TELEM_H
#include "rs485_gp.h"
#include "../generated/telem_defs.h"
typedef struct {
    uint32_t collector_generation,revision,transport_generation;
    uint64_t completion_serial;
    rs485_decoded source;
} rs485_telem_record;
int rs485_telem_decode(const uint8_t bytes[RT_RECORD_BYTES],rs485_telem_record *out);
/* Callbacks are the same ordered, little-endian D32 API as the GP helper.
 * RX descriptor must have exact packet_bytes and be issued before this call.
 * A successful ARM write means permission to stream, not DDR completion. */
int rs485_telem_arm(const rs485_io *io,uint32_t packet_id,uint32_t generation,uint32_t packet_bytes);
/* Only after DMAengine success + exact received length, CRC/data checks and
 * persistence. On error follow isolated controller cancellation/quarantine. */
int rs485_telem_complete(const rs485_io *io,uint32_t packet_id,uint32_t generation,int failed);
#endif
