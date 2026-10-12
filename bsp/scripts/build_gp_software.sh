#!/usr/bin/env bash
# Build against the preserved kernel tree. No disk deployment or module loading.
set -euo pipefail
export LC_ALL=C LANG=C TZ=UTC SOURCE_DATE_EPOCH=1791676800
TASK=${TASK:-$HOME/embedded-bsp}
GP_SOURCE=${GP_SOURCE:-$TASK/gp-software}
OUT=$TASK/output/kernel
export ARCH=arm64 CROSS_COMPILE=$TASK/vendor/tools/aarch64-linux/bin/aarch64-linux-gnu-
export KBUILD_BUILD_USER=bsp KBUILD_BUILD_HOST=linux-builder KBUILD_BUILD_VERSION=1
export KBUILD_BUILD_TIMESTAMP="$(date -u -d @${SOURCE_DATE_EPOCH})"
test -f "$OUT/include/generated/autoconf.h"
test -f "$OUT/Module.symvers"
test -f "$GP_SOURCE/generated/gp_defs.h"
# Freeze the first SD kernel identity; a different tree requires a reviewed
# config/symbol migration, never a same-version-string substitution.
test "$(sha256sum "$OUT/.config" | cut -d' ' -f1)" = 81f7b75cb8e2f0901ef3dbd6eb78282db988031904dd1001ed709beb1120dbf1
test "$(sha256sum "$OUT/Module.symvers" | cut -d' ' -f1)" = ccc69b7dbd1968066b6ce46d5e5a741f55045f7cc9663db722c3959c1cb548a3
make -C "$TASK/vendor/sources/linux" O="$OUT" M="$GP_SOURCE" W=1 modules
"${CROSS_COMPILE}gcc" -Wall -Wextra -Werror -O2 -o "$GP_SOURCE/gp-accept" "$GP_SOURCE/gp_accept.c"
modinfo "$GP_SOURCE/bsp_gp.ko"
"${CROSS_COMPILE}readelf" -h "$GP_SOURCE/gp-accept"
sha256sum "$GP_SOURCE/bsp_gp.ko" "$GP_SOURCE/gp-accept" "$OUT/.config" "$OUT/Module.symvers"
echo GP_SOFTWARE_BUILT_NOT_DEPLOYED
