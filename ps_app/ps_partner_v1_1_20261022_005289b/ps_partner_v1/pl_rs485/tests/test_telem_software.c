#include "../software/rs485_telem.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
int main(int argc,char **argv) {
    FILE *f;char hex[130];uint8_t b[64];unsigned x,k,frames=0,valid=0,errors=0;
    rs485_telem_record r;
    assert(argc==2);f=fopen(argv[1],"r");assert(f);
    while(fscanf(f,"%128s",hex)==1) {
        for(k=0;k<64;k++) {assert(sscanf(hex+2*(63-k),"%2x",&x)==1);b[k]=(uint8_t)x;}
        assert(rs485_telem_decode(b,&r)==0);
        assert(r.collector_generation==0 && r.revision>=2);
        assert(r.transport_generation==(frames<16?1u:2u));
        if(r.source.data_valid) {
            valid++;
            switch(r.source.query) {
            case RS_QUERY_ENCODER:assert(r.source.encoder_carry==-1 && r.source.encoder_value==32768);break;
            case RS_QUERY_PULSES:assert(r.source.signed_value==(frames<16?INT32_MIN:INT32_MAX));break;
            case RS_QUERY_ERROR:assert(r.source.signed_value==-32768);break;
            case RS_QUERY_ENABLE:assert(r.source.enum_raw==2 && r.source.enum_known);break;
            case RS_QUERY_PROTECT:assert(r.source.enum_raw==128 && !r.source.enum_known);break;
            default:assert(0);
            }
        } else {errors++;assert(r.source.status==RS_STATUS_TIMEOUT && r.source.length==0);}
        /* Every byte, including metadata and raw fields, is protected. */
        for(k=0;k<64;k++) {b[k]^=1;assert(rs485_telem_decode(b,&r)==RS485_SW_FORMAT);b[k]^=1;}
        frames++;
    }
    fclose(f);assert(frames==17 && valid==16 && errors==1);
    printf("PASS C/RTL telemetry cross-check frames=%u valid=%u errors=%u; 1088 single-byte corruptions rejected\n",frames,valid,errors);
    return 0;
}
