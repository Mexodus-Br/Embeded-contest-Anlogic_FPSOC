#ifndef RS485_GP_H
#define RS485_GP_H
#include "../generated/gp_defs.h"
#include "../generated/rs485_defs.h"
#include <stddef.h>
#include <stdint.h>
/* All access is serialized by the caller. Offsets, not physical pointers.
 * BSP callbacks must use ordered, little-endian D32 MMIO and propagate errors. */
typedef struct {
    void *ctx;
    int (*read32)(void *, uint32_t, uint32_t *);
    int (*write32)(void *, uint32_t, uint32_t);
} rs485_io;
typedef struct {
    uint32_t word[8], capture_id, generation, revision;
} rs485_capture;
typedef struct {
    uint8_t version,address,query,status,attempt,length;
    uint32_t sequence;
    uint64_t request_us,event_us,payload;
    int data_valid,enum_known;
    int64_t signed_value; /* query33 signed pulses; query39 signed error counts */
    int32_t encoder_carry;
    uint16_t encoder_value; /* query30, 65536 counts/turn, carry kept separate */
    uint8_t enum_raw; /* query3A / 3E: 1 and 2 known, other values retained */
} rs485_decoded;
enum { RS485_SW_OK=0, RS485_SW_IO=-1, RS485_SW_FORMAT=-2,
       RS485_SW_GENERATION=-3, RS485_SW_NOT_READY=-4 };
int rs485_decode(const uint32_t word[8],rs485_decoded *out);
int rs485_identify(const rs485_io *io);
int rs485_submit(const rs485_io *io,uint32_t id,const uint32_t periods[5],uint32_t mask);
/* submit OK means accepted write only. Poll CFG_STATE with a caller deadline;
 * check CFG_TXN/id and CFG_GENERATION before interpreting APPLIED/REJECTED. */
int rs485_capture_read(const rs485_io *io,rs485_capture *out);
int rs485_consume(const rs485_io *io,const rs485_capture *record);
int rs485_snapshot(const rs485_io *io,uint32_t id,uint32_t words[RG_SNAPSHOT_WORDS]);
#endif
