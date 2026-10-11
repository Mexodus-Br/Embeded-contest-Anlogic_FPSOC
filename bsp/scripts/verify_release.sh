#!/usr/bin/env bash
set -euo pipefail
TASK=${TASK:-$HOME/embedded-bsp}
OUT=$TASK/output
cd "$OUT/release"
sha256sum -c SHA256SUMS
sfdisk -d sdcard.img
fsck.vfat -n boot.vfat
e2fsck -fn rootfs.ext4
mkimage -l boot.scr
mkimage -l uImage.lz4
dtc -I dtb -O dts system.dtb > "$OUT/debug/system.decoded.dts"
fdtget -t x system.dtb /memory reg
fdtget -t x system.dtb /reserved-memory/linux,cma size
fdtget system.dtb /aliases mmc0
fdtget system.dtb /aliases mmc1
for module in "$OUT/kernel/drivers/dma/anlogic/"*.ko; do
  modinfo -F name "$module"
  modinfo -F vermagic "$module"
  modinfo -F depends "$module"
done
grep -E 'CONFIG_(MODVERSIONS|ANLOGIC_DMA|AXI_DMA|PREEMPT_RT|PREEMPT=|IKCONFIG|DMA_CMA)' "$OUT/kernel/.config"
grep -E 'CONFIG_ENV_IS' "$OUT/uboot/.config"
grep -E 'SoC_M90_DdrInit|fd_ddr_init_v2|__Soc_PlatInit' "$OUT/fsbl/symbols.txt"
test -x "$OUT/buildroot/target/usr/bin/bsp-readonly-check"
