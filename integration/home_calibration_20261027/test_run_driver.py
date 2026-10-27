"""Execute the actual additive RUN function against a rejecting MMIO model."""
from pathlib import Path
import subprocess
H=Path(__file__).resolve().parent
out=H/'artifacts/run-driver';out.mkdir(exist_ok=False)
s=(H/'software/telemetry/client/bsp_rs485.c').read_text()
function=s[s.index('static int set_run('):s.index('static int diag(')]
function=function[:function.index('static int diag(')] if 'static int diag(' in function else function
pre=r'''
#include <stdint.h>
#include <errno.h>
#include <assert.h>
#include <stdio.h>
#define GR(n) n
enum {RUN,GENERATION,CFG_REVISION,STATUS};
struct rs485_run {uint32_t run,generation,revision,busy;};
struct rs485_owner {int gp_lock;};
static uint32_t regs[4]={0,9,17,0};static unsigned writes;static int reject;
static void mutex_lock(int*p){(void)p;}static void mutex_unlock(int*p){(void)p;}
static uint32_t gr(struct rs485_owner*m,unsigned r){(void)m;return regs[r];}
static void gw(struct rs485_owner*m,unsigned r,uint32_t v){(void)m;writes++;if(!reject)regs[r]=v;}
'''
test=r'''
int main(void){struct rs485_owner m={0};struct rs485_run r={2,0,0,0};
assert(set_run(&m,&r)==-EINVAL&&writes==0);
r.run=1;assert(set_run(&m,&r)==0&&regs[RUN]==1&&r.generation==9&&r.revision==17);
reject=1;r.run=0;assert(set_run(&m,&r)==-EACCES&&regs[RUN]==1);
reject=0;assert(set_run(&m,&r)==0&&regs[RUN]==0);
puts("PASS typed RUN range, PL rejection readback, generation/revision and RUN-off");return 0;}
'''
(out/'test.c').write_text(pre+function+test)
subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror',str(out/'test.c'),'-o',str(out/'test.exe')],check=True)
subprocess.run([str(out/'test.exe')],check=True)
