/* Explicit owner/test utility; never enables motion or writes arbitrary MMIO. */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include "rs485_uapi.h"
#include "../../pl_rs485/software/rs485_telem.h"
static int ctl(int fd,unsigned long op,void *arg){int r=ioctl(fd,op,arg);if(r<0)fprintf(stderr,"ioctl error: %s\n",strerror(errno));return r;}
static void print_record(const rs485_telem_record *r)
{
 printf("collector_gen=%u revision=%u transport_gen=%u serial=%llu address=%02x query=%02x status=%u attempt=%u valid=%d request_us=%llu event_us=%llu signed_raw=%lld encoder_carry=%d encoder_value=%u enum=%u known=%d\n",
 r->collector_generation,r->revision,r->transport_generation,(unsigned long long)r->completion_serial,
 r->source.address,r->source.query,r->source.status,r->source.attempt,r->source.data_valid,
 (unsigned long long)r->source.request_us,(unsigned long long)r->source.event_us,(long long)r->source.signed_value,
 r->source.encoder_carry,r->source.encoder_value,r->source.enum_raw,r->source.enum_known);
}
int main(int argc,char **argv)
{
 int fd,ret=1,i;unsigned successes=0;struct rs485_state st;struct rs485_snapshot snap;const char *mode;
 if(argc!=2){fprintf(stderr,"usage: rs485-accept idle|diagnostic-timeouts|cancel|release\n");return 2;}
 mode=argv[1];fd=open("/dev/bsp-rs485",O_RDWR|O_CLOEXEC);if(fd<0){perror("open");return 1;}
 if(ctl(fd,RS485_STATE,&st))goto out;
 printf("STATE blocked=%u owned=%u quarantine=%u generation=%u actual=%u dma_status=%08x\n",st.blocked,st.owned,st.quarantine,st.generation,st.actual,st.dma_status);
 if(st.quarantine)goto out;
 if(!strcmp(mode,"cancel")||!strcmp(mode,"release")){ret=ctl(fd,!strcmp(mode,"cancel")?RS485_CANCEL:RS485_RELEASE,NULL)?1:0;goto out;}
 if(ctl(fd,RS485_SNAPSHOT,&snap))goto out;
 printf("CACHE snapshot=%u collector_generation=%u time_us=%llu\n",snap.id,snap.generation,(unsigned long long)snap.word[0]|((unsigned long long)snap.word[1]<<32));
 for(i=0;i<15;i++){const uint32_t *row=&snap.word[32+i*32];printf("ROW %d flags=%08x addr_query=%08x valid_gen=%u valid_rev=%u result_gen=%u result_rev=%u age=%llu\n",i,row[0],row[1],row[2],row[3],row[4],row[5],(unsigned long long)row[28]|((unsigned long long)row[29]<<32));}
 if(!strcmp(mode,"idle")){ret=ctl(fd,RS485_RELEASE,NULL)?1:0;goto out;}
 if(strcmp(mode,"diagnostic-timeouts")){fprintf(stderr,"unknown mode\n");goto out;}
 /* This explicit mode may transmit queries and accepts diagnostics as
  * transport evidence ONLY. It never declares valid driver feedback. */
 puts("EXPLICIT_DIAGNOSTIC_TRANSPORT_NOT_VALID_FEEDBACK");
 {
  struct rs485_config c={.periods={250000,250000,250000,250000,250000},.mask=31,.run=1};
  if(ctl(fd,RS485_CONFIG,&c))goto out;
  printf("CONFIG_MAP generation=%u revision=%u periods=250000,250000,250000,250000,250000 mask=31 applied_sequence=%u notified_us=%llu\n",c.generation,c.revision,c.apply_sequence,(unsigned long long)c.notified_us);
  {
   FILE *ledger=fopen("/tmp/rs485-config-ledger.csv","a");if(!ledger)goto out;
   if(fprintf(ledger,"%u,%u,%u,%llu,250000,250000,250000,250000,250000,31\n",c.generation,c.revision,c.apply_sequence,(unsigned long long)c.notified_us)<0||fflush(ledger)||fsync(fileno(ledger))){fclose(ledger);goto out;}
   fclose(ledger);
  }
  if(ctl(fd,RS485_RECOVER,NULL))goto out;
  for(i=0;i<16;i++){
   uint8_t bytes[1024];struct rs485_packet p={.data=(uintptr_t)bytes};unsigned j;
   if(ctl(fd,RS485_RX,&p)){if(errno==EAGAIN){usleep(20000);continue;}goto out;}
   printf("RX packet=%u gen=%u requested=%u actual=%u sr=%08x\n",p.id,p.generation,p.bytes,p.actual,p.status);
   for(j=0;j<p.records;j++){rs485_telem_record r;if(rs485_telem_decode(bytes+64*j,&r)){fprintf(stderr,"decoder refused record; cancel, do not COMPLETE\n");goto out;}print_record(&r);}
   /* Preserve complete bytes before granting completion/reuse. */
   {
    char name[96];int logfd;snprintf(name,sizeof(name),"/tmp/rs485-packet-%u-%u.bin",p.generation,p.id);
    logfd=open(name,O_WRONLY|O_CREAT|O_EXCL,0600);if(logfd<0)goto out;
    if(write(logfd,bytes,p.bytes)!=(ssize_t)p.bytes||fsync(logfd)){close(logfd);goto out;}close(logfd);
   }
   if(ctl(fd,RS485_COMPLETE,&p))goto out;
   successes++;
  }
  if(ctl(fd,RS485_CANCEL,NULL)||ctl(fd,RS485_RECOVER,NULL)||ctl(fd,RS485_RELEASE,NULL))goto out;
  if(!successes){fprintf(stderr,"No RX packets received; transport NOT verified\n");goto out;}
  printf("DIAGNOSTIC_TRANSPORT packets=%u; valid feedback NOT asserted; save /tmp ledger and packet bytes before power-off\n",successes);
 }
 ret=0;
out:
 if(ret)ctl(fd,RS485_CANCEL,NULL);
 close(fd);return ret;
}
