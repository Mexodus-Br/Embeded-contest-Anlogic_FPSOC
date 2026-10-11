#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C LANG=C TZ=UTC SOURCE_DATE_EPOCH=1791676800
export KBUILD_BUILD_USER=bsp KBUILD_BUILD_HOST=linux-builder KBUILD_BUILD_VERSION=1
export KBUILD_BUILD_TIMESTAMP="$(date -u -d @${SOURCE_DATE_EPOCH})"
BSP=$(cd "$(dirname "$0")/.." && pwd)
TASK=${TASK:-$HOME/embedded-bsp}
VENDOR=$TASK/vendor
OUT=$TASK/output
export ARCH=arm64 CROSS_COMPILE=$VENDOR/tools/aarch64-linux/bin/aarch64-linux-gnu-
test -f "$OUT/build.ok"
python3 "$BSP/scripts/dts_from_hpf.py" "$TASK/system.hpf" "$OUT/hpf-dts.h"
cp "$OUT/hpf-dts.h" "$VENDOR/sources/linux/arch/arm64/boot/dts/anlogic/anlogic-dr1m90-hpf.h"
cp "$OUT/hpf-dts.h" "$VENDOR/sources/u-boot/arch/arm/dts/anlogic-dr1m90-hpf.h"
cp "$BSP/configs/kernel.dts" "$VENDOR/sources/linux/arch/arm64/boot/dts/anlogic/anlogic-dr1.dts"
cp "$BSP/configs/uboot.dts" "$VENDOR/sources/u-boot/arch/arm/dts/anlogic-dr1.dts"
"$VENDOR/sources/linux/scripts/config" --file "$OUT/uboot/.config" \
  --disable ENV_IS_IN_FAT --disable ENV_IS_IN_MMC --disable ENV_IS_IN_NAND \
  --disable ENV_IS_IN_SPI_FLASH --enable ENV_IS_NOWHERE
make -C "$VENDOR/sources/u-boot" ARCH=arm O="$OUT/uboot" olddefconfig
make -C "$VENDOR/sources/u-boot" ARCH=arm O="$OUT/uboot" -j4 DEVICE_TREE=anlogic-dr1 all
make -C "$VENDOR/sources/linux" O="$OUT/kernel" -j4 dtbs
cp "$OUT/kernel/arch/arm64/boot/dts/anlogic/anlogic-dr1.dtb" "$OUT/boot/system.dtb"
cp "$OUT/uboot/u-boot.bin" "$OUT/boot/"
install -D -m755 "$BSP/scripts/board_readonly_check.sh" "$OUT/overlay/usr/bin/bsp-readonly-check"
make -C "$VENDOR/sources/buildroot" O="$OUT/buildroot"
cp "$OUT/uboot/.config" "$OUT/debug/uboot.config"
cp "$OUT/hpf-dts.h" "$OUT/debug/"
touch "$OUT/finalize.ok"
