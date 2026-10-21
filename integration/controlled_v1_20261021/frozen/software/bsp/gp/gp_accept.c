/* SPDX-License-Identifier: GPL-2.0 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <poll.h>
#include <sys/ioctl.h>
#include <time.h>
#include "gp_uapi.h"
#include "generated/gp_defs.h"
#define PROFILE(x) PLI_GP_GP_CONTROL_PROBE_V1_##x
_Static_assert(sizeof(struct gp_command) == 128, "UAPI command layout");
_Static_assert(sizeof(struct gp_event) == 16, "UAPI event layout");
static unsigned checks;
static void check(int yes, const char *name)
{
 if (!yes) { fprintf(stderr, "FAIL %s errno=%d\n", name, errno); exit(1); }
 checks++; printf("PASS %s\n", name); fflush(stdout);
}
static void call(int fd, unsigned long op, void *data)
{ if (ioctl(fd, op, data)) { perror("ioctl"); exit(1); } }
static struct gp_irq_config irq_config(int fd, uint32_t mask, uint32_t source, uint32_t clear)
{
 struct gp_irq_config q = {.mask=mask, .source=source, .clear=clear};
 call(fd, GP_IRQ_CONFIG, &q); return q;
}
static struct gp_command command(int fd, uint32_t opcode, int repeat)
{
 struct gp_command c = {.opcode=opcode, .repeat=(uint32_t)repeat};
 call(fd, GP_COMMAND, &c);
 check(!c.error && (c.status & (PLI_REG_CMD_STATUS_ACK_VALID_MASK | PLI_REG_CMD_STATUS_ACCEPTED_MASK | PLI_REG_CMD_STATUS_COMPLETED_MASK)) ==
 (PLI_REG_CMD_STATUS_ACK_VALID_MASK | PLI_REG_CMD_STATUS_ACCEPTED_MASK | PLI_REG_CMD_STATUS_COMPLETED_MASK), "control ACK accepted/completed (not motion)");
 return c;
}
static struct gp_event event(int fd, int timeout)
{
 struct pollfd p = {.fd=fd, .events=POLLIN};
 struct gp_event e = {0};
 int n;
 do { n = poll(&p, 1, timeout); } while (n < 0 && errno == EINTR);
 check(n == 1 && (p.revents & POLLIN) && !(p.revents & (POLLERR|POLLHUP)), "IRQ poll wake");
 call(fd, GP_EVENT, &e); return e;
}
static void idle_frame(const struct gp_command *c)
{
 unsigned i;
 check(c->snapshot_valid && c->snapshot_id == c->txn, "snapshot ID/valid atomicity");
 for (i=0; i<4; i++) check(c->position[i] == 0 && c->pulses[i] == 0, "idle axis position/pulse slot");
 check(c->position_valid == 0 && c->session == 0 && c->accepted_seq == UINT32_MAX && c->done_seq == UINT32_MAX,
 "idle invalid/no-point metadata");
 check(c->state == PLI_STATE_NOT_READY, "snapshot NOT_READY state");
}
int main(int argc, char **argv)
{
 int fd, n;
 unsigned i;
 uint32_t patterns[] = {0, UINT32_MAX, 0x55aa55aa, 0x12345678};
 struct gp_identity id;
 struct gp_command a, b, dup, invalid = {.opcode=PLI_CMD_START};
 struct gp_event e1, e2, ack;
 struct gp_irq_config q;
 struct timespec start, finish;
 struct pollfd p;
 double elapsed;
 if (argc != 2) { fprintf(stderr,"usage: gp-accept /dev/bsp-gp\n"); return 2; }
 fd = open(argv[1], O_RDWR|O_CLOEXEC);
 if (fd < 0) { perror("open"); return 1; }
 call(fd, GP_IDENTITY, &id);
 printf("IDENTITY version=%u caps=%x features=%x tick_hz=%u last_txn=%u\n", id.version,id.caps,id.features,id.tick_hz,id.last_txn);
 check(id.version == PROFILE(EXPECTED_VERSION) && id.caps == PROFILE(EXPECTED_CAPS) &&
 id.features == PROFILE(EXPECTED_FEATURES) && id.tick_hz == PROFILE(EXPECTED_TICK_HZ), "exact profile identity/features");
 for (i=0;i<sizeof(patterns)/sizeof(patterns[0]);i++) {
  struct gp_scratch s = {.value=patterns[i]}; call(fd, GP_SCRATCH, &s); check(s.value == patterns[i], "scratch write/readback");
 }
 errno=0; n=ioctl(fd, GP_COMMAND, &invalid);
 check(n == -1 && errno == EINVAL, "motion opcode rejected in software without MMIO");
 irq_config(fd, 0, 0, PROFILE(IRQ_PENDING_MASK));
 command(fd, PLI_CMD_NOP, 0);
 clock_gettime(CLOCK_MONOTONIC, &start);
 a = command(fd, PLI_CMD_SNAPSHOT, 0); idle_frame(&a);
 dup = command(fd, PLI_CMD_SNAPSHOT, 1);
 check(!memcmp(&a, &dup, sizeof(a)), "duplicate snapshot retains complete frame");
 usleep(20000);
 b = command(fd, PLI_CMD_SNAPSHOT, 0);
 clock_gettime(CLOCK_MONOTONIC, &finish); idle_frame(&b);
 elapsed = finish.tv_sec-start.tv_sec + (finish.tv_nsec-start.tv_nsec)/1e9;
 printf("TIMESTAMP delta_ticks=%llu host_seconds=%.6f\n", (unsigned long long)(b.timestamp-a.timestamp),elapsed);
 check(b.txn > a.txn && b.timestamp > a.timestamp, "new transaction/timestamp progression");
 check((b.timestamp-a.timestamp) >= 10000 && (b.timestamp-a.timestamp) <= (uint64_t)((elapsed+0.1)*id.tick_hz), "1MHz timestamp coarse sanity (not frequency calibration)");
 irq_config(fd, 0, 0, PROFILE(IRQ_PENDING_MASK));
 q=irq_config(fd, 0, 1, 0);
 check(q.pending & PLI_REG_IRQ_PENDING_TEST_MASK, "masked persistent source still latches");
 q=irq_config(fd, 0, 1, PLI_REG_IRQ_PENDING_TEST_MASK);
 check(q.pending & PLI_REG_IRQ_PENDING_TEST_MASK, "W1C cannot clear active source");
 irq_config(fd, PLI_REG_IRQ_PENDING_TEST_MASK, 1, 0);
 e1=event(fd,1000); check(e1.pending & PLI_REG_IRQ_PENDING_TEST_MASK, "TEST IRQ delivered");
 q=irq_config(fd, 0, 0, PLI_REG_IRQ_PENDING_TEST_MASK);
 check(!(q.pending & PLI_REG_IRQ_PENDING_TEST_MASK), "remove source then W1C clears");
 irq_config(fd, PLI_REG_IRQ_PENDING_TEST_MASK, 0, 0);
 p=(struct pollfd){.fd=fd,.events=POLLIN}; n=poll(&p,1,100);
 check(n==0, "no IRQ storm after clear/rearm");
 irq_config(fd, PLI_REG_IRQ_PENDING_TEST_MASK, 1, 0);
 e2=event(fd,1000); check(e2.count > e1.count, "TEST IRQ retrigger/recovery");
 irq_config(fd, PLI_REG_IRQ_PENDING_ACK_MASK, 0, PROFILE(IRQ_PENDING_MASK));
 b=command(fd, PLI_CMD_NOP, 0); ack=event(fd,1000);
 check(ack.pending & PLI_REG_IRQ_PENDING_ACK_MASK, "command ACK IRQ delivered");
 q=irq_config(fd,0,0,PROFILE(IRQ_PENDING_MASK)); check(!q.pending, "all sources cleared");
 dup=command(fd,PLI_CMD_NOP,1); check(dup.txn==b.txn, "IRQ clear preserves cached ACK");
 irq_config(fd,0,0,PROFILE(IRQ_PENDING_MASK));
 close(fd);
 printf("GP_ACCEPT_PASS checks=%u; idle snapshot only, no DMA or motor validation\n",checks);
 return 0;
}
