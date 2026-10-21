/* Explicit byte access; no packed structs, ABI padding or endian assumptions. */
#ifndef PLI_REFERENCE_CODEC_H
#define PLI_REFERENCE_CODEC_H
#include <stdint.h>
#include <stddef.h>
#include "generated/interface_defs.h"
static inline uint64_t pli_get_le(const uint8_t *p, unsigned n) {
    uint64_t v=0; unsigned i; for(i=0;i<n;i++) v|=(uint64_t)p[i]<<(i*8); return v;
}
static inline void pli_put_le(uint8_t *p, unsigned n, uint64_t v) {
    unsigned i; for(i=0;i<n;i++) p[i]=(uint8_t)(v>>(i*8));
}
static inline int64_t pli_get_i64(const uint8_t *p) {
    uint64_t u=pli_get_le(p,8);
    return u<=INT64_MAX ? (int64_t)u : -1-(int64_t)(UINT64_MAX-u);
}
static inline uint32_t pli_crc32(const uint8_t *p,size_t n) {
    uint32_t c=UINT32_MAX; size_t i; unsigned j;
    for(i=0;i<n;i++) { c^=p[i]; for(j=0;j<8;j++) c=(c>>1)^((c&1)?UINT32_C(0xEDB88320):0); }
    return c^UINT32_MAX;
}
/* This helper checks envelope only; schema/semantic checks remain caller responsibility. */
static inline int pli_envelope(const uint8_t *p,size_t n,uint32_t magic,size_t expected) {
    return n==expected && n>=8 && pli_get_le(p,4)==magic && pli_get_le(p+4,2)==PLI_ABI_VERSION
        && pli_get_le(p+6,2)==n && pli_get_le(p+n-4,4)==pli_crc32(p,n-4);
}
#endif
