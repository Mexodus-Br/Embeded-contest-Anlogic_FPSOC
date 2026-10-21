#!/bin/bash
set -euo pipefail
export LC_ALL=C
I=$(cd "$(dirname "$0")" && pwd)
P=$(dirname "$I")
export TASK=$P/boot_candidate_v1
B=$HOME/embedded-bsp
W=$HOME/embedded-bsp-wifi-20261018
test -f "$TASK/system.hpf"
test ! -e "$TASK/output/release/sdcard.img"
mkdir -p "$TASK/logs" "$TASK/sdk" "$TASK/vendor" "$TASK/output"
test ! -e "$TASK/sdk/master_sdk"
cp -a "$B/sdk/master_sdk" "$TASK/sdk/master_sdk"
ln -s "$B/vendor/tools" "$TASK/vendor/tools"
GP_RESET_BOOT=1 PLATFORM_NAME=project_controlled_v1 FSBL_VARIANT=fsbl_controlled_v1 bash "$TASK/bsp/scripts/build_fsbl.sh" > "$TASK/logs/fsbl.log" 2>&1
python3 "$I/build_boot_dts.py" > "$TASK/logs/dts.log" 2>&1
cp "$W/output/boot/u-boot.bin" "$W/output/boot/uImage.lz4" "$TASK/output/boot/"
ln -s "$W/output/kernel" "$TASK/output/kernel"
mkdir -p "$TASK/output/buildroot/images"
cp "$P/build/rootfs-offline-complete.ext4" "$TASK/output/buildroot/images/rootfs.ext4"
cmp "$P/build/rootfs-offline-complete.ext4" "$TASK/output/buildroot/images/rootfs.ext4"
python3 "$TASK/bsp/scripts/make_sd_image.py" "$TASK" > "$TASK/logs/package.log" 2>&1
echo OFFLINE_BOOT_IMAGE_GENERATED_NOT_RELEASED
