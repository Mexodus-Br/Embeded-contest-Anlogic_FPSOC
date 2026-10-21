#include <stdio.h>
#include <limits.h>
#include "mot2_codec.h"
int main(void) {uint8_t b[72];int64_t p[4]={INT64_MIN,INT64_MAX,-123456789012345LL,0};mot_encode(b,0xfedcba9876543210ULL,0x76543210,123456,p,1);return fwrite(b,1,72,stdout)==72?0:1;}
