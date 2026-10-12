#!/bin/sh
# Existing quarantined DMA buffers must stay allocated; no reset/unload here.
set -eu
echo BSP_DMA_FAILURE_DIAGNOSTICS_BEGIN
cat /proc/interrupts
cat /proc/modules
dmesg | tail -n 55
/usr/bin/gp-accept /dev/bsp-gp
/tmp/bsp-gp-timestamp
echo BSP_DMA_FAILURE_DIAGNOSTICS_COMPLETE_NO_DMA_REUSE
