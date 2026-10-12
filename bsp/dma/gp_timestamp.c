// SPDX-License-Identifier: GPL-2.0
/* One authorized SNAPSHOT via GP driver; no MMIO mapping or physical address. */
#include <fcntl.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include "../gp/gp_uapi.h"
#include "../gp/generated/gp_defs.h"
int main(void)
{
    struct gp_command c={.opcode=PLI_CMD_SNAPSHOT};
    int fd=open("/dev/bsp-gp",O_RDWR|O_CLOEXEC);
    if(fd<0){perror("GP open");return 1;}
    if(ioctl(fd,GP_COMMAND,&c) || c.error || !c.snapshot_valid || c.snapshot_id!=c.txn){
      perror("GP snapshot");close(fd);return 1;
    }
    printf("%" PRIu64 "\n",(uint64_t)c.timestamp);
    close(fd);return 0;
}
