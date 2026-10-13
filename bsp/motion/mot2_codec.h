#ifndef BSP_MOT2_CODEC_H
#define BSP_MOT2_CODEC_H
#include <stdint.h>
#include <string.h>
#include "generated/interface_defs.h"
#define F(x) PLI_MOTION_STREAM_V2_##x
static void mot_put(uint8_t *p,uint64_t v,unsigned n) { unsigned i;for(i=0;i<n;i++) p[i]=(uint8_t)(v>>(8*i)); }
static uint32_t mot_crc(const uint8_t *p,unsigned n) { uint32_t c=~0u;unsigned i,j;for(i=0;i<n;i++) {c^=p[i];for(j=0;j<8;j++) c=(c>>1)^((c&1)?PLI_MOTION_GP_MOTION_V1_CRC_REFLECTED_POLYNOMIAL:0);}return ~c; }
static void mot_encode(uint8_t p[72],uint64_t session,uint32_t seq,uint64_t ticks,const int64_t pos[4],int end)
{
 unsigned i;memset(p,0,F(LENGTH));
 mot_put(p+F(MAGIC_OFFSET),F(MAGIC_VALUE),F(MAGIC_SIZE));
 mot_put(p+F(VERSION_OFFSET),F(VERSION_VALUE),F(VERSION_SIZE));
 mot_put(p+F(LENGTH_OFFSET),F(LENGTH_VALUE),F(LENGTH_SIZE));
 mot_put(p+F(SESSION_ID_OFFSET),session,F(SESSION_ID_SIZE));
 mot_put(p+F(SEQUENCE_OFFSET),seq,F(SEQUENCE_SIZE));
 mot_put(p+F(FLAGS_OFFSET),end?1:0,F(FLAGS_SIZE));
 mot_put(p+F(AXIS_MASK_OFFSET),15,F(AXIS_MASK_SIZE));
 mot_put(p+F(DURATION_TICK_OFFSET),ticks,F(DURATION_TICK_SIZE));
 for(i=0;i<4;i++) mot_put(p+F(TARGET0_OFFSET)+i*F(TARGET0_SIZE),(uint64_t)pos[i],F(TARGET0_SIZE));
 mot_put(p+F(CRC_OFFSET),mot_crc(p,F(CRC_OFFSET)),F(CRC_SIZE));
}
#endif
