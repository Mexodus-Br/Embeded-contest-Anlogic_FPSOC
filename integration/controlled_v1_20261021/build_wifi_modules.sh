#!/bin/bash
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd)
TASK=$(dirname "$H")
WIFI=$HOME/embedded-bsp-wifi-20261018
BASE=$HOME/embedded-bsp
test ! -e "$TASK/build/aic8800"
mkdir -p "$TASK/input"
ln -s "$H/frozen/software/bsp" "$TASK/bsp"
ln -s "$WIFI/input/vendor-input.zip" "$TASK/input/vendor-input.zip"
python3 "$H/frozen/software/bsp/wifi/prepare_driver.py" "$TASK"
make -C "$WIFI/vendor/sources/linux" O="$WIFI/output/kernel" M="$TASK/build/aic8800" ARCH=arm64 CROSS_COMPILE="$BASE/vendor/tools/aarch64-linux/bin/aarch64-linux-gnu-" -j4 CONFIG_PLATFORM_ROCKCHIP=n CONFIG_PLATFORM_UBUNTU=n CONFIG_USE_FW_REQUEST=n modules
echo WIFI_MODULES_REBUILT_MATCHED_WIFI1
