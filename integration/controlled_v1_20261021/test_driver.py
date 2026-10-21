"""Execute the actual diagnostic ioctl functions against a register model.

No substitute implementation: extract the C functions from the compiled driver.
This verifies software admission/readback only, not AXI or DDR hardware behavior.
"""
from pathlib import Path
import subprocess
import argparse

H=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--tag',default='driver-model');a=p.parse_args()
assert a.tag.replace('-','').isalnum()
out=H/'evidence'/a.tag
out.mkdir(parents=True,exist_ok=False)
source=(H/'safety/bsp_saf2_diag.c').read_text()
functions=source[source.index('static u32 rd('):source.index('static int open_diag(')]
pre=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <assert.h>
#include "safety_uapi.h"
#include "interlock_defs.h"
#include "safety_defs.h"
typedef uint32_t u32;
#define U32_MAX UINT32_MAX
#define __user
#define CAP_SYS_RAWIO 1
typedef int irqreturn_t;
#define IRQ_NONE 0
#define IRQ_HANDLED 1
struct diag { void *base;int lock,irq_events; };
#define atomic_read(p) (*(p))
#define atomic_inc(p) (++*(p))
struct file { void *private_data; };
static u32 regs[1024];static unsigned writes;static bool admin=true,reject_config=false,reject_owner=false;
static unsigned checks;
#define CHECK(x) do {checks++;assert(x);}while(0)
static int capable(int x){(void)x;return admin;}
static void mutex_lock(int *x){(void)x;}
static void mutex_unlock(int *x){(void)x;}
static int copy_to_user(void *a,const void *b,size_t n){memcpy(a,b,n);return 0;}
static int copy_from_user(void *a,const void *b,size_t n){memcpy(a,b,n);return 0;}
static u32 readl(const void *p){return *(const u32 *)p;}
static void writel(u32 v,void *p){
 unsigned off=(char *)p-(char *)regs;writes++;
 CHECK(off==SAF_REGISTERS_SNAP_REQ || off==SI_REG_SNAP_REQ ||
       off==SI_REG_SHADOW_AXES || off==SI_REG_SHADOW_FEEDBACK_US ||
       off==SI_REG_SHADOW_WATCHDOG_US || off==SI_REG_CONFIG_TXN ||
       off==SI_REG_CONFIG_COMMIT || off==SI_REG_OWNER_OPEN || off==SAF_REGISTERS_IRQ_MASK);
 regs[off/4]=v;
 if(off==SAF_REGISTERS_SNAP_REQ)regs[(SAF_SNAPSHOT_BASE/4)+SAF_SNAPSHOT_SNAP_ID]=v;
 if(off==SI_REG_SNAP_REQ)regs[SI_REG_SNAP_ID/4]=v;
 if(off==SI_REG_CONFIG_COMMIT && !reject_config){
  regs[SI_REG_CONFIG_ACCEPTED/4]=regs[SI_REG_CONFIG_TXN/4];regs[SI_REG_CONFIG_APPLIED/4]=regs[SI_REG_CONFIG_TXN/4];
  regs[SI_REG_ACTIVE_AXES/4]=regs[SI_REG_SHADOW_AXES/4];regs[SI_REG_ACTIVE_FEEDBACK_US/4]=regs[SI_REG_SHADOW_FEEDBACK_US/4];regs[SI_REG_ACTIVE_WATCHDOG_US/4]=regs[SI_REG_SHADOW_WATCHDOG_US/4];
 }
 if(off==SI_REG_OWNER_OPEN && !reject_owner){regs[SI_REG_OWNER_LO/4]=123;regs[SI_REG_STATUS/4]|=SI_STATUS_OWNER_ACTIVE;}
}
#define readl_poll_timeout(addr,v,condition,delay,timeout) ({(v)=readl(addr);(condition)?0:-ETIMEDOUT;})
'''
test=r'''
int main(void){
 struct diag d={regs,0,0};struct file f={&d};struct saf2_snapshot s;struct saf2_config c={1,7,1000000,3000000};unsigned before;
 regs[SAF_REGISTERS_VERSION/4]=SI_VERSION;regs[SAF_REGISTERS_PROFILE/4]=SI_PROFILE;
 regs[SAF_REGISTERS_CAPS/4]=SI_CAPS;regs[SAF_REGISTERS_FEATURES/4]=SI_FEATURES;
 CHECK(identify(&d)==0);before=writes;admin=false;CHECK(control(&f,SAF2_TIMEOUT_TEST,0)==-EPERM);CHECK(writes==before);admin=true;
 CHECK(diagnostic_irq(0,&d)==IRQ_NONE);regs[SAF_REGISTERS_IRQ_PENDING/4]=3;regs[SAF_REGISTERS_IRQ_MASK/4]=3;
 CHECK(diagnostic_irq(0,&d)==IRQ_HANDLED);CHECK(d.irq_events==1);CHECK(regs[SAF_REGISTERS_IRQ_MASK/4]==0);CHECK(regs[SAF_REGISTERS_IRQ_PENDING/4]==3);
 CHECK(control(&f,SAF2_SNAPSHOT,(unsigned long)&s)==0);CHECK(s.global_id==1 && s.interlock_id==1);
 CHECK(control(&f,SAF2_SNAPSHOT,(unsigned long)&s)==0);CHECK(s.global_id==2 && s.interlock_id==2);
 regs[SAF_REGISTERS_SNAP_REQ/4]=UINT32_MAX;CHECK(snapshot(&d,&s)==-EOVERFLOW);regs[SAF_REGISTERS_SNAP_REQ/4]=2;
 regs[SI_REG_SNAP_ID/4]=UINT32_MAX;CHECK(snapshot(&d,&s)==-EOVERFLOW);regs[SI_REG_SNAP_ID/4]=2;
 CHECK(control(&f,SAF2_CONFIG,(unsigned long)&c)==-EBUSY);regs[SI_REG_STATUS/4]=SI_STATUS_DRAINED;
 for(unsigned mask=0;mask<16;mask++){
  c.axes=mask;before=writes;
  if(mask==0 || mask>7){CHECK(control(&f,SAF2_CONFIG,(unsigned long)&c)==-EINVAL);CHECK(writes==before);}
 }
 c.axes=7;c.feedback_us=999999;CHECK(control(&f,SAF2_CONFIG,(unsigned long)&c)==-EINVAL);
 c.feedback_us=1000000;c.watchdog_us=3000001;CHECK(control(&f,SAF2_CONFIG,(unsigned long)&c)==-EINVAL);c.watchdog_us=3000000;
 for(unsigned i=0;i<3;i++){
  regs[SI_REG_STATUS/4]=SI_STATUS_DRAINED|(i==0?SI_STATUS_OWNER_ACTIVE:i==1?SI_STATUS_POLL_RUN:SI_STATUS_CONFIG_PENDING);
  before=writes;CHECK(control(&f,SAF2_CONFIG,(unsigned long)&c)==-EBUSY);CHECK(control(&f,SAF2_TIMEOUT_TEST,0)==-EBUSY);CHECK(writes==before);
 }
 regs[SI_REG_STATUS/4]=SI_STATUS_DRAINED;CHECK(control(&f,SAF2_CONFIG,(unsigned long)&c)==0);
 CHECK(snapshot(&d,&s)==0);CHECK(s.config_accepted==1 && s.config_applied==1);
 before=writes;CHECK(control(&f,SAF2_CONFIG,(unsigned long)&c)==-ESTALE);CHECK(writes==before);
 c.txn=2;reject_config=true;CHECK(control(&f,SAF2_CONFIG,(unsigned long)&c)==-EACCES);reject_config=false;
 regs[SI_REG_CAUSES/4]=SI_CAUSE_WATCHDOG;before=writes;CHECK(control(&f,SAF2_TIMEOUT_TEST,0)==-EBUSY);CHECK(writes==before);regs[SI_REG_CAUSES/4]=0;
 reject_owner=true;CHECK(control(&f,SAF2_TIMEOUT_TEST,0)==-EACCES);reject_owner=false;
 CHECK(control(&f,SAF2_TIMEOUT_TEST,0)==0);before=writes;CHECK(control(&f,SAF2_TIMEOUT_TEST,0)==-EBUSY);CHECK(writes==before);
 CHECK(control(&f,0,0)==-ENOTTY);
 regs[SAF_REGISTERS_CAPS/4]=0;before=writes;CHECK(control(&f,SAF2_SNAPSHOT,(unsigned long)&s)==-ENODEV);CHECK(writes==before);
 printf("PASS %u actual-driver admission/snapshot/readback checks; no heartbeat or motion writes\n",checks);return 0;
}
'''
(out/'model.c').write_text(pre+functions+test)
subprocess.check_call(['gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror',
    '-I'+str(H/'safety'),'-I'+str(H/'safety/generated'),str(out/'model.c'),'-o',str(out/'test')])
subprocess.check_call([str(out/'test')])
