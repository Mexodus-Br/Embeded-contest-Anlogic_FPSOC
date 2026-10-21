"""Execute diagnostic formatting with wrapped device syscalls; no physical device."""
import json
from pathlib import Path
import subprocess
import argparse
H=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--tag',default='cli-format');a=p.parse_args()
assert a.tag.replace('-','').isalnum()
out=H/'evidence'/a.tag
out.mkdir(parents=True,exist_ok=False)
mock=r'''
#include <stdarg.h>
#include <string.h>
#include <stdint.h>
#include <assert.h>
#include "safety_uapi.h"
#include "generated/interlock_defs.h"
int __wrap_open(const char *path,int flags,...){(void)flags;assert(!strcmp(path,"/dev/bsp-saf2-diag"));return 77;}
int __wrap_close(int fd){assert(fd==77);return 0;}
int __wrap_ioctl(int fd,unsigned long request,...){
 va_list ap;struct saf2_snapshot *s;assert(fd==77 && request==SAF2_SNAPSHOT);
 va_start(ap,request);s=va_arg(ap,struct saf2_snapshot *);va_end(ap);memset(s,0,sizeof(*s));
 s->version=SI_VERSION;s->profile=SI_PROFILE;s->caps=SI_CAPS;s->features=SI_FEATURES;
 s->config_accepted=42;s->config_applied=41;
 s->interlock[SI_SNAP_TIME_LO]=3000000;s->interlock[SI_SNAP_OWNER_LO]=123;s->interlock[SI_SNAP_OWNER_HI]=0x10000000;
 s->interlock[SI_SNAP_LAST_SEQ_LO]=0xffffffff;s->interlock[SI_SNAP_LAST_SEQ_HI]=0xffffffff;
 s->interlock[SI_SNAP_STATUS]=SI_STATUS_POLL_RUN;s->interlock[SI_SNAP_SEEN_AXES]=3;
 s->interlock[SI_SNAP_FEEDBACK_US]=2000000;s->interlock[SI_SNAP_FEEDBACK_TIME_A0_LO]=2999900;
 s->interlock[SI_SNAP_FEEDBACK_TIME_A1_LO]=1000000;return 0;
}
'''
(out/'mock.c').write_text(mock)
subprocess.check_call(['gcc','-D_DEFAULT_SOURCE','-std=c11','-O2','-Wall','-Wextra','-Werror',
 '-I'+str(H/'safety'),str(H/'safety/saf2_diag.c'),str(out/'mock.c'),'-Wl,--wrap=open','-Wl,--wrap=close','-Wl,--wrap=ioctl','-o',str(out/'test')])
result=json.loads(subprocess.check_output([str(out/'test'),'snapshot']).decode())
assert result['production_home_approved'] is False
assert result['config_accepted']==42 and result['config_applied']==41
assert result['decoded']['owner_id']==str((0x10000000<<32)|123)
assert result['decoded']['last_sequence']==str(0xffffffffffffffff)
assert result['decoded']['feedback_age_us']==['100','2000000',None]
assert result['decoded']['feedback_fresh_by_age']==[True,False,False]
(out/'result.json').write_text(json.dumps({'passed':True,'physical_device_accessed':False,
 'checks':['u64 exact strings','expiry equality is stale','unseen feedback unknown',
           'production HOME qualification false','JSON decoding']},indent=2)+'\n')
print('PASS diagnostic JSON u64/age/boundary/unknown formatting; syscall mock only')
