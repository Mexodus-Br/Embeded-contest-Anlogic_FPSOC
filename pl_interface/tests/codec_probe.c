#include <stdio.h>
#include <string.h>
#include "reference_codec.h"
int main(int argc,char **argv) {
    uint8_t p[128]; unsigned x; size_t n=0,i; int c;
    if(pli_crc32((const uint8_t *)"123456789",9)!=UINT32_C(0xCBF43926)) return 5;
    if(argc!=2) return 2;
    while((c=getchar())!=EOF) {
        if(c=='\n'||c=='\r'||c==' ') continue;
        if(ungetc(c,stdin)==EOF || scanf("%2x",&x)!=1 || n==sizeof(p)) return 3;
        p[n++]=(uint8_t)x;
    }
    if(!strcmp(argv[1],"motion")) {
        if(!pli_envelope(p,n,PLI_MOTION_MAGIC_VALUE,PLI_MOTION_LENGTH)) return 4;
        printf("%lld %lld %lld %lld\n",
            (long long)pli_get_i64(p+PLI_MOTION_TARGET0_OFFSET),
            (long long)pli_get_i64(p+PLI_MOTION_TARGET1_OFFSET),
            (long long)pli_get_i64(p+PLI_MOTION_TARGET2_OFFSET),
            (long long)pli_get_i64(p+PLI_MOTION_TARGET3_OFFSET));
        /* Read and rewrite the signed boundary fields, using defined signed->unsigned conversion. */
        for(i=0;i<4;i++) {
            size_t o=PLI_MOTION_TARGET0_OFFSET+i*PLI_MOTION_TARGET0_SIZE;
            pli_put_le(p+o,8,(uint64_t)pli_get_i64(p+o));
        }
    } else {
        if(!pli_envelope(p,n,PLI_TELEMETRY_MAGIC_VALUE,PLI_TELEMETRY_LENGTH)) return 4;
        printf("%lld %lld %llu\n",(long long)pli_get_i64(p+PLI_TELEMETRY_COMMAND_POSITION_OFFSET),
               (long long)pli_get_i64(p+PLI_TELEMETRY_FEEDBACK_RAW_OFFSET),
               (unsigned long long)pli_get_le(p+PLI_TELEMETRY_EVENT_TICK_OFFSET,8));
    }
    pli_put_le(p+n-4,4,pli_crc32(p,n-4));
    for(i=0;i<n;i++) printf("%02x",p[i]);
    putchar('\n'); return 0;
}
