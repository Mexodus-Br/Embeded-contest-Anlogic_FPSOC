#!/usr/bin/env bash
# Work only in a separately extracted vendor copy, never the reference tree.
set -euo pipefail
export LC_ALL=C LANG=C TZ=UTC SOURCE_DATE_EPOCH=1791676800
export KBUILD_BUILD_USER=bsp KBUILD_BUILD_HOST=linux-builder KBUILD_BUILD_VERSION=1
export KBUILD_BUILD_TIMESTAMP="$(date -u -d @${SOURCE_DATE_EPOCH})"
unset PERL_MM_OPT
BSP=$(cd "$(dirname "$0")/.." && pwd)
TASK=${TASK:-$HOME/embedded-bsp}
VENDOR=$TASK/vendor
OUT=$TASK/output
JOBS=${JOBS:-4}
export ARCH=arm64 CROSS_COMPILE=$VENDOR/tools/aarch64-linux/bin/aarch64-linux-gnu-
mkdir -p "$OUT" "$TASK/logs"
test -f "$TASK/logs/extract.ok"
test ! -e "$OUT/build.ok"
test -f "$BSP/configs/kernel.dts"
test -f "$BSP/configs/uboot.dts"
if ! test -f "$OUT/uboot/.config"; then
  make -C "$VENDOR/sources/u-boot" ARCH=arm mrproper
fi
if ! test -f "$OUT/kernel/.config"; then
  make -C "$VENDOR/sources/linux" mrproper
fi
for patchfile in "$BSP"/patches/*.patch; do
  if patch --dry-run -R -d "$VENDOR/sources/linux" -p1 < "$patchfile" >/dev/null 2>&1; then
    : # Already applied.
  else
    patch -d "$VENDOR/sources/linux" -p1 < "$patchfile"
  fi
done
cp "$VENDOR/boards/DR1M/configs/defconfigs/anlogic_dr1_uboot_defconfig" "$VENDOR/sources/u-boot/configs/"
cp "$VENDOR/boards/DR1M/configs/defconfigs/anlogic_dr1_kernel_defconfig" "$VENDOR/sources/linux/arch/arm64/configs/"
cp "$BSP/configs/kernel.dts" "$VENDOR/sources/linux/arch/arm64/boot/dts/anlogic/anlogic-dr1.dts"
cp "$BSP/configs/uboot.dts" "$VENDOR/sources/u-boot/arch/arm/dts/anlogic-dr1.dts"
python3 "$BSP/scripts/dts_from_hpf.py" "$TASK/system.hpf" "$OUT/hpf-dts.h"
cp "$OUT/hpf-dts.h" "$VENDOR/sources/linux/arch/arm64/boot/dts/anlogic/anlogic-dr1m90-hpf.h"
cp "$OUT/hpf-dts.h" "$VENDOR/sources/u-boot/arch/arm/dts/anlogic-dr1m90-hpf.h"
# Vendor Makefile already contains anlogic-dr1.dtb; verify rather than silently omit.
grep -q 'anlogic-dr1.dtb' "$VENDOR/sources/linux/arch/arm64/boot/dts/anlogic/Makefile"
make -C "$VENDOR/sources/u-boot" ARCH=arm O="$OUT/uboot" anlogic_dr1_uboot_defconfig
"$VENDOR/sources/linux/scripts/config" --file "$OUT/uboot/.config" \
  --disable ENV_IS_IN_FAT --disable ENV_IS_IN_MMC --disable ENV_IS_IN_NAND \
  --disable ENV_IS_IN_SPI_FLASH --enable ENV_IS_NOWHERE
make -C "$VENDOR/sources/u-boot" ARCH=arm O="$OUT/uboot" olddefconfig
make -C "$VENDOR/sources/u-boot" ARCH=arm O="$OUT/uboot" -j"$JOBS" DEVICE_TREE=anlogic-dr1 all
make -C "$VENDOR/sources/linux" O="$OUT/kernel" anlogic_dr1_kernel_defconfig
"$VENDOR/sources/linux/scripts/kconfig/merge_config.sh" -m -O "$OUT/kernel" "$OUT/kernel/.config" "$BSP/configs/kernel.fragment"
make -C "$VENDOR/sources/linux" O="$OUT/kernel" olddefconfig
make -C "$VENDOR/sources/linux" O="$OUT/kernel" -j"$JOBS" Image modules dtbs
make -C "$VENDOR/sources/linux" O="$OUT/kernel" INSTALL_MOD_PATH="$OUT/overlay" modules_install
# Do not ship build/source symlinks pointing at the host.
find "$OUT/overlay/lib/modules" -maxdepth 2 -type l -delete
install -D -m755 "$BSP/scripts/board_readonly_check.sh" "$OUT/overlay/usr/bin/bsp-readonly-check"
make -C "$VENDOR/sources/buildroot" O="$OUT/buildroot" BR2_DEFCONFIG="$BSP/configs/buildroot_defconfig" defconfig
"$VENDOR/sources/buildroot/utils/config" --file "$OUT/buildroot/.config" \
  --set-str BR2_TOOLCHAIN_EXTERNAL_PATH "$VENDOR/tools/aarch64-linux" \
  --set-str BR2_ROOTFS_OVERLAY "$OUT/overlay" \
  --set-str BR2_DL_DIR "$TASK/downloads"
make -C "$VENDOR/sources/buildroot" O="$OUT/buildroot" olddefconfig
make -C "$VENDOR/sources/buildroot" O="$OUT/buildroot"
mkdir -p "$OUT/boot" "$OUT/debug"
lz4 -f -9 "$OUT/kernel/arch/arm64/boot/Image" "$OUT/boot/Image.lz4"
mkimage -A arm64 -O linux -T kernel -C lz4 -a 0x00400000 -e 0x00400000 -n Linux \
  -d "$OUT/boot/Image.lz4" "$OUT/boot/uImage.lz4"
cp "$OUT/kernel/arch/arm64/boot/dts/anlogic/anlogic-dr1.dtb" "$OUT/boot/system.dtb"
cp "$OUT/uboot/u-boot.bin" "$OUT/boot/"
cp "$OUT/kernel/.config" "$OUT/debug/kernel.config"
cp "$OUT/kernel/Module.symvers" "$OUT/kernel/System.map" "$OUT/kernel/vmlinux" "$OUT/debug/"
cp "$OUT/uboot/.config" "$OUT/debug/uboot.config"
cp "$OUT/buildroot/.config" "$OUT/debug/buildroot.config"
"${CROSS_COMPILE}gcc" --version > "$OUT/debug/toolchain.txt"
touch "$OUT/build.ok"
