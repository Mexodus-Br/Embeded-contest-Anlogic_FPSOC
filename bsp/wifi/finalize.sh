#!/bin/bash
# Restage reviewed scripts/package selections after a completed initial build.
# Never run concurrently with build.sh. Use a new log filename for every attempt.
set -euo pipefail
TASK=${TASK:-$HOME/embedded-bsp-wifi-20261018}
BASE=${BASE:-$HOME/embedded-bsp}
SCOPE=${SCOPE:-$HOME/embedded-bsp-scope}
WIFI=$TASK/bsp/wifi
test -f "$TASK/output/build.ok" || test -f "$TASK/output/build.initial.ok"
if test -f "$TASK/output/build.ok"; then mv "$TASK/output/build.ok" "$TASK/output/build.initial.ok"; fi
python3 "$WIFI/stage.py" "$TASK" "$SCOPE" "$BASE"
BR=$BASE/vendor/sources/buildroot
B=$TASK/output/buildroot
make -C "$BR" O="$B" BR2_DEFCONFIG="$TASK/build/buildroot.config" defconfig
make -C "$BR" O="$B" olddefconfig
make -C "$BR" O="$B" busybox-reconfigure
make -C "$BR" O="$B" -j4
cp "$B/.config" "$TASK/output/debug/buildroot.config"
python3 "$WIFI/package.py" "$TASK"
python3 "$WIFI/verify.py" "$TASK"
touch "$TASK/output/build.ok"
echo WIFI_FINAL_OFFLINE_GATES_PASSED
