#!/usr/bin/env bash
set -euo pipefail
TASK=${TASK:-$HOME/embedded-bsp}
OUT=$TASK/output
mkdir -p "$OUT/debug" "$OUT/support"
cp "$OUT/kernel/.config" "$OUT/debug/kernel.config"
cp "$OUT/buildroot/.config" "$OUT/debug/buildroot.config"
cp "$OUT/uboot/.config" "$OUT/debug/uboot.config"
cp -a "$OUT/fsbl" "$OUT/support/"
cp "$TASK/sdk/master_sdk/solutions/boards/project_sd_baseline/inc/soc_plat.h" "$OUT/support/fsbl-platform.h"
cp "$TASK/sdk/master_sdk/solutions/boards/project_sd_baseline/src/soc_plat.c" "$OUT/support/fsbl-platform.c"
tar -czf "$OUT/support/kernel-generated.tar.gz" -C "$OUT/kernel" \
  include/generated include/config arch/arm64/include/generated \
  scripts/mod scripts/basic scripts/genksyms
find "$TASK/downloads" -type f ! -name '*.lock' -print0 | sort -z | xargs -0 sha256sum > "$OUT/support/downloads.sha256"
sha256sum "$TASK"/master-sdk.tar.gz "$HOME"/uisrc-lab-anlogicM-V4.0.1.tar.gz > "$OUT/support/source-archives.sha256"
cp -a "$TASK/bsp/configs" "$TASK/bsp/patches" "$OUT/support/"
tar -czf "$TASK/bsp-release.tar.gz" -C "$OUT" release debug support -C "$TASK" logs
sha256sum "$TASK/bsp-release.tar.gz"
