#!/bin/bash
# Isolated candidate build; does not access any physical device.
set -euo pipefail
export LC_ALL=C TZ=UTC SOURCE_DATE_EPOCH=1791676800
export KBUILD_BUILD_USER=bsp KBUILD_BUILD_HOST=linux-builder KBUILD_BUILD_VERSION=1
export KBUILD_BUILD_TIMESTAMP="$(date -u -d @${SOURCE_DATE_EPOCH})"
TASK=${TASK:-$HOME/embedded-bsp-wifi-20261018}
BASE=${BASE:-$HOME/embedded-bsp}
SCOPE=${SCOPE:-$HOME/embedded-bsp-scope}
WIFI=$TASK/bsp/wifi
K=$TASK/vendor/sources/linux
O=$TASK/output/kernel
export ARCH=arm64 CROSS_COMPILE=$BASE/vendor/tools/aarch64-linux/bin/aarch64-linux-gnu-
mkdir -p "$TASK/logs" "$TASK/output" "$TASK/vendor/sources"
test ! -f "$TASK/output/build.ok"
test ! -L "$TASK/vendor/sources/linux"
if ! test -d "$K"; then cp -a "$BASE/vendor/sources/linux" "$K"; fi
if ! test -d "$O"; then cp -a "$BASE/output/kernel" "$O"; fi
"$K/scripts/kconfig/merge_config.sh" -m -O "$O" "$O/.config" "$WIFI/kernel.fragment"
make -C "$K" O="$O" olddefconfig
make -C "$K" O="$O" -j4 Image modules
mkdir -p "$TASK/build/modules" "$TASK/output/overlay"
for pair in "gp:$HOME/embedded-bsp-gp/bsp/gp" "provider:$SCOPE/bsp/motion/provider" "client:$SCOPE/bsp/motion/client"; do
 name=${pair%%:*}; source=${pair#*:}
 test -d "$TASK/build/modules/$name" || cp -a "$source" "$TASK/build/modules/$name"
done
cp "$SCOPE/bsp/motion/"*.h "$TASK/build/modules/"
test -d "$TASK/build/modules/generated" || cp -a "$SCOPE/bsp/motion/generated" "$TASK/build/modules/generated"
make -C "$K" O="$O" M="$TASK/build/modules/gp" clean
make -C "$K" O="$O" M="$TASK/build/modules/gp" -j4 modules
make -C "$K" O="$O" M="$TASK/build/modules/provider" clean
make -C "$K" O="$O" M="$TASK/build/modules/provider" -j4 modules
make -C "$K" O="$O" M="$TASK/build/modules/client" clean
make -C "$K" O="$O" M="$TASK/build/modules/client" KBUILD_EXTRA_SYMBOLS="$TASK/build/modules/provider/Module.symvers" -j4 modules
python3 "$WIFI/prepare_driver.py" "$TASK"
make -C "$K" O="$O" M="$TASK/build/aic8800" -j4 CONFIG_PLATFORM_ROCKCHIP=n CONFIG_PLATFORM_UBUNTU=n CONFIG_USE_FW_REQUEST=n modules
make -C "$K" O="$O" INSTALL_MOD_PATH="$TASK/output/overlay" modules_install
find "$TASK/output/overlay/lib/modules" -maxdepth 2 -type l -delete
R=$(cat "$O/include/config/kernel.release")
install -D -m644 "$TASK/build/modules/gp/bsp_gp.ko" "$TASK/output/overlay/lib/modules/$R/extra/bsp_gp.ko"
install -D -m644 "$TASK/build/modules/provider/anlogic-dma-engine.ko" "$TASK/output/overlay/lib/modules/$R/kernel/drivers/dma/anlogic/anlogic-dma-engine.ko"
install -D -m644 "$TASK/build/modules/client/bsp_motion.ko" "$TASK/output/overlay/lib/modules/$R/extra/bsp_motion.ko"
# Candidate Wi-Fi modules are deliberately outside modprobe's search path.
for name in aic_load_fw aic8800_fdrv; do
 install -D -m644 "$TASK/build/aic8800/$name/$name.ko" "$TASK/output/overlay/opt/wifi-candidates/$name.ko"
done
depmod -b "$TASK/output/overlay" "$R"
python3 "$WIFI/stage.py" "$TASK" "$SCOPE" "$BASE"
BR=$BASE/vendor/sources/buildroot
B=$TASK/output/buildroot
make -C "$BR" O="$B" BR2_DEFCONFIG="$TASK/build/buildroot.config" defconfig
make -C "$BR" O="$B" olddefconfig
make -C "$BR" O="$B" -j4
mkdir -p "$TASK/output/boot" "$TASK/output/debug" "$TASK/output/fsbl"
cp "$SCOPE/output/fsbl/fsbl.elf" "$TASK/output/fsbl/"
cp "$SCOPE/output/boot/u-boot.bin" "$TASK/output/boot/"
lz4 -f -9 "$O/arch/arm64/boot/Image" "$TASK/output/boot/Image.lz4"
mkimage -A arm64 -O linux -T kernel -C lz4 -a 0x00400000 -e 0x00400000 -n Linux -d "$TASK/output/boot/Image.lz4" "$TASK/output/boot/uImage.lz4"
cp "$O/.config" "$TASK/output/debug/kernel.config"
cp "$B/.config" "$TASK/output/debug/buildroot.config"
python3 "$WIFI/package.py" "$TASK"
python3 "$WIFI/verify.py" "$TASK"
touch "$TASK/output/build.ok"
echo WIFI_CANDIDATE_BUILT_NOT_BOARD_TESTED
