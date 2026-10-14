#include "rs485_telem.h"
#include <string.h>
static uint64_t le(const uint8_t *b,unsigned n) {
    uint64_t v=0;unsigned k;for(k=0;k<n;k++) v|=(uint64_t)b[k]<<(8*k);return v;
}
int rs485_telem_decode(const uint8_t b[RT_RECORD_BYTES],rs485_telem_record *o) {
    uint32_t c=RT_CRC_INIT,w[8];unsigned k,j;memset(o,0,sizeof(*o));
    if(le(b+RT_FRAME_MAGIC_OFFSET,RT_FRAME_MAGIC_SIZE)!=RT_RECORD_MAGIC ||
       le(b+RT_FRAME_VERSION_OFFSET,RT_FRAME_VERSION_SIZE)!=RT_RECORD_VERSION ||
       le(b+RT_FRAME_LENGTH_OFFSET,RT_FRAME_LENGTH_SIZE)!=RT_RECORD_BYTES) return RS485_SW_FORMAT;
    for(k=0;k<RT_CRC_BYTES;k++) {c^=b[k];for(j=0;j<8;j++) c=(c&1)?(c>>1)^RT_CRC_POLY:c>>1;}
    if((c^RT_CRC_XOROUT)!=(uint32_t)le(b+RT_FRAME_CRC_OFFSET,RT_FRAME_CRC_SIZE)) return RS485_SW_FORMAT;
    o->collector_generation=(uint32_t)le(b+RT_FRAME_COLLECTOR_GENERATION_OFFSET,RT_FRAME_COLLECTOR_GENERATION_SIZE);
    o->revision=(uint32_t)le(b+RT_FRAME_REVISION_OFFSET,RT_FRAME_REVISION_SIZE);
    o->transport_generation=(uint32_t)le(b+RT_FRAME_TRANSPORT_GENERATION_OFFSET,RT_FRAME_TRANSPORT_GENERATION_SIZE);
    o->completion_serial=le(b+RT_FRAME_SERIAL_OFFSET,RT_FRAME_SERIAL_SIZE);
    for(k=0;k<8;k++) w[k]=(uint32_t)le(b+RT_FRAME_RAW_OFFSET+4*k,4);
    return rs485_decode(w,&o->source);
}
static int wr(const rs485_io *io,uint32_t r,uint32_t v) {return io->write32(io->ctx,r,v)?RS485_SW_IO:0;}
int rs485_telem_arm(const rs485_io *io,uint32_t id,uint32_t gen,uint32_t size) {
    if(!id || !gen || size<RT_RECORD_BYTES || size>RT_RECORD_BYTES*RT_BATCH_MAX || size%RT_RECORD_BYTES) return RS485_SW_FORMAT;
    if(wr(io,RT_REG_ARM_ID,id) || wr(io,RT_REG_ARM_GEN,gen) || wr(io,RT_REG_ARM_BYTES,size)) return RS485_SW_IO;
    return wr(io,RT_REG_ARM,1);
}
int rs485_telem_complete(const rs485_io *io,uint32_t id,uint32_t gen,int failed) {
    if(!id || !gen || (failed!=0 && failed!=1)) return RS485_SW_FORMAT;
    if(wr(io,RT_REG_COMPLETE_ID,id) || wr(io,RT_REG_COMPLETE_GEN,gen) || wr(io,RT_REG_COMPLETE_RESULT,(uint32_t)failed)) return RS485_SW_IO;
    return wr(io,RT_REG_COMPLETE,1);
}
