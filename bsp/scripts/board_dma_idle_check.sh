#!/bin/sh
# Read-only follow-up after full accepted DMA test; do not submit or unload.
set -eu
grep -q 'root=PARTUUID=a3d29e67-02' /proc/cmdline
before=$(grep 'anlogic-dma-controller' /proc/interrupts)
test -n "$before"
sleep 1
after=$(grep 'anlogic-dma-controller' /proc/interrupts)
test "$before" = "$after"
cat /proc/interrupts
cat /proc/modules
echo BSP_DMA_IDLE_IRQ_STABLE_ONE_SECOND
