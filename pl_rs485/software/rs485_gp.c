#include "rs485_gp.h"
#include <string.h>
static uint64_t bits(const uint32_t w[8],unsigned shift,unsigned width) {
    uint64_t v=0;
    unsigned i;
    for(i=0;i<width;i++) v|=(uint64_t)((w[(shift+i)/32]>>((shift+i)%32))&1u)<<i;
    return v;
}
static int64_t signed_bits(uint64_t v,unsigned width) {
    /* Avoid implementation-defined unsigned-to-signed conversion. */
    return (v & (UINT64_C(1)<<(width-1))) ?
      -(int64_t)((UINT64_C(1)<<width)-v):(int64_t)v;
}
int rs485_decode(const uint32_t w[8],rs485_decoded *o) {
    unsigned expected=0;
    memset(o,0,sizeof(*o));
#define GET(n) bits(w,RS_##n##_LSB,RS_##n##_WIDTH)
    o->version=(uint8_t)GET(VERSION);o->address=(uint8_t)GET(ADDRESS);
    o->query=(uint8_t)GET(QUERY);o->status=(uint8_t)GET(STATUS);
    o->attempt=(uint8_t)GET(ATTEMPT);o->length=(uint8_t)GET(LENGTH);
    o->sequence=(uint32_t)GET(SEQUENCE);o->request_us=GET(REQUEST_US);
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
        o->encoder_carry=(int32_t)signed_bits(o->payload>>16,32);
        o->encoder_value=(uint16_t)o->payload;break;
    case RS_QUERY_PULSES:o->signed_value=signed_bits(o->payload,32);break;
    case RS_QUERY_ERROR:o->signed_value=signed_bits(o->payload,16);break;
    default:o->enum_raw=(uint8_t)o->payload;o->enum_known=(o->enum_raw==1 || o->enum_raw==2);break;
    }
    return RS485_SW_OK;
}
static int rd(const rs485_io *io,uint32_t o,uint32_t *v) {return io->read32(io->ctx,o,v)?RS485_SW_IO:0;}
static int wr(const rs485_io *io,uint32_t o,uint32_t v) {return io->write32(io->ctx,o,v)?RS485_SW_IO:0;}
int rs485_identify(const rs485_io *io) {
    uint32_t v;
    if(rd(io,RG_REG_VERSION,&v)) return RS485_SW_IO;
    if(v!=RG_VERSION) return RS485_SW_FORMAT;
    if(rd(io,RG_REG_PROFILE,&v)) return RS485_SW_IO;
    if(v!=RG_PROFILE) return RS485_SW_FORMAT;
    if(rd(io,RG_REG_FEATURES,&v)) return RS485_SW_IO;
    return (v&RG_FEATURES)==RG_FEATURES?0:RS485_SW_FORMAT;
}
int rs485_submit(const rs485_io *io,uint32_t id,const uint32_t p[5],uint32_t mask) {
    unsigned k;
    if(!id || (mask&~RG_QUERY_VALID_MASK)) return RS485_SW_FORMAT;
    for(k=0;k<5;k++) if(wr(io,RG_REG_SHADOW_PERIOD0+4*k,p[k])) return RS485_SW_IO;
    if(wr(io,RG_REG_SHADOW_MASK,mask) || wr(io,RG_REG_TXN_ID,id)) return RS485_SW_IO;
    return wr(io,RG_REG_CFG_SUBMIT,1);
}
int rs485_capture_read(const rs485_io *io,rs485_capture *o) {
    unsigned k;uint32_t generation,after,id,state,level;
    if(rd(io,RG_REG_GENERATION,&generation) || rd(io,RG_REG_CAPTURE_STATUS,&state)) return RS485_SW_IO;
    if(!(state&RG_CAP_VALID_MASK)) {
        if(rd(io,RG_REG_FIFO_LEVEL,&level)) return RS485_SW_IO;
        if(!level) return RS485_SW_NOT_READY;
        if(wr(io,RG_REG_CAPTURE,1)) return RS485_SW_IO;
    }
    if(rd(io,RG_REG_CAPTURE_ID,&o->capture_id) || rd(io,RG_REG_CAPTURE_GENERATION,&o->generation) || rd(io,RG_REG_CAPTURE_REVISION,&o->revision)) return RS485_SW_IO;
    for(k=0;k<8;k++) if(rd(io,RG_REG_WORD0+4*k,&o->word[k])) return RS485_SW_IO;
    if(rd(io,RG_REG_GENERATION,&after) || rd(io,RG_REG_CAPTURE_ID,&id) || rd(io,RG_REG_CAPTURE_STATUS,&state)) return RS485_SW_IO;
    if(generation!=after || o->generation!=after || id!=o->capture_id || !(state&RG_CAP_VALID_MASK)) return RS485_SW_GENERATION;
    return 0;
}
int rs485_consume(const rs485_io *io,const rs485_capture *o) {
    uint32_t gen;
    if(rd(io,RG_REG_GENERATION,&gen)) return RS485_SW_IO;
    if(gen!=o->generation) return RS485_SW_GENERATION;
    return wr(io,RG_REG_CONSUME_ID,o->capture_id);
}
int rs485_snapshot(const rs485_io *io,uint32_t id,uint32_t w[RG_SNAPSHOT_WORDS]) {
    unsigned k;uint32_t gen,after,got,valid;
    if(!id) return RS485_SW_FORMAT;
    if(rd(io,RG_REG_GENERATION,&gen) || wr(io,RG_REG_SNAP_REQ_ID,id) || wr(io,RG_REG_SNAP_SUBMIT,1)) return RS485_SW_IO;
    for(k=0;k<RG_SNAPSHOT_WORDS;k++) if(rd(io,RG_SNAPSHOT_BASE+4*k,&w[k])) return RS485_SW_IO;
    if(rd(io,RG_REG_GENERATION,&after) || rd(io,RG_REG_SNAP_ID,&got) || rd(io,RG_REG_SNAP_STATUS,&valid)) return RS485_SW_IO;
    return gen==after && w[RG_SNAP_GENERATION]==gen && got==id && valid?0:RS485_SW_GENERATION;
}
