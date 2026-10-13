#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C TZ=UTC SOURCE_DATE_EPOCH=1791676800
BASE=${BASE:-$HOME/embedded-bsp}
TASK=${TASK:-$HOME/embedded-bsp-motion}
CROSS=$BASE/vendor/tools/aarch64-linux/bin/aarch64-linux-gnu-
KERNEL=$BASE/vendor/sources/linux
KOUT=$BASE/output/kernel
test "$(sha256sum "$KOUT/.config" | cut -d' ' -f1)" = 81f7b75cb8e2f0901ef3dbd6eb78282db988031904dd1001ed709beb1120dbf1
test "$(sha256sum "$KOUT/Module.symvers" | cut -d' ' -f1)" = ccc69b7dbd1968066b6ce46d5e5a741f55045f7cc9663db722c3959c1cb548a3
SRC=$TASK/bsp/motion
make -C "$KERNEL" O="$KOUT" ARCH=arm64 CROSS_COMPILE="$CROSS" M="$SRC/provider" W=1 modules
make -C "$KERNEL" O="$KOUT" ARCH=arm64 CROSS_COMPILE="$CROSS" M="$SRC/client" KBUILD_EXTRA_SYMBOLS="$SRC/provider/Module.symvers" W=1 modules
"${CROSS}gcc" -O2 -Wall -Wextra -Werror -pthread -o "$SRC/motion-accept" "$SRC/motion_accept.c"
sha256sum "$SRC/provider/anlogic-dma-engine.ko" "$SRC/provider/Module.symvers" "$SRC/client/bsp_motion.ko" "$SRC/motion-accept"
modinfo -F vermagic "$SRC/provider/anlogic-dma-engine.ko"
modinfo -F vermagic "$SRC/client/bsp_motion.ko"
