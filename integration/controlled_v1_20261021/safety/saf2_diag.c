/* Explicit no-motor diagnostic CLI. No execution backend or heartbeat thread. */
#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <time.h>
#include "safety_uapi.h"
#include "generated/interlock_defs.h"
static int number(const char *s,uint32_t *v)
{char *end;unsigned long n;errno=0;if(!*s||*s=='-')return -1;n=strtoul(s,&end,10);if(errno||*end||n>UINT32_MAX)return -1;*v=(uint32_t)n;return 0;}
static uint64_t wide(const uint32_t *words,unsigned lo)
{return (uint64_t)words[lo]|(uint64_t)words[lo+1]<<32;}
static int report(int fd)
{
 struct saf2_snapshot s={0};unsigned i;
 if(ioctl(fd,SAF2_SNAPSHOT,&s)<0){perror("snapshot");return 1;}
 printf("{\"source\":\"BOARD_SAF2_DIAGNOSTIC\",\"version\":%u,\"profile\":%u,\"caps\":%u,\"features\":%u,\"config_valid\":%u,\"config_id\":[",s.version,s.profile,s.caps,s.features,s.config_valid);
 for(i=0;i<8;i++)printf("%s%u",i?",":"",s.config_id[i]);
 printf("],\"irq_pending\":%u,\"irq_mask\":%u,\"irq_events\":%u,\"config_accepted\":%u,\"config_applied\":%u,\"global_id\":%u,\"interlock_id\":%u,\"global\":[",s.irq_pending,s.irq_mask,s.irq_events,s.config_accepted,s.config_applied,s.global_id,s.interlock_id);
 for(i=0;i<64;i++)printf("%s%u",i?",":"",s.global[i]);
 printf("],\"interlock\":[");for(i=0;i<32;i++)printf("%s%u",i?",":"",s.interlock[i]);
 printf("],\"decoded\":{\"time_us\":\"%" PRIu64 "\",\"owner_id\":\"%" PRIu64 "\",\"last_sequence\":\"%" PRIu64 "\",\"causes\":%u,\"status\":%u,\"axes\":%u,\"seen_axes\":%u,\"feedback_limit_us\":%u,\"watchdog_limit_us\":%u,\"feedback_age_us\":[",
  wide(s.interlock,SI_SNAP_TIME_LO),wide(s.interlock,SI_SNAP_OWNER_LO),wide(s.interlock,SI_SNAP_LAST_SEQ_LO),
  s.interlock[SI_SNAP_CAUSES],s.interlock[SI_SNAP_STATUS],s.interlock[SI_SNAP_AXES],s.interlock[SI_SNAP_SEEN_AXES],
  s.interlock[SI_SNAP_FEEDBACK_US],s.interlock[SI_SNAP_WATCHDOG_US]);
 for(i=0;i<3;i++){
  if(i)putchar(',');
  if((s.interlock[SI_SNAP_STATUS]&SI_STATUS_POLL_RUN) && (s.interlock[SI_SNAP_SEEN_AXES]&(1U<<i)))
   printf("\"%" PRIu64 "\"",wide(s.interlock,SI_SNAP_TIME_LO)-wide(s.interlock,SI_SNAP_FEEDBACK_TIME_A0_LO+2*i));
  else printf("null");
 }
 printf("],\"feedback_fresh_by_age\":[");
 for(i=0;i<3;i++){
  int fresh=(s.interlock[SI_SNAP_STATUS]&SI_STATUS_POLL_RUN) && (s.interlock[SI_SNAP_SEEN_AXES]&(1U<<i)) &&
    wide(s.interlock,SI_SNAP_TIME_LO)-wide(s.interlock,SI_SNAP_FEEDBACK_TIME_A0_LO+2*i)<s.interlock[SI_SNAP_FEEDBACK_US];
  printf("%s%s",i?",":"",fresh?"true":"false");
 }
 puts("]},\"time_unit\":\"us_u64_low_high_words\",\"production_home_approved\":false,\"dma_ddr_quiescence\":\"NOT_PROVEN_BY_PL_SNAPSHOT\"}");
 return ferror(stdout)?1:0;
}
int main(int argc,char **argv)
{
 int fd,ret=1;struct saf2_config c;
 if(argc<2 || (strcmp(argv[1],"snapshot") && strcmp(argv[1],"config") && strcmp(argv[1],"watchdog-timeout"))){
  fputs("Usage: saf2-diag snapshot | config TXN AXES FEEDBACK_US WATCHDOG_US | watchdog-timeout --no-motor\n",stderr);return 2;}
 if(!strcmp(argv[1],"snapshot") && argc!=2)return 2;
 if(!strcmp(argv[1],"config") && (argc!=6 || number(argv[2],&c.txn) || number(argv[3],&c.axes) || number(argv[4],&c.feedback_us) || number(argv[5],&c.watchdog_us)))return 2;
 if(!strcmp(argv[1],"watchdog-timeout") && (argc!=3 || strcmp(argv[2],"--no-motor")))return 2;
 fd=open("/dev/bsp-saf2-diag",O_RDWR|O_CLOEXEC);if(fd<0){perror("open SAF2 diagnostic");return 1;}
 if(!strcmp(argv[1],"config")){
  if(ioctl(fd,SAF2_CONFIG,&c)<0)perror("config rejected");else ret=report(fd);
 }else if(!strcmp(argv[1],"watchdog-timeout")){
  if(ioctl(fd,SAF2_TIMEOUT_TEST)<0)perror("new owner rejected");else{
   struct timespec wait={3,100000000};
   struct saf2_snapshot s={0};
   while(nanosleep(&wait,&wait)<0 && errno==EINTR){}
   if(ioctl(fd,SAF2_SNAPSHOT,&s)<0)perror("timeout snapshot");
   else if(!(s.interlock[SI_SNAP_CAUSES]&SI_CAUSE_WATCHDOG) ||
           (s.interlock[SI_SNAP_STATUS]&SI_STATUS_OWNER_ACTIVE))
    fputs("watchdog timeout not confirmed\n",stderr);
   else ret=report(fd);
  }
 }else ret=report(fd);
 close(fd);return ret;
}
