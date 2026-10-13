#!/bin/sh
set -eu
/usr/bin/bsp-readonly-check 2176bfe4-02
test "$(sha256sum /usr/bin/motion-accept | cut -d' ' -f1)" = 29c2e1646f3b9d7980b398b121e982bf77c4e7d9573ae604bdb476550319b3f6
cat /proc/interrupts
cat /proc/modules
/usr/bin/motion-accept idle
rmmod bsp_motion
test ! -e /dev/bsp-motion
/usr/bin/gp-accept /dev/bsp-gp
cat /proc/interrupts
sleep 1
cat /proc/interrupts
cat /proc/modules
dmesg | tail -n 40
echo BSP_MOTION_FAILURE_SAFE_RELEASE_COMPLETE
