#!/bin/bash
set -euo pipefail
export LC_ALL=C
TASK=${TASK:-$HOME/embedded-bsp-integrated}
BASE=${BASE:-$HOME/embedded-bsp}
cd "$TASK"
mkdir -p logs build
exec > >(tee "logs/telemetry-software-$(date -u +%Y%m%d-%H%M%S).log") 2>&1
prefix=$BASE/vendor/tools/aarch64-linux/bin/aarch64-linux-gnu-
kernel=$BASE/output/kernel
test "$(sha256sum "$kernel/.config" | cut -d' ' -f1)" = 81f7b75cb8e2f0901ef3dbd6eb78282db988031904dd1001ed709beb1120dbf1
make -C "$kernel" M="$TASK/bsp/telemetry/provider" ARCH=arm64 CROSS_COMPILE="$prefix" modules
make -C "$kernel" M="$TASK/bsp/telemetry/client" ARCH=arm64 CROSS_COMPILE="$prefix" KBUILD_EXTRA_SYMBOLS="$TASK/bsp/telemetry/provider/Module.symvers" modules
make -C "$kernel" M="$TASK/bsp/motion/client" ARCH=arm64 CROSS_COMPILE="$prefix" KBUILD_EXTRA_SYMBOLS="$TASK/bsp/telemetry/provider/Module.symvers" modules
"${prefix}gcc" -D_DEFAULT_SOURCE -std=c11 -O2 -Wall -Wextra -Werror -pedantic bsp/telemetry/rs485_accept.c pl_rs485/software/rs485_gp.c pl_rs485/software/rs485_telem.c -o build/rs485-accept
sha256sum bsp/telemetry/provider/anlogic-dma-engine.ko bsp/telemetry/client/bsp_rs485.ko bsp/motion/client/bsp_motion.ko build/rs485-accept
echo TELEMETRY_SOFTWARE_BUILD_COMPLETE_NOT_DEPLOYED
