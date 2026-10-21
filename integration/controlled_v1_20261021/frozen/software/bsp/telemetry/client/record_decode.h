#include <linux/string.h>
#include "generated/rs485_defs.h"
#define RS485_SW_FORMAT (-EBADMSG)
#define RS485_SW_OK 0
typedef struct {
    u8 version,address,query,status,attempt,length;
    u32 sequence;
    u64 request_us,event_us,payload;
    int data_valid,enum_known;
    s64 signed_value; /* query33 signed pulses; query39 signed error counts */
    s32 encoder_carry;
    u16 encoder_value; /* query30, 65536 counts/turn, carry kept separate */
    u8 enum_raw; /* query3A / 3E: 1 and 2 known, other values retained */
} rs485_decoded;
static u64 bits(const u32 w[8],unsigned shift,unsigned width) {
    u64 v=0;
    unsigned i;
    for(i=0;i<width;i++) v|=(u64)((w[(shift+i)/32]>>((shift+i)%32))&1u)<<i;
    return v;
}
static s64 signed_bits(u64 v,unsigned width) {
    /* Avoid implementation-defined unsigned-to-signed conversion. */
    return (v & (UINT64_C(1)<<(width-1))) ?
      -(s64)((UINT64_C(1)<<width)-v):(s64)v;
}
static int rs485_decode(const u32 w[8],rs485_decoded *o) {
    unsigned expected=0;
    memset(o,0,sizeof(*o));
#define GET(n) bits(w,RS_##n##_LSB,RS_##n##_WIDTH)
    o->version=(u8)GET(VERSION);o->address=(u8)GET(ADDRESS);
    o->query=(u8)GET(QUERY);o->status=(u8)GET(STATUS);
    o->attempt=(u8)GET(ATTEMPT);o->length=(u8)GET(LENGTH);
    o->sequence=(u32)GET(SEQUENCE);o->request_us=GET(REQUEST_US);
    o->event_us=GET(EVENT_US);o->payload=GET(PAYLOAD);
#undef GET
    if(o->version!=RS_VERSION) return RS485_SW_FORMAT;
    /* Unknown status is preserved, never interpreted as zero feedback. */
    if(o->status!=RS_STATUS_VALID) {
        if(o->length!=0 || o->payload!=0) return RS485_SW_FORMAT;
        return RS485_SW_OK;
    }
    switch(o->query) {
    case RS_QUERY_ENCODER:expected=RS_LENGTH_ENCODER;break;
    case RS_QUERY_PULSES:expected=RS_LENGTH_PULSES;break;
    case RS_QUERY_ERROR:expected=RS_LENGTH_ERROR;break;
    case RS_QUERY_ENABLE:expected=RS_LENGTH_ENABLE;break;
    case RS_QUERY_PROTECT:expected=RS_LENGTH_PROTECT;break;
    default:return RS485_SW_FORMAT;
    }
    if(o->length!=expected || (expected<6 && (o->payload>>(expected*8))!=0)) return RS485_SW_FORMAT;
    o->data_valid=1;
    switch(o->query) {
    case RS_QUERY_ENCODER:
        o->encoder_carry=(s32)signed_bits(o->payload>>16,32);
        o->encoder_value=(u16)o->payload;break;
    case RS_QUERY_PULSES:o->signed_value=signed_bits(o->payload,32);break;
    case RS_QUERY_ERROR:o->signed_value=signed_bits(o->payload,16);break;
    default:o->enum_raw=(u8)o->payload;o->enum_known=(o->enum_raw==1 || o->enum_raw==2);break;
    }
    return RS485_SW_OK;
}
