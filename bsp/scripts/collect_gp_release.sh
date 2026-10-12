#!/usr/bin/env bash
set -euo pipefail
TASK=${TASK:-$HOME/embedded-bsp-gp}
BASE=${BASE:-$HOME/embedded-bsp}
OUT=$TASK/output
mkdir -p "$OUT/support" "$OUT/debug"
# These belong to the unchanged, hash-checked kernel build tree.
cp "$BASE/output/support/kernel-generated.tar.gz" \
   "$BASE/output/support/downloads.sha256" "$BASE/output/support/source-archives.sha256" "$OUT/support/"
cp -a "$TASK/bsp/configs" "$TASK/bsp/patches" "$TASK/bsp/gp" "$TASK/bsp/scripts" "$OUT/support/"
cp -a "$OUT/fsbl" "$OUT/support/"
PLAT=$TASK/sdk/master_sdk/solutions/boards/project_gp_control
cp "$PLAT/inc/soc_plat.h" "$OUT/support/fsbl-platform.h"
cp "$PLAT/src/soc_plat.c" "$OUT/support/fsbl-platform.c"
cp "$BASE/output/gp-rootfs/gp-rootfs.sha256" "$OUT/support/" 2>/dev/null || true
cd "$OUT/release"
sha256sum -c SHA256SUMS
fsck.vfat -n boot.vfat
e2fsck -fn rootfs.ext4
test "$(fdtget system.dtb /soc/gp-control@80400000 status)" = "${GP_STATUS:-disabled}"
test "$(sha256sum "$OUT/debug/kernel.config" | cut -d' ' -f1)" = 81f7b75cb8e2f0901ef3dbd6eb78282db988031904dd1001ed709beb1120dbf1
test "$(sha256sum "$OUT/debug/Module.symvers" | cut -d' ' -f1)" = ccc69b7dbd1968066b6ce46d5e5a741f55045f7cc9663db722c3959c1cb548a3
printf 'GP node status=%s. Built artifact; consult BSP evidence for actual SD/board test results.\n' "${GP_STATUS:-disabled}" > "$OUT/support/REVIEW-STATUS.txt"
find "$OUT/debug" "$OUT/support" -type f -print0 | sort -z | xargs -0 sha256sum > "$OUT/support-files.sha256"
bundle=${BUNDLE_NAME:-gp-review-candidate.tar.gz}
test "$bundle" = gp-review-candidate.tar.gz || test "$bundle" = gp-release.tar.gz
tar -czf "$TASK/$bundle" -C "$OUT" release debug support support-files.sha256 -C "$TASK" logs
sha256sum "$TASK/$bundle"
