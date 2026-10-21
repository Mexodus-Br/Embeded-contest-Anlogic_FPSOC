"""Actual adapted configuration function and identity expression, no fake hardware pass."""
from pathlib import Path
import re
import subprocess
import argparse
H=Path(__file__).resolve().parent
S=H/'frozen/software'
p=argparse.ArgumentParser();p.add_argument('--tag',default='r5s2-software');a=p.parse_args()
assert a.tag.replace('-','').isalnum()
out=H/'evidence'/a.tag
out.mkdir(parents=True,exist_ok=False)
s=(S/'bsp/telemetry/client/bsp_rs485.c').read_text()
function=s[s.index('static int config('):s.index('static int snapshot(')]
identity=re.search(r'if\((gr\(m,GR\(VERSION\)\).*?)\)return -ENODEV;',s).group(1)
observation=s[s.index('static ssize_t integration_state_show('):s.index('static DEVICE_ATTR_RO(integration_state)')]
pre=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdarg.h>
#include <assert.h>
#include <errno.h>
#include <limits.h>
#include <sys/types.h>
#include "rs485_uapi.h"
#undef UINT32_C
#undef UINT64_C
#include "generated/gp_defs.h"
#include "generated/telem_defs.h"
#include "generated/interlock_defs.h"
typedef uint32_t u32;typedef uint64_t u64;
#define U32_MAX UINT32_MAX
#define GR(x) RG_REG_##x
#define RR(x) RT_REG_##x
struct rs485_owner {
 void *gp;int gp_lock,life;u32 txn,generation,packet_id,bytes,actual,status;
 void *buffer;bool blocked,owned,quarantine,dma_done,drain_validated;
};
struct device {struct rs485_owner *data;};struct device_attribute {int unused;};
static void *dev_get_drvdata(struct device *d){return d->data;}
#define sysfs_emit(buf,...) snprintf(buf,4096,__VA_ARGS__)
static u32 gp[1024],telem[1024];static unsigned writes,reads,checks;
static bool reject_run,change_gen,timeout_cfg;
#define CHECK(x) do {checks++;assert(x);}while(0)
static void mutex_lock(int *p){(void)p;}static void mutex_unlock(int *p){(void)p;}
static u32 gr(struct rs485_owner *m,u32 off){(void)m;reads++;return gp[off/4];}
static u32 tr(struct rs485_owner *m,u32 off){(void)m;reads++;return telem[off/4];}
static void gw(struct rs485_owner *m,u32 off,u32 v){(void)m;writes++;
 if(off==GR(RUN) && reject_run)return;
 gp[off/4]=v;
 if(off==GR(CFG_SUBMIT)){
  gp[GR(CFG_STATE)/4]=timeout_cfg?0:RG_CFG_APPLIED;
  gp[GR(CFG_TXN)/4]=gp[GR(TXN_ID)/4];
  if(change_gen)gp[GR(GENERATION)/4]++;
 }
}
#define readl_poll_timeout(addr,v,condition,delay,timeout) ({(v)=*(u32 *)(addr);(condition)?0:-ETIMEDOUT;})
'''
test=r'''
int main(void){
 struct rs485_owner m={.gp=gp};struct rs485_config c={.periods={1000,0,2000,0,3000},.mask=31,.run=0};
 struct device dev={&m};struct device_attribute attr={0};char buf[4096];unsigned before;
 gp[GR(VERSION)/4]=SI_COLLECTOR_VERSION;gp[GR(PROFILE)/4]=SI_COLLECTOR_PROFILE;
 gp[GR(CAPS)/4]=SI_COLLECTOR_CAPS;gp[GR(FEATURES)/4]=SI_COLLECTOR_FEATURES;
 telem[RR(VERSION)/4]=RT_VERSION;telem[RR(PROFILE)/4]=RT_PROFILE;telem[RR(CAPS)/4]=RT_CAPS;telem[RR(FEATURES)/4]=RT_FEATURES;
 CHECK(identity(&m)==0);gp[GR(PROFILE)/4]=RG_PROFILE;CHECK(identity(&m)==-ENODEV);gp[GR(PROFILE)/4]=SI_COLLECTOR_PROFILE;
 gp[GR(CAPS)/4]=RG_CAPS;CHECK(identity(&m)==-ENODEV);gp[GR(CAPS)/4]=SI_COLLECTOR_CAPS;
 gp[GR(RUN)/4]=1;before=writes;CHECK(config(&m,&c)==-EBUSY);CHECK(writes==before);gp[GR(RUN)/4]=0;
 c.mask=32;CHECK(config(&m,&c)==-EINVAL);c.mask=31;c.run=2;CHECK(config(&m,&c)==-EINVAL);c.run=0;
 c.periods[0]=999;CHECK(config(&m,&c)==-ERANGE);c.periods[0]=2147483648U;CHECK(config(&m,&c)==-ERANGE);c.periods[0]=1000;
 CHECK(config(&m,&c)==0);CHECK(c.id==1);CHECK(gp[GR(RUN)/4]==0);
 c.run=1;reject_run=true;CHECK(config(&m,&c)==-EACCES);reject_run=false;CHECK(gp[GR(RUN)/4]==0);
 CHECK(config(&m,&c)==0);CHECK(gp[GR(RUN)/4]==1);gp[GR(RUN)/4]=0;
 change_gen=true;CHECK(config(&m,&c)==-ESTALE);change_gen=false;timeout_cfg=true;CHECK(config(&m,&c)==-ETIMEDOUT);timeout_cfg=false;
 m.txn=UINT32_MAX;before=writes;CHECK(config(&m,&c)==-EOVERFLOW);CHECK(writes==before);
 before=reads+writes;CHECK(integration_state_show(&dev,&attr,buf)>0);CHECK(reads+writes==before);
 CHECK(buf[0]=='{');puts(buf);
 printf("PASS %u actual R5S2 identity/admission/RUN readback/readonly-observation checks\n",checks);return 0;
}
'''
(out/'model.c').write_text(pre+'\nstatic int identity(struct rs485_owner *m){return ('+identity+')?-ENODEV:0;}\n'+function+observation+test)
subprocess.check_call(['gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-parameter',
 '-I'+str(S/'bsp/telemetry'),str(out/'model.c'),'-o',str(out/'test')])
subprocess.check_call([str(out/'test')])
