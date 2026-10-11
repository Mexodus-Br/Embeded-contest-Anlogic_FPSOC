#!/bin/sh
# Execute after a deliberately authorized SD boot; all queries are read-only.
set -eu
uname -a
cat /etc/os-release /proc/cmdline
findmnt -n -o SOURCE,MAJ:MIN,FSTYPE /
rootdev=$(findmnt -n -o MAJ:MIN /)
rootpath=$(readlink -f "/sys/dev/block/$rootdev")
rootname=${rootpath##*/}
parent=${rootpath%/*}
echo "Root block device: $rootname"
cat "$parent/device/type"
test "$(cat "$parent/device/type")" = SD || { echo 'ERROR: root is not SD'; exit 1; }
lsblk -o NAME,TYPE,SIZE,FSTYPE,PARTUUID,MOUNTPOINT
grep -E 'MemTotal|MemAvailable|CmaTotal|CmaFree' /proc/meminfo
dmesg | grep -Ei 'DDR|Memory:|cma|mmc|sdhci|error|failed' || true
zcat /proc/config.gz | grep -E 'CONFIG_(ANLOGIC_DMA|AXI_DMA|CMA|DMA_CMA|MODVERSIONS|UIO)' || true
cat /proc/interrupts
ls -l /sys/class/dma /sys/class/fpga_manager
modinfo anlogic-dma-engine
modinfo axi-dma-test
echo 'No modules loaded; no MMIO/DMA/memory stress or storage writes performed.'
