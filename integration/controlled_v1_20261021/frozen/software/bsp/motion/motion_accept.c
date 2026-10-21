#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <time.h>
#include <pthread.h>
#include <poll.h>
#include "motion_uapi.h"
#include "mot2_codec.h"
#define P(x) PLI_MOTION_GP_MOTION_V1_##x
static unsigned checks;
static int fd;
static void require(int ok,const char *s) { if(!ok) {fprintf(stderr,"MOTION_ACCEPT_FAIL %s errno=%d\n",s,errno);ioctl(fd,MOTION_STOP);exit(1);}checks++; }
static uint64_t now(void) {struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*1000000000+t.tv_nsec;}
static struct motion_snapshot snap(void) {struct motion_snapshot s={0};require(ioctl(fd,MOTION_SNAPSHOT,&s)==0,"snapshot");require(!s.quarantined,"not quarantined");return s;}
static uint64_t pair(const uint32_t *w) {return (uint64_t)w[1]<<32|w[0];}
static struct motion_command cmd(unsigned op,unsigned mask) {struct motion_command c={.opcode=op,.axis_mask=mask,.timeout_ms=2000};require(ioctl(fd,MOTION_COMMAND,&c)==0,"command ACK");return c;}
static uint64_t begin(void) {struct motion_command c;require(ioctl(fd,MOTION_RECOVER)==0,"explicit recover");cmd(PLI_CMD_DISABLE,15);require(ioctl(fd,MOTION_RECOVER)==0,"recover after DISABLE cancellation");cmd(PLI_CMD_REBASE,15);cmd(PLI_CMD_ENABLE,15);c=cmd(PLI_CMD_OPEN_SESSION,15);require(c.session!=0,"session unique");return c.session;}
static struct motion_packet send_bytes(uint8_t *b,unsigned count,int expect_ok) {struct motion_packet p={.data=(uintptr_t)b,.count=count,.timeout_ms=2000};int r=ioctl(fd,MOTION_PACKET,&p);if(expect_ok) require(r==0 && !p.result,"IOC + packet_closed");else require(r<0,"rejected packet");return p;}
static void wait_done(unsigned n) {uint64_t end=now()+2000000000;struct motion_snapshot s;do {s=snap();require(!s.words[P(SNAP_WORD_ERROR)],"no motion error");if(s.words[P(SNAP_WORD_END_COUNT)]>=n) return;usleep(100);}while(now()<end);require(0,"session_done timeout");}
static void print_snapshot(const char *tag) {struct motion_snapshot s=snap();unsigned i;printf("SNAP %s gen=%u status=%x error=%x accepted=%u active=%u done=%u valid=%x buffered=%u ends=%u cancels=%u time=%"PRIu64,tag,s.generation,s.words[P(SNAP_WORD_STATUS)],s.words[P(SNAP_WORD_ERROR)],s.words[P(SNAP_WORD_ACCEPT_SEQ)],s.words[P(SNAP_WORD_ACTIVE_SEQ)],s.words[P(SNAP_WORD_DONE_SEQ)],s.words[P(SNAP_WORD_VALIDITY)],s.words[P(SNAP_WORD_BUFFERED)],s.words[P(SNAP_WORD_END_COUNT)],s.words[P(SNAP_WORD_CANCEL_COUNT)],pair(s.words+2));for(i=0;i<4;i++) printf(" pos%u=%"PRId64" pulse%u=%"PRIu64,i,(int64_t)pair(s.words+16+i*4),i,pair(s.words+18+i*4));puts("");}
struct snapshot_job {struct motion_snapshot s;int result;};
static void *snapshot_worker(void *data) {struct snapshot_job *j=data;usleep(10000);j->result=ioctl(fd,MOTION_SNAPSHOT,&j->s);return NULL;}
static void event_poll(void) {
 struct snapshot_job j={0};struct motion_snapshot before=snap(),after;struct pollfd p={.fd=fd,.events=POLLIN};pthread_t thread;
 require(ioctl(fd,MOTION_EVENTS)==0,"clear/rearm motion events");require(poll(&p,1,0)==0,"no old pending event");
 require(pthread_create(&thread,NULL,snapshot_worker,&j)==0,"independent snapshot worker");
 require(poll(&p,1,1000)==1 && (p.revents&POLLIN),"motion IRQ poll wake");
 require(pthread_join(thread,NULL)==0 && j.result==0,"snapshot while waiting");
 after=snap();require(after.event_count>before.event_count,"motion IRQ event count advances");
 printf("MOTION_EVENT_POLL_PASS before=%"PRIu64" after=%"PRIu64"\n",(uint64_t)before.event_count,(uint64_t)after.event_count);
}
static void short_path(void) {
 uint8_t b[3*72];uint64_t session=begin();int64_t pos[3][4]={{12,-7,0,5},{-4,9,0,-2},{-4,9,0,-2}};
 struct motion_snapshot a=snap(),z;unsigned i;
 for(i=0;i<3;i++) mot_encode(b+i*72,session,i,10000,pos[i],i==2);
 send_bytes(b,3,1);cmd(PLI_CMD_START,15);wait_done(a.words[P(SNAP_WORD_END_COUNT)]+1);z=snap();
 require(z.words[P(SNAP_WORD_ACCEPT_SEQ)]==2 && z.words[P(SNAP_WORD_DONE_SEQ)]==2 && (z.words[P(SNAP_WORD_VALIDITY)]&(P(SNAP_VALIDITY_ACCEPT_VALID_MASK)|P(SNAP_VALIDITY_DONE_VALID_MASK)))==(P(SNAP_VALIDITY_ACCEPT_VALID_MASK)|P(SNAP_VALIDITY_DONE_VALID_MASK)),"accepted/done seq");
 for(i=0;i<4;i++) {static const uint64_t pulses[4]={28,23,0,12};require((int64_t)pair(z.words+16+i*4)==pos[2][i],"four axis final position");require(pair(z.words+18+i*4)-pair(a.words+18+i*4)==pulses[i],"pulse totals with reverse/zero");}
 print_snapshot("short-END");cmd(PLI_CMD_DISABLE,15);
}
static void *pause_worker(void *data) {struct motion_command *c=data;c->opcode=PLI_CMD_PAUSE;c->axis_mask=15;c->timeout_ms=2000;return (void *)(intptr_t)ioctl(fd,MOTION_COMMAND,c);}
static void pause_stop(void) {
 uint8_t b[2*72];int64_t p[4]={100,-60,20,-8};uint64_t session=begin();pthread_t t;void *result;struct motion_command c={0};struct motion_snapshot s;
 mot_encode(b,session,0,500000,p,0);p[0]=200;mot_encode(b+72,session,1,500000,p,1);send_bytes(b,2,1);cmd(PLI_CMD_START,15);
 require(pthread_create(&t,NULL,pause_worker,&c)==0,"PAUSE thread");usleep(1000);
 require(ioctl(fd,MOTION_STOP)==0,"independent STOP during busy PAUSE");require(pthread_join(t,&result)==0,"PAUSE join");require((intptr_t)result<0,"pending PAUSE cancelled");
 s=snap();require(s.words[P(SNAP_WORD_STATUS)]&P(STATUS_BITS_STOP_COMPLETE_MASK),"pulse safe");require(!s.words[P(SNAP_WORD_BUFFERED)],"STOP queues empty");print_snapshot("busy-PAUSE-STOP");require(ioctl(fd,MOTION_RECOVER)==0,"cancel recovery");
 s=snap();require(!s.dma_owned,"DMA buffer reclaimed");require(ioctl(fd,MOTION_REALLOC)==0,"buffer reallocation after proof");require(ioctl(fd,MOTION_RECOVER)==0,"explicit link recovery after reallocation");
}
static void pause_resume(void) {
 uint8_t b[3*72];uint64_t session=begin();int64_t p[4]={3,-2,1,-1};struct motion_snapshot a=snap(),s;
 unsigned i;for(i=0;i<3;i++) {p[0]+=3;mot_encode(b+i*72,session,i,100000,p,i==2);}send_bytes(b,3,1);cmd(PLI_CMD_START,15);cmd(PLI_CMD_PAUSE,15);
 s=snap();require(s.words[P(SNAP_WORD_STATUS)]&P(STATUS_BITS_PAUSED_MASK),"PAUSE at boundary");usleep(10000);require(snap().words[P(SNAP_WORD_DONE_SEQ)]==s.words[P(SNAP_WORD_DONE_SEQ)],"paused sequence stable");cmd(PLI_CMD_RESUME,15);wait_done(a.words[P(SNAP_WORD_END_COUNT)]+1);print_snapshot("pause-resume-END");cmd(PLI_CMD_DISABLE,15);
}
static void bad_packets(void) {
 unsigned mode;for(mode=0;mode<3;mode++) {uint8_t b[72];int64_t p[4]={1,2,-3,0};uint64_t session=begin();struct motion_snapshot a=snap(),s;
 mot_encode(b,session,mode==1?1:0,10000,p,1);
 if(mode==0) b[PLI_MOTION_STREAM_V2_CRC_OFFSET]^=1;
 if(mode==2) {mot_encode(b,session-1,0,10000,p,1);send_bytes(b,1,1);} else send_bytes(b,1,mode==1);
 s=snap();if(mode==2) {require(s.words[P(SNAP_WORD_STALE_COUNT)]>a.words[P(SNAP_WORD_STALE_COUNT)],"old-session stale");require(s.words[P(SNAP_WORD_ACCEPT_COUNT)]==a.words[P(SNAP_WORD_ACCEPT_COUNT)],"stale not accepted");} else {require(s.words[P(SNAP_WORD_ERROR)]!=0,"CRC/sequence fault");require(!s.words[P(SNAP_WORD_BUFFERED)],"bad queue cleared");}
 require(ioctl(fd,MOTION_STOP)==0,"bad STOP");require(ioctl(fd,MOTION_RECOVER)==0,"explicit fault recovery");print_snapshot("malformed-recovered");}
}
static void underflow(void) {
 uint8_t b[32*72];uint64_t session=begin(),end;int64_t p[4]={0};unsigned i;struct motion_snapshot s;
 for(i=0;i<32;i++) {p[0]=i;mot_encode(b+i*72,session,i,100,p,0);}send_bytes(b,32,1);cmd(PLI_CMD_START,15);
 end=now()+2000000000;do {s=snap();if(s.words[P(SNAP_WORD_ERROR)]) break;usleep(100);}while(now()<end);
 require(s.words[P(SNAP_WORD_ERROR)]==PLI_ERR_UNDERRUN,"expected underflow");require(!(s.words[P(SNAP_WORD_STATUS)]&P(STATUS_BITS_SESSION_MASK)),"underflow cancels session");
 require(ioctl(fd,MOTION_RECOVER)==0,"underflow explicit recovery");print_snapshot("underflow-recovered");
}
struct injection {uint8_t data[910*72];struct motion_packet p;int result;};
static void *inject_worker(void *arg) {struct injection *x=arg;x->result=ioctl(fd,MOTION_INJECT,&x->p);return NULL;}
static void injected(void) {
 unsigned mode,i;for(mode=1;mode<=3;mode++) {
  struct injection x={0};pthread_t thread;uint64_t session=begin();int64_t p[4]={1,-2,0,4};struct motion_snapshot before=snap(),after;
  x.p.data=(uintptr_t)x.data;x.p.count=mode==3?910:2;x.p.timeout_ms=100;x.p.reserved=mode;
  for(i=0;i<x.p.count;i++) mot_encode(x.data+i*72,session,i,100000,p,i==x.p.count-1);
  if(mode==3) {
   require(pthread_create(&thread,NULL,inject_worker,&x)==0,"inflight DMA thread");usleep(1000);
   after=snap();require(after.dma_owned && after.words[P(SNAP_WORD_BUFFERED)]>0,"backpressured DMA inflight");
   require(ioctl(fd,MOTION_STOP)==0,"inflight STOP");require(ioctl(fd,MOTION_RECOVER)==0,"inflight DMA terminate/reset recovery");require(pthread_join(thread,NULL)==0,"inflight thread joined");
  } else x.result=ioctl(fd,MOTION_INJECT,&x.p);
  require(x.result<0,"truncated/ARM mismatch/STOP cancels packet");
  require(ioctl(fd,MOTION_RECOVER)==0,"injection explicit recovery");after=snap();
  require(pair(after.words+2)>=pair(before.words+2),"DMA reset keeps timestamp");
  for(i=0;i<4;i++) require(pair(after.words+16+i*4)==pair(before.words+16+i*4),"prestart DMA reset keeps position");
  require(!after.words[P(SNAP_WORD_BUFFERED)] && !after.dma_owned,"queues and DMA ownership cleared");print_snapshot("inject-recovered");
 }
}
static void sustained(void) {
 uint8_t b[32*72];int64_t pos[4]={0};uint64_t session=begin(),last=0,maxgap=0,minlevel=~0u,start=now();unsigned seq=0,batch,i;struct motion_snapshot a=snap(),s;struct motion_packet q, timings[6400];uint64_t gaps[6400]={0};
 for(batch=0;batch<6400;batch++) {
  if(batch) {do {s=snap();require(!s.words[P(SNAP_WORD_ERROR)],"sustained fault");if(s.words[P(SNAP_WORD_BUFFERED)]<minlevel) minlevel=s.words[P(SNAP_WORD_BUFFERED)];if(s.words[P(SNAP_WORD_BUFFERED)]<=48) break;usleep(50);}while(1);}
  for(i=0;i<(batch<2?32u:16u);i++,seq++) {pos[0]=(int64_t)(seq%40)-20;pos[1]=(int64_t)(seq%30)-15;pos[2]=0;pos[3]=(int64_t)(seq%10)-5;mot_encode(b+i*72,session,seq,100,pos,batch==6399 && i==15);}
  q=send_bytes(b,batch<2?32:16,1);if(last) {gaps[batch]=now()-last;if(gaps[batch]>maxgap) maxgap=gaps[batch];}last=now();timings[batch]=q;
  /* Keep UART printing outside the live producer interval. */
  if(!batch) cmd(PLI_CMD_START,15);
 }
 wait_done(a.words[P(SNAP_WORD_END_COUNT)]+1);s=snap();require(s.words[P(SNAP_WORD_DONE_SEQ)]==seq-1,"long trajectory done");
 printf("SUPPLY_RESULT points=%u elapsed_ns=%"PRIu64" max_success_gap_ns=%"PRIu64" min_sampled_watermark=%"PRIu64" target_gap_ns=2000000 target_met=%u\n",seq,now()-start,maxgap,minlevel,maxgap<=2000000);
 for(batch=0;batch<6400;batch++) printf("SUPPLY batch=%u gap_ns=%"PRIu64" submit_ns=%"PRIu64" ioc_ns=%"PRIu64" closed_ns=%"PRIu64"\n",batch,gaps[batch],(uint64_t)timings[batch].submit_ns,(uint64_t)timings[batch].ioc_ns,(uint64_t)timings[batch].closed_ns);
 print_snapshot("sustained-END");cmd(PLI_CMD_DISABLE,15);
}
int main(int argc,char **argv) {
 require(mot_crc((const uint8_t *)"123456789",9)==0xcbf43926,"CRC32 ISO HDLC");
 fd=open("/dev/bsp-motion",O_RDWR|O_CLOEXEC);require(fd>=0,"open restricted client");
 require(ioctl(fd,MOTION_EVENTS)==0,"IRQ arm");print_snapshot("initial");
 if(argc>1 && !strcmp(argv[1],"idle")) { /* explicit stop/release only; no trajectory */ }
 else if(argc>1 && !strcmp(argv[1],"supply")) sustained();else {event_poll();short_path();pause_resume();pause_stop();bad_packets();underflow();injected();short_path();}
 require(ioctl(fd,MOTION_STOP)==0,"final STOP");require(ioctl(fd,MOTION_RECOVER)==0,"final DMA quiescence");cmd(PLI_CMD_DISABLE,15);print_snapshot("final-idle");require(ioctl(fd,MOTION_RELEASE)==0,"quiescent buffer release");require(close(fd)==0,"close stop/synchronize");printf("MOTION_ACCEPT_PASS checks=%u\n",checks);return 0;
}
