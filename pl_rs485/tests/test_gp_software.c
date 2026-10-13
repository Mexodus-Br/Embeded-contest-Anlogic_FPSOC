#include "../software/rs485_gp.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void set_bits(uint32_t w[8],unsigned shift,unsigned width,uint64_t v) {
    unsigned i;
    for(i=0;i<width;i++) {
        uint32_t bit=UINT32_C(1)<<((shift+i)%32);
        if((v>>i)&1) w[(shift+i)/32]|=bit;else w[(shift+i)/32]&=~bit;
    }
}
static void make_record(uint32_t w[8],unsigned q,unsigned len,uint64_t payload) {
    memset(w,0,32);
    set_bits(w,248,8,1);set_bits(w,240,8,0xe2);set_bits(w,232,8,q);
    set_bits(w,216,8,1);set_bits(w,208,8,len);set_bits(w,176,32,0xfffffffe);
    set_bits(w,112,64,UINT64_C(0x12345678fffffffe));set_bits(w,48,64,UINT64_C(0x1234567900000010));
    set_bits(w,0,48,payload);
}
typedef struct {
    uint32_t r[1024];unsigned reads,writes,consumes;int injected_reset;
} mock;
static int read32(void *context,uint32_t offset,uint32_t *value) {
    mock *m=context;
    if(offset%4 || offset>=4096) return -1;
    m->reads++;
    if(m->injected_reset && offset==RG_REG_WORD4) m->r[RG_REG_GENERATION/4]++;
    *value=m->r[offset/4];return 0;
}
static int write32(void *context,uint32_t offset,uint32_t value) {
    mock *m=context;
    if(offset%4 || offset>=4096) return -1;
    m->writes++;m->r[offset/4]=value;
    if(offset==RG_REG_CAPTURE) m->r[RG_REG_CAPTURE_STATUS/4]=1;
    if(offset==RG_REG_CONSUME_ID) m->consumes++;
    if(offset==RG_REG_SNAP_SUBMIT) {m->r[RG_REG_SNAP_STATUS/4]=1;m->r[RG_REG_SNAP_ID/4]=m->r[RG_REG_SNAP_REQ_ID/4];}
    return 0;
}
int main(void) {
    uint32_t w[8],snap[RG_SNAPSHOT_WORDS],p[5]={125000,500000,125000,1000000,1000000};
    rs485_decoded d;rs485_capture cap;
    mock m;rs485_io io={&m,read32,write32};unsigned i;
    make_record(w,RS_QUERY_ENCODER,6,UINT64_C(0xffffffff8000));
    assert(rs485_decode(w,&d)==0 && d.data_valid && d.encoder_carry==-1 && d.encoder_value==32768);
    assert(d.address==0xe2 && d.attempt==1 && d.sequence==0xfffffffe);
    assert(d.request_us==UINT64_C(0x12345678fffffffe) && d.event_us==UINT64_C(0x1234567900000010));
    make_record(w,RS_QUERY_PULSES,4,0x80000000);assert(rs485_decode(w,&d)==0 && d.signed_value==INT32_MIN);
    make_record(w,RS_QUERY_PULSES,4,0x7fffffff);assert(rs485_decode(w,&d)==0 && d.signed_value==INT32_MAX);
    make_record(w,RS_QUERY_ERROR,2,0xfffe);assert(rs485_decode(w,&d)==0 && d.signed_value==-2);
    make_record(w,RS_QUERY_PROTECT,1,1);assert(rs485_decode(w,&d)==0 && d.enum_known && d.enum_raw==1);
    make_record(w,RS_QUERY_ENABLE,1,0x80);assert(rs485_decode(w,&d)==0 && d.data_valid && !d.enum_known && d.enum_raw==0x80);
    make_record(w,RS_QUERY_ENABLE,0,0);set_bits(w,224,8,RS_STATUS_TIMEOUT);
    assert(rs485_decode(w,&d)==0 && !d.data_valid && d.status==RS_STATUS_TIMEOUT);
    set_bits(w,224,8,0xfa);assert(rs485_decode(w,&d)==0 && !d.data_valid && d.status==0xfa);
    set_bits(w,0,48,1);assert(rs485_decode(w,&d)==RS485_SW_FORMAT && !d.data_valid);
    make_record(w,RS_QUERY_ERROR,4,0xfffe);assert(rs485_decode(w,&d)==RS485_SW_FORMAT);
    make_record(w,RS_QUERY_ERROR,2,0x1fffe);assert(rs485_decode(w,&d)==RS485_SW_FORMAT);
    make_record(w,RS_QUERY_ERROR,2,0xfffe);set_bits(w,248,8,2);assert(rs485_decode(w,&d)==RS485_SW_FORMAT);
    memset(&m,0,sizeof(m));m.r[RG_REG_VERSION/4]=RG_VERSION;m.r[RG_REG_PROFILE/4]=RG_PROFILE;m.r[RG_REG_FEATURES/4]=RG_FEATURES;
    assert(rs485_identify(&io)==0);m.r[RG_REG_PROFILE/4]=0;assert(rs485_identify(&io)==RS485_SW_FORMAT);m.r[RG_REG_PROFILE/4]=RG_PROFILE;
    assert(rs485_submit(&io,10,p,31)==0);assert(m.r[RG_REG_TXN_ID/4]==10 && m.r[RG_REG_CFG_SUBMIT/4]==1);
    for(i=0;i<5;i++) assert(m.r[(RG_REG_SHADOW_PERIOD0+4*i)/4]==p[i]);
    assert(rs485_submit(&io,0,p,31)==RS485_SW_FORMAT);
    assert(rs485_capture_read(&io,&cap)==RS485_SW_NOT_READY);
    m.r[RG_REG_GENERATION/4]=7;m.r[RG_REG_FIFO_LEVEL/4]=1;m.r[RG_REG_CAPTURE_ID/4]=42;m.r[RG_REG_CAPTURE_GENERATION/4]=7;m.r[RG_REG_CAPTURE_REVISION/4]=2;
    make_record(w,RS_QUERY_ERROR,2,0xfffe);for(i=0;i<8;i++) m.r[(RG_REG_WORD0+4*i)/4]=w[i];
    assert(rs485_capture_read(&io,&cap)==0 && cap.capture_id==42 && cap.generation==7 && cap.revision==2);
    assert(!memcmp(w,cap.word,32) && m.consumes==0);
    assert(rs485_consume(&io,&cap)==0 && m.consumes==1);
    m.injected_reset=1;assert(rs485_capture_read(&io,&cap)==RS485_SW_GENERATION);
    assert(rs485_consume(&io,&cap)==RS485_SW_GENERATION && m.consumes==1);m.injected_reset=0;
    m.r[(RG_SNAPSHOT_BASE+RG_SNAP_GENERATION*4)/4]=m.r[RG_REG_GENERATION/4];
    assert(rs485_snapshot(&io,123,snap)==0 && snap[RG_SNAP_GENERATION]==m.r[RG_REG_GENERATION/4]);
    printf("PASS GP software signed BE payload/unknown/status/generation/mock reads=%u writes=%u\n",m.reads,m.writes);
    return 0;
}
