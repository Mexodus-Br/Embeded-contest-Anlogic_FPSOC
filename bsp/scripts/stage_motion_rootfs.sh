#!/usr/bin/env bash
# Isolated Buildroot packaging using the original matching host/fakeroot tools.
set -euo pipefail
export LC_ALL=C TZ=UTC SOURCE_DATE_EPOCH=1791676800 E2FSPROGS_FAKE_TIME=1791676800
BASE=${BASE:-$HOME/embedded-bsp}
TASK=${TASK:-$HOME/embedded-bsp-motion}
OUT=$TASK/output
TARGET=$OUT/rootfs-target
RELEASE=6.1.111-rt42-bsp-sd1
test ! -d "$TARGET" || test "${DMA_RESTAGE:-0}" = 1 || { echo 'Target exists; inspect before restaging'; exit 2; }
mkdir -p "$OUT/buildroot/images" "$OUT/debug"
test -d "$TARGET" || cp -a "$HOME/embedded-bsp-dma/output/rootfs-target" "$TARGET"
rm -f "$TARGET/lib/modules/$RELEASE/extra/bsp_dma_loop.ko" "$TARGET/usr/bin/dma-accept"
install -D -m644 "$TASK/bsp/motion/provider/anlogic-dma-engine.ko" "$TARGET/lib/modules/$RELEASE/kernel/drivers/dma/anlogic/anlogic-dma-engine.ko"
install -D -m644 "$TASK/bsp/motion/client/bsp_motion.ko" "$TARGET/lib/modules/$RELEASE/extra/bsp_motion.ko"
install -D -m755 "$TASK/bsp/motion/motion-accept" "$TARGET/usr/bin/motion-accept"
install -D -m755 "$TASK/bsp/scripts/board_readonly_check.sh" "$TARGET/usr/bin/bsp-readonly-check"
test "$(sha256sum "$TARGET/lib/modules/$RELEASE/extra/bsp_gp.ko" | cut -d' ' -f1)" = c0131bcdd4d18485e4392e16428778bf2aac5520bfa48a781ec86d1aede3040b
test "$(sha256sum "$TARGET/usr/bin/gp-accept" | cut -d' ' -f1)" = ce7a38c0c2e4f35fe1b73d0591fc9881476ce064fede2823a57d552840017136
depmod -b "$TARGET" "$RELEASE"
grep '^extra/bsp_motion.ko:' "$TARGET/lib/modules/$RELEASE/modules.dep"
cat > "$OUT/fakeroot-dma.sh" <<EOF
#!/bin/sh
set -e
chown -h -R 0:0 '$TARGET'
'$BASE/output/buildroot/host/bin/makedevs' -d '$BASE/output/buildroot/build/buildroot-fs/full_devices_table.txt' '$TARGET'
find '$TARGET' -print0 | xargs -0 -r touch -hd @1791676800
'$BASE/output/buildroot/host/sbin/mkfs.ext4' -F -d '$TARGET' -r 1 -N 0 -m 5 -L bsp-root -O ^64bit -U 6d398841-220c-4d38-aefa-20ab09f33832 '$OUT/buildroot/images/rootfs.ext4' 256M
EOF
"$BASE/output/buildroot/host/bin/fakeroot" -- sh "$OUT/fakeroot-dma.sh"
e2fsck -fn "$OUT/buildroot/images/rootfs.ext4"
cp "$BASE/output/buildroot/.config" "$OUT/debug/buildroot.config"
sha256sum "$OUT/buildroot/images/rootfs.ext4" "$TARGET/usr/bin/motion-accept" "$TARGET/lib/modules/$RELEASE/extra/bsp_motion.ko" "$TARGET/lib/modules/$RELEASE/kernel/drivers/dma/anlogic/anlogic-dma-engine.ko"
