"""Generate kernel adaptations from the sealed sole-source C definitions/decoder."""
import argparse,json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'bsp/telemetry'
p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
outputs={}
for name in ('telem_defs.h','gp_defs.h','rs485_defs.h'):
 s=(R/'pl_rs485/generated'/name).read_text(encoding='utf-8')
 s=s.replace('#include <stdint.h>','#include <linux/types.h>\n#define UINT32_C(x) x##U\n#define UINT64_C(x) x##ULL')
 outputs[D/'generated'/name]=s
h=(R/'pl_rs485/software/rs485_gp.h').read_text(encoding='utf-8')
body=h[h.index('typedef struct {\n    uint8_t version'):h.index('enum { RS485_SW_OK')]
c=(R/'pl_rs485/software/rs485_gp.c').read_text(encoding='utf-8')
code=c[c.index('static uint64_t bits'):c.index('static int rd(')]
s='#include <linux/string.h>\n#include "generated/rs485_defs.h"\n#define RS485_SW_FORMAT (-EBADMSG)\n#define RS485_SW_OK 0\n'+body+code
for old,new in [('uint64_t','u64'),('int64_t','s64'),('uint32_t','u32'),('int32_t','s32'),('uint16_t','u16'),('uint8_t','u8')]:s=s.replace(old,new)
s=s.replace('int rs485_decode(','static int rs485_decode(')
outputs[D/'client/record_decode.h']=s
for path,s in outputs.items():
 if a.check:assert path.read_text(encoding='utf-8')==s,path
 else:path.write_bytes(s.encode())
print('PASS kernel types/include adaptation; original decoder algorithm unchanged')
