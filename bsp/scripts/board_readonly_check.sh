#!/bin/sh
# Execute after a deliberately authorized SD boot; all queries are read-only.
set -eu
uname -a
cat /etc/os-release /proc/cmdline
findmnt -n -o SOURCE,MAJ:MIN,FSTYPE /
rootdev=$(findmnt -n -o MAJ:MIN / | tr -d '[:space:]')
rootpath=$(readlink -f "/sys/dev/block/$rootdev")
rootname=${rootpath##*/}
parent=${rootpath%/*}
echo "Root block device: $rootname"
cat "$parent/device/type"
test "$(cat "$parent/device/type")" = SD || { echo 'ERROR: root is not SD'; exit 1; }
cmdroot=$(tr ' ' '\n' < /proc/cmdline | sed -n 's/^root=//p')
case "$cmdroot" in
  PARTUUID=????????-02) ;;
  *) echo 'ERROR: expected exactly one SD root=PARTUUID=<MBR-id>-02'; exit 1 ;;
esac
expected_uuid=${cmdroot#PARTUUID=}
actual_uuid=$(blkid -s PARTUUID -o value "/dev/$rootname")
test "$actual_uuid" = "$expected_uuid" || { echo 'ERROR: root PARTUUID differs from boot arguments'; exit 1; }
# Optional independent assertion from the reviewed release manifest. No fixed
# old UUID in rootfs: its hash is an input to each new image's MBR signature.
if test -n "${1:-}"; then
  test "$actual_uuid" = "$1" || { echo 'ERROR: root PARTUUID differs from release manifest'; exit 1; }
fi
echo "SD root PARTUUID: $actual_uuid"
lsblk -o NAME,TYPE,SIZE,FSTYPE,PARTUUID,MOUNTPOINT
grep -E 'MemTotal|MemAvailable|CmaTotal|CmaFree' /proc/meminfo
dmesg | grep -Ei 'DDR|Memory:|cma|mmc|sdhci|error|failed' || true
zcat /proc/config.gz | grep -E 'CONFIG_(ANLOGIC_DMA|AXI_DMA|CMA|DMA_CMA|MODVERSIONS|UIO)' || true
cat /proc/interrupts
ls -l /sys/class/dma /sys/class/fpga_manager
modinfo anlogic-dma-engine
modinfo axi-dma-test
cat /proc/modules
echo 'This check did not load modules or perform MMIO/DMA/memory stress or storage writes.'
