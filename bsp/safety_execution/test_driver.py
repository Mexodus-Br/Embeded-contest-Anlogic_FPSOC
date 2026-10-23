"""Compile actual execution ioctl/open/release C functions against a register model.
No kernel/AXI timing or DDR proof is claimed. Linux ABI is cross-compiled separately.
"""
from pathlib import Path
import subprocess,sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'ps_app/tools'))
from partner_support import compile_sources,compiler,OUT
root=Path(__file__).resolve().parents[2]
out=OUT/'safety-execution';out.mkdir(parents=True,exist_ok=True)
s=(root/'bsp/safety_execution/bsp_saf2_exec.c').read_text()
functions=s[s.index('static u32 rd('):s.index('static const struct file_operations ops=')].replace('unsigned long arg','uintptr_t arg')
defines=''
for name in ['safety_defs.h','interlock_defs.h']:
    defines+='\n'+(root/'integration/controlled_v1_20261021/safety/generated'/name).read_text().replace('#include <linux/types.h>','')
for f in ['integration/controlled_v1_20261021/safety/safety_uapi.h','bsp/safety_execution/execution_uapi.h']:
    defines+='\n'+'\n'.join(line for line in (root/f).read_text().splitlines() if not line.startswith('#include'))
pre=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <assert.h>
typedef uint32_t __u32;typedef uint64_t __u64;typedef uint32_t u32;typedef uint64_t u64;
#define _IOR(c,n,s) (((c)<<8)|(n))
#define _IOW(c,n,s) _IOR(c,n,s)
#define _IOWR(c,n,s) _IOR(c,n,s)
#define _IO(c,n) (((c)<<8)|(n))
#define U32_MAX UINT32_MAX
#ifndef ESTALE
#define ESTALE 116
#endif
#define spin_lock_irqsave(p,f) do {(void)(p);(f)=0;}while(0)
#define spin_unlock_irqrestore(p,f) do {(void)(p);(void)(f);}while(0)
#define __user
#define __iomem
#define CAP_SYS_RAWIO 1
#define IRQ_NONE 0
#define IRQ_HANDLED 1
typedef int irqreturn_t;
struct miscdevice {int unused;};struct inode {int unused;};
struct file {void *private_data;};
static bool admin=true,copyfail=false,reject_feed=false,reject_open=false;
static unsigned checks=0,writes=0,lock_calls=0;
#define CHECK(x) do {++checks;if(!(x)){fprintf(stderr,"check %u line %u failed\n",checks,__LINE__);return 1;}}while(0)
#define atomic_read(p) (*(p))
#define atomic_inc(p) (++*(p))
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
static int capable(int unused){(void)unused;return admin;}
static void mutex_lock(int *p){(void)p;++lock_calls;}
static void mutex_unlock(int *p){(void)p;}
static int copy_to_user(void *a,const void*b,size_t n){if(copyfail)return 1;memcpy(a,b,n);return 0;}
static int copy_from_user(void *a,const void*b,size_t n){memcpy(a,b,n);return 0;}
static u32 regs[1024];
static u32 readl(const void *p){return *(const u32 *)p;}
#define readl_poll_timeout(addr,v,c,d,t) ((v)=readl(addr),(c)?0:-ETIMEDOUT)
'''
wr=r'''
struct diag {void *base;struct miscdevice misc;int lock;bool opened,cancelled_owner;int command_lock;u64 owner,sequence;u32 txn;int irq_events;};
static void writel(u32 v,void *p){unsigned off=(char*)p-(char*)regs;regs[off/4]=v;++writes;
 if(off==SAF_REGISTERS_SNAP_REQ)regs[SAF_SNAPSHOT_BASE/4+SAF_SNAPSHOT_SNAP_ID]=v;
 if(off==SI_REG_SNAP_REQ)regs[SI_REG_SNAP_ID/4]=v;
 if(off==SI_REG_OWNER_OPEN&&!reject_open){regs[SI_REG_OWNER_LO/4]++;regs[SI_REG_STATUS/4]|=SI_STATUS_OWNER_ACTIVE;}
 if(off==SI_REG_OWNER_CLOSE)regs[SI_REG_STATUS/4]&=~SI_STATUS_OWNER_ACTIVE;
 if(off==SI_REG_HEARTBEAT_COMMIT&&!reject_feed){regs[SI_REG_LAST_SEQ_LO/4]=regs[SI_REG_HEARTBEAT_SEQ_LO/4];regs[SI_REG_LAST_SEQ_HI/4]=regs[SI_REG_HEARTBEAT_SEQ_HI/4];regs[SI_REG_STATUS/4]|=SI_STATUS_HEARTBEAT_QUALIFIED;}
 if(off==SAF_REGISTERS_SUBMIT){regs[SAF_REGISTERS_ACK_ID/4]=regs[SAF_REGISTERS_TXN/4];regs[SAF_REGISTERS_ACK_STATUS/4]=7;regs[SAF_REGISTERS_ACK_ERROR/4]=regs[SAF_REGISTERS_ARG/4]?1:0;}
}
'''
test=r'''
int main(void){struct diag d={.base=regs};struct file f={.private_data=&d};struct saf2_owner o={0},bad={0};struct saf2_action a={.txn=1};struct saf2_snapshot snap={0};unsigned before;
 regs[SAF_REGISTERS_VERSION/4]=SI_VERSION;regs[SAF_REGISTERS_PROFILE/4]=SI_PROFILE;regs[SAF_REGISTERS_CAPS/4]=SI_CAPS;regs[SAF_REGISTERS_FEATURES/4]=SI_FEATURES;regs[SI_REG_STATUS/4]=SI_STATUS_DRAINED;
 CHECK(control(&f,SAF2_SNAPSHOT,(unsigned long long)&snap)==0);CHECK(snap.profile==SI_PROFILE);
 regs[SI_REG_STATUS/4]|=SI_STATUS_OWNER_ACTIVE;before=writes;CHECK(control(&f,SAF2_OWNER_OPEN,(unsigned long long)&o)==-EBUSY);CHECK(writes==before);regs[SI_REG_STATUS/4]&=~SI_STATUS_OWNER_ACTIVE;
 CHECK(control(&f,SAF2_OWNER_OPEN,(unsigned long long)&o)==0);CHECK(o.id&&o.sequence==0);CHECK(!regs[SI_REG_LAST_SEQ_LO/4]);
 o.sequence=1;CHECK(control(&f,SAF2_OWNER_FEED,(unsigned long long)&o)==0);before=writes;CHECK(control(&f,SAF2_OWNER_FEED,(unsigned long long)&o)==-ESTALE);CHECK(writes==before);
 bad=o;bad.id++;bad.sequence++;CHECK(control(&f,SAF2_OWNER_FEED,(unsigned long long)&bad)==-ESTALE);
 reject_feed=true;o.sequence=2;CHECK(control(&f,SAF2_OWNER_FEED,(unsigned long long)&o)==-EIO);reject_feed=false;CHECK(control(&f,SAF2_OWNER_FEED,(unsigned long long)&o)==-ESTALE);o.sequence=3;CHECK(control(&f,SAF2_OWNER_FEED,(unsigned long long)&o)==0);
 CHECK(control(&f,SAF2_HOME,(unsigned long long)&a)==0);CHECK(regs[SAF_REGISTERS_OPCODE/4]==SAF_COMMANDS_HOME_START);CHECK(regs[SAF_REGISTERS_ARG/4]==0);CHECK(control(&f,SAF2_HOME,(unsigned long long)&a)==-EBUSY);
 a.txn=2;CHECK(control(&f,SAF2_CLEAR,(unsigned long long)&a)==0);CHECK(regs[SAF_REGISTERS_OPCODE/4]==SAF_COMMANDS_CLEAR_FAULT);CHECK(control(&f,SAF2_ACK,(unsigned long long)&a)==0);CHECK(a.ack_id==2&&!a.ack_error);
 before=lock_calls;CHECK(control(&f,SAF2_STOP,0)==0);CHECK(lock_calls==before);CHECK(regs[SAF_REGISTERS_STOP/4]==1);
 a.txn=3;before=writes;CHECK(control(&f,SAF2_HOME,(unsigned long long)&a)==-ECANCELED);CHECK(writes==before);
 admin=false;before=writes;CHECK(control(&f,SAF2_STOP,0)==-EPERM);CHECK(writes==before);admin=true;
 CHECK(control(&f,0xffffffff,0)==-ENOTTY);
 /* Closing a software fd neither closes nor adopts PL owner. */
 CHECK(close_diag(NULL,&f)==0);CHECK(!d.owner&&(regs[SI_REG_STATUS/4]&SI_STATUS_OWNER_ACTIVE));before=writes;o.sequence=4;CHECK(control(&f,SAF2_OWNER_FEED,(unsigned long long)&o)==-ESTALE);CHECK(writes==before);
 regs[SI_REG_STATUS/4]&=~SI_STATUS_OWNER_ACTIVE;CHECK(control(&f,SAF2_OWNER_OPEN,(unsigned long long)&o)==0);CHECK(control(&f,SAF2_OWNER_CLOSE,(unsigned long long)&o)==0);CHECK(!d.owner);
 CHECK(control(&f,SAF2_OWNER_OPEN,(unsigned long long)&o)==0);regs[SI_REG_STATUS/4]&=~SI_STATUS_OWNER_ACTIVE;
 CHECK(control(&f,SAF2_OWNER_OPEN,(unsigned long long)&bad)==0);CHECK(bad.id!=o.id);CHECK(d.sequence==0);
 printf("PASS %u actual safety execution driver checks\n",checks);return 0;}
'''
p=out/'actual-driver.c';p.write_text(pre+defines+wr+functions+test,encoding='utf-8');exe=out/'actual-driver.exe'
compile_sources([p],exe,compiler(),cxx=False,extra=['-Wno-pointer-to-int-cast','-Wno-int-to-pointer-cast'])
r=subprocess.run([str(exe)],capture_output=True,text=True);print(r.stdout+r.stderr)
(OUT/'safety_execution_report.json').write_text(json.dumps({'exit_code':r.returncode,'passed':r.returncode==0,'scope':'actual_C_functions_register_model_not_kernel','output':r.stdout+r.stderr},indent=2));raise SystemExit(r.returncode)
