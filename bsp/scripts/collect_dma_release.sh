#!/usr/bin/env bash
set -euo pipefail
TASK=${TASK:-$HOME/embedded-bsp-dma}
BASE=${BASE:-$HOME/embedded-bsp}
OUT=$TASK/output
mkdir -p "$OUT/support"
cp "$BASE/output/support/kernel-generated.tar.gz" "$BASE/output/support/downloads.sha256" "$BASE/output/support/source-archives.sha256" "$OUT/support/"
cp -a "$TASK/bsp" "$OUT/support/"
cp -a "$OUT/fsbl" "$OUT/support/"
mkdir -p "$OUT/support/fsbl-source"
cp "$TASK/sdk/master_sdk/solutions/demo/fsbl_dma_loop/"*.c "$TASK/sdk/master_sdk/solutions/demo/fsbl_dma_loop/"*.h "$TASK/sdk/master_sdk/solutions/demo/fsbl_dma_loop/Makefile" "$OUT/support/fsbl-source/"
cp "$TASK/sdk/master_sdk/solutions/boards/project_dma_loop/inc/soc_plat.h" "$OUT/support/fsbl-platform.h"
cp "$TASK/sdk/master_sdk/solutions/boards/project_dma_loop/src/soc_plat.c" "$OUT/support/fsbl-platform.c"
cd "$OUT/release"
sha256sum -c SHA256SUMS
python3 "$TASK/bsp/scripts/verify_dma_image.py" "$TASK"
find "$OUT/debug" "$OUT/support" -type f -print0 | sort -z | xargs -0 sha256sum > "$OUT/support-files.sha256"
tar -czf "$TASK/dma-release.tar.gz" -C "$OUT" release debug support support-files.sha256 -C "$TASK" logs
sha256sum "$TASK/dma-release.tar.gz"
