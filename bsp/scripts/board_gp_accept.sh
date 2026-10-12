#!/bin/sh
# Run only after the authorized new SD cold boot; serial output is the evidence.
set -eu
test "$#" = 1 || { echo 'Usage: board_gp_accept.sh REVIEWED_ROOT_PARTUUID'; exit 2; }
/usr/bin/bsp-readonly-check "$1"
test "$(uname -r)" = 6.1.111-rt42-bsp-sd1
test "$(zcat /proc/config.gz | sha256sum | cut -d' ' -f1)" = 81f7b75cb8e2f0901ef3dbd6eb78282db988031904dd1001ed709beb1120dbf1
test "$(sha256sum /usr/bin/gp-accept | cut -d' ' -f1)" = ce7a38c0c2e4f35fe1b73d0591fc9881476ce064fede2823a57d552840017136
test "$(sha256sum /lib/modules/$(uname -r)/extra/bsp_gp.ko | cut -d' ' -f1)" = c0131bcdd4d18485e4392e16428778bf2aac5520bfa48a781ec86d1aede3040b
test "$(modinfo -F vermagic bsp_gp)" = '6.1.111-rt42-bsp-sd1 SMP preempt mod_unload modversions aarch64'
echo BSP_GP_IRQ_BEFORE
cat /proc/interrupts
modprobe bsp_gp
test -c /dev/bsp-gp
/usr/bin/gp-accept /dev/bsp-gp
echo BSP_GP_IRQ_AFTER
cat /proc/interrupts
dmesg | tail -n 60
echo BSP_GP_BOARD_ACCEPT_COMPLETE_IDLE_ONLY
