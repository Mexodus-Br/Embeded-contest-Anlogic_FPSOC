#!/usr/bin/env bash
# Stage inert GP software into a file rootfs; does not enable a DT node or flash.
set -euo pipefail
export LC_ALL=C LANG=C TZ=UTC SOURCE_DATE_EPOCH=1791676800
TASK=${TASK:-$HOME/embedded-bsp}
GP_SOURCE=${GP_SOURCE:-$TASK/gp-software}
OUT=$TASK/output
RELEASE=$(cat "$OUT/kernel/include/config/kernel.release")
test "$RELEASE" = 6.1.111-rt42-bsp-sd1
test "$(sha256sum "$OUT/kernel/.config" | cut -d' ' -f1)" = 81f7b75cb8e2f0901ef3dbd6eb78282db988031904dd1001ed709beb1120dbf1
test "$(modinfo -F vermagic "$GP_SOURCE/bsp_gp.ko")" = '6.1.111-rt42-bsp-sd1 SMP preempt mod_unload modversions aarch64'
STAGE=$OUT/gp-rootfs
mkdir -p "$STAGE"
if ! test -f "$STAGE/baseline-rootfs.ext4"; then
  cp "$OUT/buildroot/images/rootfs.ext4" "$STAGE/baseline-rootfs.ext4"
fi
install -D -m644 "$GP_SOURCE/bsp_gp.ko" "$OUT/overlay/lib/modules/$RELEASE/extra/bsp_gp.ko"
install -D -m755 "$GP_SOURCE/gp-accept" "$OUT/overlay/usr/bin/gp-accept"
install -D -m755 "$TASK/bsp/scripts/board_readonly_check.sh" "$OUT/overlay/usr/bin/bsp-readonly-check"
depmod -b "$OUT/overlay" "$RELEASE"
make -C "$TASK/vendor/sources/buildroot" O="$OUT/buildroot"
cmp "$TASK/bsp/scripts/board_readonly_check.sh" "$OUT/buildroot/target/usr/bin/bsp-readonly-check"
cmp "$GP_SOURCE/bsp_gp.ko" "$OUT/buildroot/target/lib/modules/$RELEASE/extra/bsp_gp.ko"
cmp "$GP_SOURCE/gp-accept" "$OUT/buildroot/target/usr/bin/gp-accept"
cp "$OUT/buildroot/images/rootfs.ext4" "$STAGE/rootfs.ext4"
cp "$OUT/buildroot/.config" "$STAGE/buildroot.config"
sha256sum "$STAGE/rootfs.ext4" "$STAGE/buildroot.config" \
 "$OUT/buildroot/target/usr/bin/bsp-readonly-check" "$OUT/buildroot/target/usr/bin/gp-accept"
e2fsck -fn "$STAGE/rootfs.ext4"
echo GP_ROOTFS_STAGED_NO_GP_BOOT_IMAGE_OR_BOARD_TEST
